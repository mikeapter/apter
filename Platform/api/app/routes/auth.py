# Platform/api/app/routes/auth.py

from __future__ import annotations

import re
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.twofa_service import decrypt_secret, verify_backup_code, verify_totp
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.services.hubspot_service import sync_contact_to_hubspot

from app.security.config import ACCESS_TOKEN_MINUTES, REFRESH_TOKEN_DAYS
from app.security.rate_limit import get_login_limiter, get_register_limiter
from app.security.lockout import login_lockout
from app.security.tokens import refresh_token_store
from app.security.audit import audit_log


router = APIRouter(prefix="/auth", tags=["Authentication"])

# Name pattern: 2-50 chars, letters, spaces, hyphens, apostrophes
_NAME_PATTERN = re.compile(r"^[a-zA-Z\s'\-]{2,50}$")

REMEMBER_TOKEN_EXPIRE_DAYS = 30


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    referral_source: Optional[str] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        if len(v) > 50:
            raise ValueError("Name must be 50 characters or fewer")
        if not _NAME_PATTERN.match(v):
            raise ValueError("Name may only contain letters, spaces, hyphens, and apostrophes")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("Password must be at least 10 characters")
        return v


class RegisterResponse(BaseModel):
    user_id: int
    email: EmailStr
    first_name: str
    last_name: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_device: bool = False


class Login2FARequest(BaseModel):
    user_id: int
    code: str
    trust_device: bool = False


# ── Helper: issue token pair ─────────────────────────────────────────────────

def _issue_token_pair(user_id: int, remember_device: bool = False) -> dict:
    """
    Issue an access token + a one-time-use refresh token.
    Stores the refresh token hash server-side for rotation.
    """
    access_token = create_access_token(
        data={"sub": str(user_id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_MINUTES),
    )

    if remember_device:
        refresh_delta = timedelta(days=REMEMBER_TOKEN_EXPIRE_DAYS)
    else:
        refresh_delta = timedelta(days=REFRESH_TOKEN_DAYS)

    raw_refresh, jti, expires_at = create_refresh_token(
        user_id=user_id,
        expires_delta=refresh_delta,
    )

    # Store hashed refresh token server-side
    refresh_token_store.store(
        raw_token=raw_refresh,
        user_id=user_id,
        jti=jti,
        expires_at=expires_at,
    )

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
    }


# ─────────────────────────────────────────────────────────────────────────────
# REGISTER (Observer by default)
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/register", response_model=RegisterResponse)
def register(
    payload: RegisterRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Rate limit registration by IP
    get_register_limiter().check(request)

    normalized_email = str(payload.email).lower().strip()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    first = payload.first_name.strip()
    last = payload.last_name.strip()
    user = User(
        first_name=first,
        last_name=last,
        full_name=f"{first} {last}".strip(),
        email=normalized_email,
        hashed_password=hash_password(payload.password),
        subscription_tier="observer",
        subscription_status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Fire-and-forget HubSpot contact sync
    background_tasks.add_task(
        sync_contact_to_hubspot,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        subscription_tier=user.subscription_tier,
        subscription_status=user.subscription_status,
        created_at=user.created_at,
    )

    tokens = _issue_token_pair(user.id)

    audit_log(
        "register",
        request=request,
        user_id=user.id,
        email=normalized_email,
        success=True,
    )

    return RegisterResponse(
        user_id=user.id,
        email=user.email,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN — STEP 1 (PASSWORD)
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    normalized_email = str(payload.email).lower().strip()

    # Rate limit + lockout check
    get_login_limiter().check(request, normalized_email)
    login_lockout.check(request, normalized_email)

    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        # Record failure for lockout tracking
        login_lockout.record_failure(request, normalized_email)
        audit_log(
            "auth_failure",
            request=request,
            email=normalized_email,
            success=False,
            details={"reason": "invalid_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if user.is_2fa_enabled:
        # Don't clear lockout yet — 2FA still needed
        audit_log(
            "auth_2fa_required",
            request=request,
            user_id=user.id,
            email=normalized_email,
            success=True,
        )
        return {
            "requires_2fa": True,
            "user_id": user.id,
            "message": "2FA required",
        }

    # Successful login — clear lockout counter
    login_lockout.record_success(request, normalized_email)

    tokens = _issue_token_pair(user.id, remember_device=payload.remember_device)

    audit_log(
        "auth_success",
        request=request,
        user_id=user.id,
        email=normalized_email,
        success=True,
    )

    return tokens


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN — STEP 2 (2FA)
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/login/2fa")
def login_2fa(
    payload: Login2FARequest,
    request: Request,
    db: Session = Depends(get_db),
):
    # Rate limit 2FA attempts with the login limiter
    get_login_limiter().check(request)

    user = db.query(User).filter(User.id == payload.user_id).first()

    if not user or not user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA session",
        )

    # --- Try TOTP first ---
    secret = decrypt_secret(user.twofa_secret)
    valid_totp = verify_totp(secret, payload.code)

    # --- If not TOTP, try backup code ---
    if not valid_totp:
        if not user.backup_codes:
            login_lockout.record_failure(request, user.email)
            audit_log(
                "auth_failure",
                request=request,
                user_id=user.id,
                email=user.email,
                success=False,
                details={"reason": "invalid_2fa_code"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code",
            )

        valid_backup, remaining_codes = verify_backup_code(
            payload.code,
            user.backup_codes,
        )

        if not valid_backup:
            login_lockout.record_failure(request, user.email)
            audit_log(
                "auth_failure",
                request=request,
                user_id=user.id,
                email=user.email,
                success=False,
                details={"reason": "invalid_2fa_code"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code",
            )

        # Persist backup code invalidation
        user.backup_codes = remaining_codes
        db.commit()

    # Successful 2FA — clear lockout
    login_lockout.record_success(request, user.email)

    tokens = _issue_token_pair(user.id, remember_device=payload.trust_device)

    audit_log(
        "auth_success",
        request=request,
        user_id=user.id,
        email=user.email,
        success=True,
        details={"method": "2fa"},
    )

    return tokens


# ─────────────────────────────────────────────────────────────────────────────
# WHO AM I (token validation)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "user_id": user.id,
        "email": user.email,
        "tier": user.subscription_tier,
        "status": user.subscription_status,
    }
