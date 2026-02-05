from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.twofa_service import (
    generate_totp_secret,
    encrypt_secret,
    decrypt_secret,
    generate_qr_uri,
    verify_totp,
    generate_backup_codes,
)

router = APIRouter(prefix="/2fa", tags=["2FA"])


# -------------------------
# START 2FA SETUP
# -------------------------
@router.post("/setup")
def setup_2fa(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA already enabled",
        )

    secret = generate_totp_secret()
    encrypted_secret = encrypt_secret(secret)
    qr_uri = generate_qr_uri(user.email, secret)

    user.twofa_secret = encrypted_secret
    db.commit()

    return {
        "qr_uri": qr_uri,
        "manual_key": secret,
    }


# -------------------------
# VERIFY & ENABLE 2FA
# -------------------------
@router.post("/verify")
def verify_2fa(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    secret = decrypt_secret(user.twofa_secret)

    if not verify_totp(secret, code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code",
        )

    raw_codes, hashed_codes = generate_backup_codes()

    user.is_2fa_enabled = True
    user.backup_codes = hashed_codes
    db.commit()

    return {
        "backup_codes": raw_codes,
    }


# -------------------------
# DISABLE 2FA
# -------------------------
@router.post("/disable")
def disable_2fa(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    user.is_2fa_enabled = False
    user.twofa_secret = None
    user.backup_codes = None
    db.commit()

    return {"status": "2FA disabled"}
