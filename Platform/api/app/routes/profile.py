"""
Profile routes:
- GET  /api/me       — Current user profile
- PUT  /api/me       — Update profile fields
- PUT  /api/me/avatar — Upload avatar image
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api", tags=["Profile"])


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    account_name: Optional[str] = None


@router.get("/me")
def get_profile(
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return current user's profile."""
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    full = user.display_name()

    return {
        "id": user.id,
        "email": user.email,
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full,
        "phone": getattr(user, "phone", None) or None,
        "account_name": getattr(user, "account_name", None) or full,
        "avatar_url": getattr(user, "avatar_url", None),
        "subscription_tier": user.subscription_tier,
        "subscription_status": user.subscription_status,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.put("/me")
def update_profile(
    payload: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Update profile fields."""
    if payload.full_name is not None:
        parts = payload.full_name.strip().split(" ", 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ""
        user.full_name = payload.full_name.strip()

    if payload.phone is not None and hasattr(user, "phone"):
        user.phone = payload.phone  # type: ignore
    if payload.account_name is not None and hasattr(user, "account_name"):
        user.account_name = payload.account_name  # type: ignore

    db.commit()
    db.refresh(user)

    return get_profile(user)


@router.put("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Upload avatar image. Returns updated avatar_url."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "uploads", "avatars")
    os.makedirs(upload_dir, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "png"
    filename = f"user_{user.id}.{ext}"
    filepath = os.path.join(upload_dir, filename)

    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    avatar_url = f"/uploads/avatars/{filename}"

    if hasattr(user, "avatar_url"):
        user.avatar_url = avatar_url  # type: ignore
        db.commit()

    return {"avatar_url": avatar_url}
