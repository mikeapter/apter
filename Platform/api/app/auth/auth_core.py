"""
Core auth module: httpOnly cookie auth with access + refresh tokens.

- Access token: short-lived JWT in httpOnly cookie (apter_at)
- Refresh token: long-lived JWT in httpOnly cookie (apter_rt)
- Refresh sessions stored in DB for revocation support
- Password reuse prevention on reset
"""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Request, Response, HTTPException, status
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.models.refresh_session import RefreshSession
from app.services.auth_service import SECRET_KEY, ALGORITHM, verify_password

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment / config
# ---------------------------------------------------------------------------
APP_ENV = os.getenv("APP_ENV", "development").lower()

ACCESS_MIN = int(os.getenv("ACCESS_TOKEN_TTL_MIN", "20"))
REFRESH_DAYS_SHORT = int(os.getenv("REFRESH_TTL_DAYS_SHORT", "7"))
REFRESH_DAYS_LONG = int(os.getenv("REFRESH_TTL_DAYS_LONG", "30"))

COOKIE_DOMAIN: Optional[str] = os.getenv("COOKIE_DOMAIN") or None  # e.g. ".apterfinancial.com"
COOKIE_PATH = os.getenv("COOKIE_PATH", "/")
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()
COOKIE_SECURE = os.getenv(
    "COOKIE_SECURE",
    "true" if APP_ENV == "production" else "false",
).lower() in ("1", "true", "yes", "on")

if COOKIE_SAMESITE not in ("lax", "strict", "none"):
    COOKIE_SAMESITE = "lax"


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------
def _set_cookie(
    resp: Response,
    key: str,
    value: str,
    max_age_seconds: int | None = None,
) -> None:
    kwargs: dict = dict(
        key=key,
        value=value,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
    )
    # If max_age_seconds is set, cookie persists; otherwise it's a session cookie
    if max_age_seconds is not None:
        kwargs["max_age"] = max_age_seconds
    if COOKIE_DOMAIN:
        kwargs["domain"] = COOKIE_DOMAIN
    resp.set_cookie(**kwargs)


def _delete_cookie(resp: Response, key: str) -> None:
    kwargs: dict = dict(key=key, path=COOKIE_PATH, httponly=True)
    if COOKIE_DOMAIN:
        kwargs["domain"] = COOKIE_DOMAIN
    resp.delete_cookie(**kwargs)


def set_auth_cookies(
    resp: Response,
    access_token: str,
    refresh_token: str,
    refresh_days: int,
    persistent: bool = True,
) -> None:
    """
    Set httpOnly auth cookies on the response.

    persistent=True  → cookies have max-age (survive browser close)
    persistent=False → session cookies (cleared when browser closes)
    """
    # Access token cookie is always short-lived (or session)
    at_max_age = ACCESS_MIN * 60 if persistent else None
    rt_max_age = refresh_days * 86400 if persistent else None

    _set_cookie(resp, "apter_at", access_token, at_max_age)
    _set_cookie(resp, "apter_rt", refresh_token, rt_max_age)

    # Non-httponly indicator so Next.js middleware can see a session
    session_kwargs: dict = dict(
        key="apter_session",
        value="1",
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
    )
    if persistent:
        session_kwargs["max_age"] = refresh_days * 86400
    if COOKIE_DOMAIN:
        session_kwargs["domain"] = COOKIE_DOMAIN
    resp.set_cookie(**session_kwargs)


def clear_auth_cookies(resp: Response) -> None:
    _delete_cookie(resp, "apter_at")
    _delete_cookie(resp, "apter_rt")
    # Clear the session indicator too
    kwargs: dict = dict(key="apter_session", path=COOKIE_PATH)
    if COOKIE_DOMAIN:
        kwargs["domain"] = COOKIE_DOMAIN
    resp.delete_cookie(**kwargs)


# ---------------------------------------------------------------------------
# JWT helpers  (re-uses SECRET_KEY and ALGORITHM from auth_service)
# ---------------------------------------------------------------------------
def make_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_MIN)).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def make_refresh_token(user_id: str, session_id: str, refresh_days: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "sid": session_id,
        "typ": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=refresh_days)).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ---------------------------------------------------------------------------
# Refresh-session DB helpers
# ---------------------------------------------------------------------------
def create_refresh_session(db: Session, user_id: int, refresh_days: int) -> RefreshSession:
    sid = secrets.token_urlsafe(24)
    exp = datetime.now(timezone.utc) + timedelta(days=refresh_days)
    sess = RefreshSession(sid=sid, user_id=user_id, expires_at=exp)
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def get_refresh_session(db: Session, sid: str) -> Optional[RefreshSession]:
    sess = db.query(RefreshSession).filter(RefreshSession.sid == sid).first()
    if not sess:
        return None
    if sess.revoked:
        return None
    if sess.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        return None
    return sess


def revoke_all_sessions_for_user(db: Session, user_id: int) -> None:
    db.query(RefreshSession).filter(
        RefreshSession.user_id == user_id,
        RefreshSession.revoked == False,  # noqa: E712
    ).update({"revoked": True})
    db.commit()


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


# ---------------------------------------------------------------------------
# Issue a full cookie pair (access + refresh) for a user
# ---------------------------------------------------------------------------
def issue_auth_cookies(
    resp: Response,
    db: Session,
    user_id: int,
    keep_signed_in: bool = False,
) -> None:
    """
    Create refresh session + tokens and set httpOnly cookies on the response.

    keep_signed_in=True  → persistent cookies (30 days), survive browser close
    keep_signed_in=False → session cookies, cleared when browser closes
    """
    refresh_days = REFRESH_DAYS_LONG if keep_signed_in else REFRESH_DAYS_SHORT
    sess = create_refresh_session(db, user_id, refresh_days)
    at = make_access_token(str(user_id))
    rt = make_refresh_token(str(user_id), sess.sid, refresh_days)
    set_auth_cookies(resp, at, rt, refresh_days, persistent=keep_signed_in)


# ---------------------------------------------------------------------------
# Cookie-based refresh flow
# ---------------------------------------------------------------------------
def refresh_from_cookie(req: Request, resp: Response, db: Session) -> int:
    """
    Read apter_rt cookie, validate, issue new cookie pair.
    Returns user_id on success, raises 401 on failure.
    """
    rt = req.cookies.get("apter_rt")
    if not rt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    try:
        payload = decode_token(rt)
    except (JWTError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if payload.get("typ") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id_str = str(payload.get("sub") or "")
    sid = str(payload.get("sid") or "")
    if not user_id_str or not sid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    sess = get_refresh_session(db, sid)
    if not sess or sess.user_id != int(user_id_str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh session revoked or expired",
        )

    # Determine remaining lifetime (clamp >= 1 day)
    days_left = max(
        1,
        int((sess.expires_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds() // 86400),
    )

    new_at = make_access_token(user_id_str)
    new_rt = make_refresh_token(user_id_str, sid, days_left)
    # If the refresh cookie was present, it survived browser close → persistent
    set_auth_cookies(resp, new_at, new_rt, days_left, persistent=True)

    return int(user_id_str)


# ---------------------------------------------------------------------------
# Read user_id from access-token cookie (for dependency injection)
# ---------------------------------------------------------------------------
def get_user_id_from_cookie(req: Request) -> Optional[str]:
    """Return user_id from apter_at cookie, or None if missing/invalid."""
    at = req.cookies.get("apter_at")
    if not at:
        return None
    try:
        payload = decode_token(at)
    except (JWTError, Exception):
        return None
    if payload.get("typ") != "access":
        return None
    user_id = payload.get("sub")
    return str(user_id) if user_id else None
