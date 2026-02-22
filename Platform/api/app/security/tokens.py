# Platform/api/app/security/tokens.py
"""
Refresh token store with rotation and theft-detection revocation.

Tokens are stored as SHA-256 hashes keyed by (user_id, jti).
Each refresh token is single-use: on refresh, the old token is consumed
and a new one issued.  If a consumed token is presented again (reuse),
ALL tokens for that user are revoked (indicates token theft).

Limitation: in-memory only — tokens are lost on restart.
For production multi-worker deployments, swap with a Redis/DB store.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class _StoredToken:
    token_hash: str
    user_id: int
    jti: str
    created_at: float
    expires_at: float
    consumed: bool = False  # True after it has been used to issue a new pair


class RefreshTokenStore:
    """In-memory refresh token store with rotation and reuse detection."""

    def __init__(self):
        # keyed by jti -> _StoredToken
        self._tokens: dict[str, _StoredToken] = {}
        # user_id -> set of jtis (for mass revocation)
        self._user_tokens: dict[int, set[str]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = 600

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def store(
        self,
        raw_token: str,
        user_id: int,
        jti: str,
        expires_at: float,
    ):
        """Store a newly issued refresh token (hashed)."""
        token_hash = self.hash_token(raw_token)
        entry = _StoredToken(
            token_hash=token_hash,
            user_id=user_id,
            jti=jti,
            created_at=time.time(),
            expires_at=expires_at,
        )
        with self._lock:
            self._maybe_cleanup()
            self._tokens[jti] = entry
            self._user_tokens.setdefault(user_id, set()).add(jti)

    def validate_and_consume(
        self,
        raw_token: str,
        jti: str,
        user_id: int,
    ) -> bool:
        """
        Validate a refresh token for rotation.

        Returns True if the token is valid and has been consumed.
        Raises HTTPException(401) if invalid.
        Revokes ALL user tokens if reuse is detected (theft).
        """
        token_hash = self.hash_token(raw_token)

        with self._lock:
            entry = self._tokens.get(jti)

            if entry is None:
                # Token not found — could be expired/revoked or never existed
                logger.warning("Refresh token not found: jti=%s user=%s", jti, user_id)
                return False

            # Check if token was already consumed (REUSE DETECTED = THEFT)
            if entry.consumed:
                logger.warning(
                    "REFRESH TOKEN REUSE DETECTED — revoking all tokens for user %s (jti=%s)",
                    user_id,
                    jti,
                )
                self._revoke_all_for_user_locked(user_id)
                return False

            # Verify hash matches
            if entry.token_hash != token_hash:
                logger.warning("Refresh token hash mismatch: jti=%s user=%s", jti, user_id)
                return False

            # Verify user matches
            if entry.user_id != user_id:
                logger.warning("Refresh token user mismatch: jti=%s", jti)
                return False

            # Check expiry
            if entry.expires_at < time.time():
                logger.info("Refresh token expired: jti=%s user=%s", jti, user_id)
                del self._tokens[jti]
                user_jtis = self._user_tokens.get(user_id)
                if user_jtis:
                    user_jtis.discard(jti)
                return False

            # Mark as consumed (one-time use)
            entry.consumed = True
            return True

    def revoke_all_for_user(self, user_id: int):
        """Revoke all refresh tokens for a user (e.g., on password change or logout-all)."""
        with self._lock:
            self._revoke_all_for_user_locked(user_id)

    def _revoke_all_for_user_locked(self, user_id: int):
        """Must be called with self._lock held."""
        jtis = self._user_tokens.pop(user_id, set())
        for jti in jtis:
            self._tokens.pop(jti, None)
        logger.info("Revoked %d refresh tokens for user %s", len(jtis), user_id)

    def revoke(self, jti: str):
        """Revoke a single refresh token by jti."""
        with self._lock:
            entry = self._tokens.pop(jti, None)
            if entry:
                user_jtis = self._user_tokens.get(entry.user_id)
                if user_jtis:
                    user_jtis.discard(jti)

    def _maybe_cleanup(self):
        """Remove expired tokens periodically. Must be called with lock held."""
        now = time.monotonic()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        current_time = time.time()
        expired = [jti for jti, t in self._tokens.items() if t.expires_at < current_time]
        for jti in expired:
            entry = self._tokens.pop(jti)
            user_jtis = self._user_tokens.get(entry.user_id)
            if user_jtis:
                user_jtis.discard(jti)


# Singleton instance
refresh_token_store = RefreshTokenStore()
