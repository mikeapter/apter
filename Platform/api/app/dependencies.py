from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth_service import decode_access_token
from app.models.user import User
from app.services.plans import PlanTier, is_complimentary_pro

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Auto-upgrade complimentary Pro accounts
    if is_complimentary_pro(user.email) and user.subscription_tier != PlanTier.pro.value:
        user.subscription_tier = PlanTier.pro.value
        user.subscription_status = "active"
        user.subscription_provider = "complimentary"
        db.commit()

    return user


def get_optional_user(
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User | None:
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = db.query(User).filter(User.id == int(user_id)).first()
        # Auto-upgrade complimentary Pro accounts
        if user and is_complimentary_pro(user.email) and user.subscription_tier != PlanTier.pro.value:
            user.subscription_tier = PlanTier.pro.value
            user.subscription_status = "active"
            user.subscription_provider = "complimentary"
            db.commit()
        return user
    except Exception:
        return None
