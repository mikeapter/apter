"""
Cookie auth helpers for apter_at (access token) and apter_session (indicator).

The primary refresh token is managed by app/security/tokens.py and the
apter_refresh cookie. This module handles:
  - Setting/clearing the apter_at httpOnly cookie
  - Setting/clearing the apter_session cookie (middleware indicator)
  - Reading user_id from the apter_at cookie for dependency injection
  - Password reuse prevention
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import HTTPException, Request, Response, status

from app.services.auth_service import decode_access_token, verify_password
from app.security.config import ACCESS_TOKEN_MINUTES, IS_PRODUCTION

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cookie configuration
# ---------------------------------------------------------------------------
COOKIE_DOMAIN: Optional[str] = os.getenv("COOKIE_DOMAIN") or None
COOKIE_PATH = "/"
COOKIE_SAMESITE = "lax"


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------
def set_access_cookie(
    resp: Response,
    access_token: str,
    persistent: bool = True,
) -> None:
    """Set the apter_at httpOnly cookie with the access token.

    persistent=True  -> cookie has max-age (survives browser close)
    persistent=False -> session cookie (cleared on browser close)
    """
    kwargs: dict = dict(
        key="apter_at",
        value=access_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
    )
    if persistent:
        kwargs["max_age"] = ACCESS_TOKEN_MINUTES * 60
    if COOKIE_DOMAIN:
        kwargs["domain"] = COOKIE_DOMAIN
    resp.set_cookie(**kwargs)


def set_session_cookie(
    resp: Response,
    persistent: bool = True,
    max_age_days: int = 14,
) -> None:
    """Set the apter_session indicator cookie (non-httpOnly, for Next.js middleware).

    persistent=True  -> cookie has max-age (survives browser close)
    persistent=False -> session cookie (cleared on browser close)
    """
    kwargs: dict = dict(
        key="apter_session",
        value="1",
        httponly=False,
        secure=IS_PRODUCTION,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
    )
    if persistent:
        kwargs["max_age"] = max_age_days * 86400
    if COOKIE_DOMAIN:
        kwargs["domain"] = COOKIE_DOMAIN
    resp.set_cookie(**kwargs)


def clear_access_and_session_cookies(resp: Response) -> None:
    """Clear apter_at and apter_session cookies."""
    for key in ("apter_at", "apter_session"):
        kwargs: dict = dict(key=key, path=COOKIE_PATH)
        if COOKIE_DOMAIN:
            kwargs["domain"] = COOKIE_DOMAIN
        resp.delete_cookie(**kwargs)


# ---------------------------------------------------------------------------
# Read user_id from access-token cookie (for dependency injection)
# ---------------------------------------------------------------------------
def get_user_id_from_cookie(req: Request) -> Optional[str]:
    """Return user_id from apter_at cookie, or None if missing/invalid."""
    at = req.cookies.get("apter_at")
    if not at:
        return None
    try:
        payload = decode_access_token(at)
    except Exception:
        return None
    # Reject refresh tokens
    if payload.get("type") == "refresh":
        return None
    user_id = payload.get("sub")
    return str(user_id) if user_id else None


# ---------------------------------------------------------------------------
# Password-reuse prevention
# ---------------------------------------------------------------------------
def reject_if_reusing_password(new_plain: str, current_hash: str) -> None:
    """Raise 400 if the new password is the same as the current one."""
    if verify_password(new_plain, current_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password.",
        )
