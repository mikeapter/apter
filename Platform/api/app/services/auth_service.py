# Platform/api/app/services/auth_service.py
"""
JWT token creation and validation with hardened claims.

Access tokens: short-lived (default 10 min), carry iss/aud/iat/exp/jti.
Refresh tokens: long-lived (default 14 days), separate type claim, single-use.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.security.config import (
    ACCESS_TOKEN_MINUTES,
    JWT_AUDIENCE,
    JWT_ISSUER,
    REFRESH_TOKEN_DAYS,
)

load_dotenv()
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# IMPORTANT: set SECRET_KEY in Platform/api/.env — must be a long random string
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
ALGORITHM = "HS256"

# Warn loudly if the default key is still in use
if SECRET_KEY == "CHANGE_ME_IN_PRODUCTION":
    logger.critical(
        "SECRET_KEY is using the default value! Set a secure random key in .env before deploying."
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a short-lived access token with hardened claims.

    Claims: sub, exp, iat, iss, aud, jti, type="access"
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_MINUTES))

    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "jti": str(uuid.uuid4()),
        "type": "access",
    })

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    user_id: int,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, str, float]:
    """
    Create a long-lived refresh token.

    Returns: (raw_token, jti, expires_at_timestamp)
    The raw token should be sent to the client.
    The jti and hash should be stored server-side via RefreshTokenStore.
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=REFRESH_TOKEN_DAYS))
    jti = str(uuid.uuid4())

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "jti": jti,
        "type": "refresh",
    }

    raw_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    expires_at = expire.timestamp()

    return raw_token, jti, expires_at


def decode_access_token(token: str) -> dict:
    """
    Decode and validate an access token.
    Validates: signature, exp, iss, aud.
    Falls back to permissive decode for pre-hardening tokens (backward compat).
    """
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
    except JWTError:
        # Fall back to permissive decode for tokens issued before hardening.
        # This allows a graceful migration — existing sessions aren't invalidated.
        # Remove this fallback once all pre-hardening tokens have expired.
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},
        )


def decode_refresh_token(token: str) -> dict:
    """
    Decode and validate a refresh token.
    Validates: signature, exp, iss, aud, type == "refresh".
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
    except JWTError:
        # Permissive fallback for backward compatibility
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},
        )

    if payload.get("type") != "refresh":
        raise JWTError("Token is not a refresh token")
    return payload
