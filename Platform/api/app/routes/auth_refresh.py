# Platform/api/app/routes/auth_refresh.py
"""
Auth refresh endpoint with token rotation.

POST /auth/refresh — Exchange a one-time-use refresh token for a new
access token + refresh token pair.  Reuse of a consumed refresh token
triggers revocation of ALL tokens for that user (theft detection).

The refresh token is read from the `apter_refresh` HTTP-only cookie.
For backward compatibility, a JSON body `{"refresh_token": "..."}` is
also accepted as a fallback.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.security.config import (
    ACCESS_TOKEN_MINUTES,
    IS_PRODUCTION,
    REFRESH_COOKIE_NAME,
    REFRESH_COOKIE_PATH,
    REFRESH_TOKEN_DAYS,
)
from app.security.rate_limit import get_refresh_limiter
from app.security.tokens import refresh_token_store
from app.security.audit import audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

REMEMBER_TOKEN_EXPIRE_DAYS = 30


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # access token TTL in seconds


def _set_refresh_cookie(
    response: Response,
    refresh_token: str,
    remember_device: bool = False,
) -> None:
    max_age = (
        REMEMBER_TOKEN_EXPIRE_DAYS * 86400
        if remember_device
        else REFRESH_TOKEN_DAYS * 86400
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
        max_age=max_age,
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh_token(
    request: Request,
    response: Response,
    payload: RefreshRequest = RefreshRequest(),
    db: Session = Depends(get_db),
):
    """
    Rotate refresh token: consume the old one, issue a new pair.
    If the old token was already consumed (reuse), revoke all user tokens.
    """
    # Rate limit
    get_refresh_limiter().check(request)

    # Read refresh token: prefer HTTP-only cookie, fall back to body
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh and payload and payload.refresh_token:
        raw_refresh = payload.refresh_token

    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
        )

    # Decode the refresh token
    try:
        token_payload = decode_refresh_token(raw_refresh)
    except Exception as e:
        logger.info("Refresh failed — invalid token: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id_str = token_payload.get("sub")
    jti = token_payload.get("jti")

    if not user_id_str or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user_id = int(user_id_str)

    # Validate and consume the refresh token (one-time use)
    if not refresh_token_store.validate_and_consume(
        raw_token=raw_refresh,
        jti=jti,
        user_id=user_id,
    ):
        audit_log(
            "token_refresh_rejected",
            request=request,
            user_id=user_id,
            success=False,
            details={"reason": "invalid_or_reused_refresh_token", "jti": jti},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Verify user still exists and is active
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning("Refresh failed — user %s not found", user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        logger.warning("Refresh failed — user %s suspended", user_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended",
        )

    # Determine refresh token duration from original token
    import time
    exp = token_payload.get("exp", 0)
    iat = token_payload.get("iat", time.time())
    original_duration = exp - iat if exp and iat else REFRESH_TOKEN_DAYS * 86400
    is_remember = original_duration > 86400 * 15  # > 15 days = remember device

    # Issue new token pair
    new_access = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_MINUTES),
    )

    if is_remember:
        refresh_delta = timedelta(days=REMEMBER_TOKEN_EXPIRE_DAYS)
    else:
        refresh_delta = timedelta(days=REFRESH_TOKEN_DAYS)

    new_refresh, new_jti, new_expires_at = create_refresh_token(
        user_id=user.id,
        expires_delta=refresh_delta,
    )

    # Store the new refresh token server-side
    refresh_token_store.store(
        raw_token=new_refresh,
        user_id=user.id,
        jti=new_jti,
        expires_at=new_expires_at,
    )

    # Set new refresh token cookie
    _set_refresh_cookie(response, new_refresh, remember_device=is_remember)

    audit_log(
        "token_refresh",
        request=request,
        user_id=user.id,
        success=True,
    )

    logger.info("Token refreshed for user %s", user_id)

    return RefreshResponse(
        access_token=new_access,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_MINUTES * 60,
    )
