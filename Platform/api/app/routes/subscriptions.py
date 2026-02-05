from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.plans import PlanTier, plan_definitions, public_plans_payload

load_dotenv()

router = APIRouter(prefix="/api", tags=["Subscriptions"])


class SetTierRequest(BaseModel):
    tier: PlanTier


@router.get("/plans")
def get_plans() -> Dict[str, Any]:
    """Public: pricing + entitlements (no secrets)."""
    return public_plans_payload()


@router.get("/subscription/me")
def my_subscription(
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    plans = plan_definitions()
    tier = PlanTier(user.subscription_tier)
    return {
        "tier": tier.value,
        "plan": plans[tier],
        "status": user.subscription_status,
        "updated_at": user.subscription_updated_at.isoformat() if user.subscription_updated_at else None,
    }


@router.post("/subscription/dev/set-tier")
def dev_set_tier(
    payload: SetTierRequest,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """DEV ONLY: switch the current user's tier for local testing.
    Requires header: X-Admin-Key: <LOCAL_DEV_API_KEY>
    """
    expected = os.getenv("LOCAL_DEV_API_KEY") or ""
    if not expected or not x_admin_key or x_admin_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid X-Admin-Key")

    user.subscription_tier = payload.tier.value
    user.subscription_status = "active"
    user.subscription_updated_at = datetime.utcnow()
    db.commit()

    return {"ok": True, "tier": user.subscription_tier, "status": user.subscription_status}
