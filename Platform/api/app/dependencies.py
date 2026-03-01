from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth_service import decode_access_token
from app.auth.auth_core import get_user_id_from_cookie
from app.models.user import User

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

    # 1) Try cookie first
    cookie_uid = get_user_id_from_cookie(request)
    if cookie_uid:
        user_id = cookie_uid

    # 2) Fall back to Bearer header
    if not user_id and token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
        except Exception:
            pass

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def get_optional_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User | None:
    """Same as get_current_user but returns None instead of raising."""
    user_id: str | None = None

    cookie_uid = get_user_id_from_cookie(request)
    if cookie_uid:
        user_id = cookie_uid

    if not user_id and token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
        except Exception:
            return None

    if not user_id:
        return None

    try:
        return db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        return None
