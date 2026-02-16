from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api", tags=["Profile"])


@router.get("/me")
def get_profile(
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return current user's profile (name, email, tier)."""
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "full_name": user.display_name(),
        "subscription_tier": user.subscription_tier,
        "subscription_status": user.subscription_status,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
