# Platform/api/app/dependencies.py

import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth_service import decode_access_token
from app.auth.auth_core import get_user_id_from_cookie
from app.models.user import User
from app.services.plans import PlanTier, is_complimentary_pro

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the authenticated user.
    Priority: httpOnly cookie (apter_at) > Bearer header.
    """
    user_id: str | None = None

    # 1) Try cookie first (apter_at httpOnly cookie)
    cookie_uid = get_user_id_from_cookie(request)
    if cookie_uid:
        user_id = cookie_uid

    # 2) Fall back to Bearer header
    if not user_id and token:
        try:
            payload = decode_access_token(token)
        except Exception as exc:
            msg = str(exc).lower()
            if "expired" in msg:
                logger.info("Token expired for request")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired. Please sign in again.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            logger.warning("Token decode failed: %s", msg[:120])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Reject refresh tokens used as access tokens
        if payload.get("type") == "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )

        user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended",
        )

    # Auto-upgrade complimentary Pro accounts
    if is_complimentary_pro(user.email) and user.subscription_tier != PlanTier.pro.value:
        user.subscription_tier = PlanTier.pro.value
        user.subscription_status = "active"
        user.subscription_provider = "complimentary"
        db.commit()

    return user


def get_optional_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User | None:
    """Same as get_current_user but returns None instead of raising."""
    user_id: str | None = None

    # 1) Try cookie first
    cookie_uid = get_user_id_from_cookie(request)
    if cookie_uid:
        user_id = cookie_uid

    # 2) Fall back to Bearer header
    if not user_id and token:
        try:
            payload = decode_access_token(token)
            if payload.get("type") == "refresh":
                return None
            user_id = payload.get("sub")
        except Exception:
            return None

    if not user_id:
        return None

    try:
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
