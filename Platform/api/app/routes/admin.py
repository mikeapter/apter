"""
Temporary admin endpoints.

DELETE this file after the one-time HubSpot backfill is complete.
"""
from __future__ import annotations

import os
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.services.hubspot_service import batch_upsert_contacts

load_dotenv()

router = APIRouter(prefix="/admin", tags=["Admin (temporary)"])


def _verify_admin_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> str:
    """Verify the admin key matches the HubSpot token (reused as admin secret)."""
    expected = os.getenv("HUBSPOT_PRIVATE_APP_TOKEN", "")
    if not expected or not x_admin_key or x_admin_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Key",
        )
    return x_admin_key


@router.post("/backfill-hubspot")
def backfill_hubspot(
    _key: str = Depends(_verify_admin_key),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    One-time backfill: sync all existing DB users to HubSpot.

    Requires header:  X-Admin-Key: <HUBSPOT_PRIVATE_APP_TOKEN value>

    DELETE THIS ENDPOINT after use.
    """
    users = db.query(User).all()

    if not users:
        return {"users_found": 0, "stats": {"created": 0, "updated": 0, "failed": 0}}

    contacts = []
    for u in users:
        contacts.append({
            "email": u.email,
            "full_name": getattr(u, "full_name", None),
            "subscription_tier": u.subscription_tier,
            "subscription_status": u.subscription_status,
            "user_id": u.id,
            "created_at": u.created_at,
        })

    stats = batch_upsert_contacts(
        contacts,
        batch_size=100,
        delay_seconds=1.0,
    )

    return {"users_found": len(users), "stats": stats}
