from __future__ import annotations

import os
from datetime import datetime

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.plans import PlanTier

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

PRICE_MAP: dict[str, str | None] = {
    "signals": os.getenv("STRIPE_PRICE_SIGNALS"),
    "pro": os.getenv("STRIPE_PRICE_PRO"),
}

router = APIRouter(prefix="/api/stripe", tags=["Stripe"])


class CreateCheckoutRequest(BaseModel):
    tier: str


# ------------------------------------------
# Create Stripe Checkout Session
# ------------------------------------------
@router.post("/create-checkout-session")
def create_checkout_session(
    payload: CreateCheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.tier not in PRICE_MAP:
        raise HTTPException(status_code=400, detail="Invalid tier for checkout")

    price_id = PRICE_MAP[payload.tier]
    if not price_id:
        raise HTTPException(
            status_code=500,
            detail=f"Stripe price not configured for tier: {payload.tier}",
        )

    # Create or reuse Stripe customer
    if not user.subscription_provider_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": str(user.id)},
        )
        user.subscription_provider_customer_id = customer.id
        user.subscription_provider = "stripe"
        db.commit()

    base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:3000")

    session = stripe.checkout.Session.create(
        customer=user.subscription_provider_customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{base_url}/plans?success=true",
        cancel_url=f"{base_url}/plans?canceled=true",
        metadata={"user_id": str(user.id), "tier": payload.tier},
    )

    return {"checkout_url": session.url}


# ------------------------------------------
# Stripe Webhook
# ------------------------------------------
@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data_object, db)

    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data_object, db)

    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data_object, db)

    return {"received": True}


def _handle_checkout_completed(session: dict, db: Session) -> None:
    metadata = session.get("metadata", {})
    user_id = metadata.get("user_id")
    tier = metadata.get("tier")
    subscription_id = session.get("subscription")

    if not user_id or not tier:
        return

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        return

    user.subscription_tier = tier
    user.subscription_status = "active"
    user.subscription_provider_subscription_id = subscription_id
    user.subscription_updated_at = datetime.utcnow()
    db.commit()


def _handle_subscription_deleted(subscription: dict, db: Session) -> None:
    sub_id = subscription.get("id")
    if not sub_id:
        return

    user = (
        db.query(User)
        .filter(User.subscription_provider_subscription_id == sub_id)
        .first()
    )
    if not user:
        return

    user.subscription_tier = PlanTier.observer.value
    user.subscription_status = "canceled"
    user.subscription_updated_at = datetime.utcnow()
    db.commit()


def _handle_subscription_updated(subscription: dict, db: Session) -> None:
    sub_id = subscription.get("id")
    sub_status = subscription.get("status")
    if not sub_id:
        return

    user = (
        db.query(User)
        .filter(User.subscription_provider_subscription_id == sub_id)
        .first()
    )
    if not user:
        return

    if sub_status == "past_due":
        user.subscription_status = "past_due"
    elif sub_status == "active":
        user.subscription_status = "active"
    elif sub_status in ("canceled", "unpaid"):
        user.subscription_tier = PlanTier.observer.value
        user.subscription_status = "canceled"

    user.subscription_updated_at = datetime.utcnow()
    db.commit()


# ------------------------------------------
# Stripe Customer Portal
# ------------------------------------------
@router.post("/create-portal-session")
def create_portal_session(
    user: User = Depends(get_current_user),
):
    if not user.subscription_provider_customer_id:
        raise HTTPException(status_code=400, detail="No active subscription")

    base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:3000")

    session = stripe.billing_portal.Session.create(
        customer=user.subscription_provider_customer_id,
        return_url=f"{base_url}/plans",
    )

    return {"portal_url": session.url}
