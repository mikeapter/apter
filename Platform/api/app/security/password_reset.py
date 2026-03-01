# Platform/api/app/security/password_reset.py
"""
Password reset token store.

Generates secure tokens, stores SHA-256 hashes with expiry.
Uses Redis when available, falls back to in-memory.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
import threading
from typing import Optional

from app.security.config import PASSWORD_RESET_TOKEN_MINUTES

logger = logging.getLogger(__name__)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class _InMemoryResetStore:
    """In-memory password reset token store."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # token_hash -> {"user_id": int, "expires_at": float}
        self._tokens: dict[str, dict] = {}

    def create(self, user_id: int) -> str:
        """Generate a reset token and store its hash. Returns the raw token."""
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        expires_at = time.time() + PASSWORD_RESET_TOKEN_MINUTES * 60

        with self._lock:
            # Invalidate any previous tokens for this user
            self._tokens = {
                h: v for h, v in self._tokens.items()
                if v["user_id"] != user_id
            }
            self._tokens[token_hash] = {
                "user_id": user_id,
                "expires_at": expires_at,
            }

        return token

    def validate_and_consume(self, token: str) -> Optional[int]:
        """Validate a reset token. Returns user_id if valid, None otherwise."""
        token_hash = _hash_token(token)
        now = time.time()

        with self._lock:
            entry = self._tokens.pop(token_hash, None)

        if not entry:
            return None
        if entry["expires_at"] < now:
            return None
        return entry["user_id"]


class _RedisResetStore:
    """Redis-backed password reset token store."""

    PREFIX = "apter:pw_reset:"

    def __init__(self, redis_client) -> None:
        self._r = redis_client

    def create(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        ttl = PASSWORD_RESET_TOKEN_MINUTES * 60

        # Remove previous tokens for this user
        old_key = f"{self.PREFIX}user:{user_id}"
        old_hash = self._r.get(old_key)
        if old_hash:
            self._r.delete(f"{self.PREFIX}{old_hash}")

        # Store new token
        self._r.setex(f"{self.PREFIX}{token_hash}", ttl, str(user_id))
        self._r.setex(old_key, ttl, token_hash)

        return token

    def validate_and_consume(self, token: str) -> Optional[int]:
        token_hash = _hash_token(token)
        key = f"{self.PREFIX}{token_hash}"

        user_id_str = self._r.get(key)
        if not user_id_str:
            return None

        self._r.delete(key)
        self._r.delete(f"{self.PREFIX}user:{user_id_str}")
        return int(user_id_str)


class _ResetStoreProxy:
    """Lazy proxy that picks Redis or in-memory on first use."""

    def __init__(self) -> None:
        self._impl: _InMemoryResetStore | _RedisResetStore | None = None

    def _get(self):
        if self._impl is None:
            from app.security.redis import get_redis
            r = get_redis()
            if r:
                self._impl = _RedisResetStore(r)
                logger.info("Password reset store: Redis")
            else:
                self._impl = _InMemoryResetStore()
                logger.info("Password reset store: in-memory")
        return self._impl

    def create(self, user_id: int) -> str:
        return self._get().create(user_id)

    def validate_and_consume(self, token: str) -> Optional[int]:
        return self._get().validate_and_consume(token)


password_reset_store = _ResetStoreProxy()
