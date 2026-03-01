# Platform/api/app/routes/password_reset.py
"""
Password reset endpoints.

POST /auth/forgot-password — Request a password reset (rate-limited).
POST /auth/reset-password  — Submit new password with reset token.

Emails are sent via SendGrid when SENDGRID_API_KEY is set. Otherwise
the reset URL is logged for manual retrieval.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import hash_password
from app.security.config import RATE_LIMIT_FORGOT_PASSWORD
from app.security.rate_limit import get_login_limiter
from app.security.password_reset import password_reset_store
from app.security.audit import audit_log
from app.services.email_service import send_password_reset_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Build the reset URL base from env
_PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://apterfinancial.com")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("Password must be at least 10 characters")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# FORGOT PASSWORD — request reset
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Request a password reset link. Always returns success to prevent
    email enumeration attacks.
    """
    # Rate limit by IP
    get_login_limiter().check(request)

    normalized_email = str(payload.email).lower().strip()

    # Always return success (prevent email enumeration)
    user = db.query(User).filter(User.email == normalized_email).first()

    if user and user.is_active:
        token = password_reset_store.create(user.id)
        reset_url = f"{_PUBLIC_BASE_URL}/reset-password?token={token}"

        # Log the reset URL for admin retrieval until email service is added
        audit_log(
            "password_reset_request",
            request=request,
            user_id=user.id,
            email=normalized_email,
            success=True,
            details={"reset_url": reset_url},
        )

        logger.info("Password reset requested for user %s", user.id)

        send_password_reset_email(normalized_email, reset_url)
    else:
        # Log attempt for non-existent email (don't reveal to client)
        audit_log(
            "password_reset_request",
            request=request,
            email=normalized_email,
            success=False,
            details={"reason": "email_not_found_or_suspended"},
        )

    return {
        "detail": "If an account with that email exists, a reset link has been sent.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# RESET PASSWORD — submit new password
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Validate the reset token and update the user's password."""
    user_id = password_reset_store.validate_and_consume(payload.token)

    if not user_id:
        audit_log(
            "password_reset_failed",
            request=request,
            success=False,
            details={"reason": "invalid_or_expired_token"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended",
        )

    user.hashed_password = hash_password(payload.new_password)
    db.commit()

    audit_log(
        "password_reset_completed",
        request=request,
        user_id=user.id,
        email=user.email,
        success=True,
    )

    logger.info("Password reset completed for user %s", user.id)

    return {"detail": "Password has been reset. You can now sign in."}
