"""
Auth refresh endpoint for session stability.

Supports two modes:
  1) Cookie-based: reads apter_rt httpOnly cookie, issues new cookie pair
  2) Bearer-based (legacy): reads Authorization header, issues new bearer token

Cookie-based refresh is preferred and used by the frontend silently on 401.
"""

from __future__ import annotations

import logging
import time
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import oauth2_scheme_optional
from app.models.user import User
from app.services.auth_service import create_access_token, decode_access_token
from app.auth.auth_core import refresh_from_cookie

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

ACCESS_TOKEN_EXPIRE_MINUTES = 60
REMEMBER_TOKEN_EXPIRE_DAYS = 30


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


@router.post("/refresh", response_model=RefreshResponse)
def refresh_token(
    req: Request,
    resp: Response,
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
):
    """
    Refresh the access token.

    1) If apter_rt cookie is present: use cookie-based refresh (issues new cookie pair).
    2) Else if Bearer token is present: use legacy bearer refresh.
    3) Else: 401.
    """

    # --- Cookie-based refresh (preferred) ---
    rt_cookie = req.cookies.get("apter_rt")
    if rt_cookie:
        try:
            user_id = refresh_from_cookie(req, resp, db)
            # Also return a bearer token for backward compat with localStorage
            new_bearer = create_access_token(
                data={"sub": str(user_id)},
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            )
            logger.info("Cookie-based refresh for user %s", user_id)
            return RefreshResponse(
                access_token=new_bearer,
                token_type="bearer",
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Cookie refresh error: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh failed",
            )

    # --- Legacy bearer-based refresh ---
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided",
        )

    try:
        payload = decode_access_token(token)
    except Exception as e:
        logger.info("Refresh failed — invalid token: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(User).filter(User.id == int(user_id_str)).first()
    if not user:
        logger.warning("Refresh failed — user %s not found", user_id_str)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Determine token duration from original token's exp/iat
    exp = payload.get("exp", 0)
    iat = payload.get("iat", time.time())
    original_duration = exp - iat if exp and iat else 3600

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

    logger.info("Bearer-based refresh for user %s", user_id_str)

    return RefreshResponse(
        access_token=new_token,
        token_type="bearer",
        expires_in=expires_in,
    )
