from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.services.twofa_service import decrypt_secret, verify_backup_code, verify_totp
from app.services.auth_service import create_access_token, hash_password, verify_password
from app.services.hubspot_service import sync_contact_to_hubspot


router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class RegisterResponse(BaseModel):
    user_id: int
    email: EmailStr
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Login2FARequest(BaseModel):
    user_id: int
    code: str
    trust_device: bool = False


ACCESS_TOKEN_EXPIRE_MINUTES = 60


# -------------------------
# REGISTER (Observer by default)
# -------------------------
@router.post("/register", response_model=RegisterResponse)
def register(
    payload: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=str(payload.email),
        hashed_password=hash_password(payload.password),
        full_name=payload.name,
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

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return RegisterResponse(
        user_id=user.id,
        email=user.email,
        access_token=access_token,
    )


# -------------------------
# LOGIN — STEP 1 (PASSWORD)
# -------------------------
@router.post("/login")
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # 🚨 2FA gate
    if user.is_2fa_enabled:
        return {
            "requires_2fa": True,
            "user_id": user.id,
            "message": "2FA required",
        }

    # ✅ No 2FA → issue token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# -------------------------
# LOGIN — STEP 2 (2FA)
# -------------------------
@router.post("/login/2fa")
def login_2fa(
    payload: Login2FARequest,
    db: Session = Depends(get_db),
):
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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code",
            )

        valid_backup, remaining_codes = verify_backup_code(
            payload.code,
            user.backup_codes,
        )

        if not valid_backup:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code",
            )

        # Persist backup code invalidation
        user.backup_codes = remaining_codes
        db.commit()

    # ✅ 2FA success → issue token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # (Trust-device cookie logic added in later step)
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
