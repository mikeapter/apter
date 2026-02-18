"""
Auth refresh endpoint for session stability.
- POST /auth/refresh — Refresh access token using existing valid token
"""

from __future__ import annotations

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import oauth2_scheme_optional
from app.models.user import User
from app.services.auth_service import create_access_token, decode_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

ACCESS_TOKEN_EXPIRE_MINUTES = 60
REMEMBER_TOKEN_EXPIRE_DAYS = 30
EXTENDED_REMEMBER_DAYS = 90


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


@router.post("/refresh", response_model=RefreshResponse)
def refresh_token(
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
):
    """
    Refresh the access token.
    Reads the current token, validates it (with leeway for near-expiry),
    and issues a new token with the same duration.
    Only returns 401 for genuine auth failures.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided",
        )

    try:
        # Decode with leeway to allow near-expired tokens to refresh
        payload = decode_access_token(token)
    except Exception as e:
        logger.info("Refresh failed — invalid token: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Verify user still exists and is active
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        logger.warning("Refresh failed — user %s not found", user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Determine token duration (check original token's exp to infer remember_device)
    import time
    exp = payload.get("exp", 0)
    iat = payload.get("iat", time.time())
    original_duration = exp - iat if exp and iat else 3600

    # If original token was long-lived (>1 day), user had "remember device" on
    if original_duration > 86400:
        expires_delta = timedelta(days=REMEMBER_TOKEN_EXPIRE_DAYS)
        expires_in = REMEMBER_TOKEN_EXPIRE_DAYS * 86400
    else:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60

    new_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=expires_delta,
    )

    logger.info("Token refreshed for user %s", user_id)

    return RefreshResponse(
        access_token=new_token,
        token_type="bearer",
        expires_in=expires_in,
    )
