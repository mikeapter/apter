# Platform/api/app/security/tokens.py
"""
Refresh token store with rotation and theft-detection revocation.

Uses Redis if available, otherwise falls back to in-memory.
Tokens are stored as SHA-256 hashes. Each refresh token is single-use.
If a consumed token is reused, ALL tokens for that user are revoked (theft).
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


# ─── In-memory implementation ────────────────────────────────────────────────

@dataclass
class _StoredToken:
    token_hash: str
    user_id: int
    jti: str
    created_at: float
    expires_at: float
    consumed: bool = False


class _InMemoryTokenStore:
    """In-memory refresh token store (single-worker, lost on restart)."""

    def __init__(self):
        self._tokens: dict[str, _StoredToken] = {}
        self._user_tokens: dict[int, set[str]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = 600

    def store(self, raw_token: str, user_id: int, jti: str, expires_at: float):
        token_hash = _hash_token(raw_token)
        entry = _StoredToken(
            token_hash=token_hash, user_id=user_id, jti=jti,
            created_at=time.time(), expires_at=expires_at,
        )
        with self._lock:
            self._maybe_cleanup()
            self._tokens[jti] = entry
            self._user_tokens.setdefault(user_id, set()).add(jti)

    def validate_and_consume(self, raw_token: str, jti: str, user_id: int) -> bool:
        token_hash = _hash_token(raw_token)
        with self._lock:
            entry = self._tokens.get(jti)
            if entry is None:
                logger.warning("Refresh token not found: jti=%s user=%s", jti, user_id)
                return False
            if entry.consumed:
                logger.warning("REFRESH TOKEN REUSE DETECTED — revoking all for user %s", user_id)
                self._revoke_all_locked(user_id)
                return False
            if entry.token_hash != token_hash:
                logger.warning("Refresh token hash mismatch: jti=%s", jti)
                return False
            if entry.user_id != user_id:
                logger.warning("Refresh token user mismatch: jti=%s", jti)
                return False
            if entry.expires_at < time.time():
                logger.info("Refresh token expired: jti=%s", jti)
                del self._tokens[jti]
                user_jtis = self._user_tokens.get(user_id)
                if user_jtis:
                    user_jtis.discard(jti)
                return False
            entry.consumed = True
            return True

    def revoke_all_for_user(self, user_id: int):
        with self._lock:
            self._revoke_all_locked(user_id)

    def _revoke_all_locked(self, user_id: int):
        jtis = self._user_tokens.pop(user_id, set())
        for jti in jtis:
            self._tokens.pop(jti, None)
        logger.info("Revoked %d refresh tokens for user %s", len(jtis), user_id)

    def revoke(self, jti: str):
        with self._lock:
            entry = self._tokens.pop(jti, None)
            if entry:
                user_jtis = self._user_tokens.get(entry.user_id)
                if user_jtis:
                    user_jtis.discard(jti)

    def _maybe_cleanup(self):
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


# ─── Redis implementation ────────────────────────────────────────────────────

class _RedisTokenStore:
    """Redis-backed refresh token store (shared across workers, survives restarts)."""

    def __init__(self, redis_client):
        self._redis = redis_client

    def _token_key(self, jti: str) -> str:
        return f"rt:{jti}"

    def _user_key(self, user_id: int) -> str:
        return f"rt:user:{user_id}"

    def store(self, raw_token: str, user_id: int, jti: str, expires_at: float):
        token_hash = _hash_token(raw_token)
        ttl = max(1, int(expires_at - time.time()) + 60)  # +60s buffer

        try:
            data = json.dumps({
                "token_hash": token_hash,
                "user_id": user_id,
                "jti": jti,
                "created_at": time.time(),
                "expires_at": expires_at,
                "consumed": False,
            })
            pipe = self._redis.pipeline()
            pipe.setex(self._token_key(jti), ttl, data)
            pipe.sadd(self._user_key(user_id), jti)
            pipe.expire(self._user_key(user_id), ttl)
            pipe.execute()
        except Exception as e:
            logger.warning("Redis token store error: %s", str(e))

    def validate_and_consume(self, raw_token: str, jti: str, user_id: int) -> bool:
        token_hash = _hash_token(raw_token)
        try:
            key = self._token_key(jti)
            raw = self._redis.get(key)

            if raw is None:
                logger.warning("Refresh token not found: jti=%s user=%s", jti, user_id)
                return False

            entry = json.loads(raw)

            if entry.get("consumed"):
                logger.warning("REFRESH TOKEN REUSE DETECTED — revoking all for user %s", user_id)
                self.revoke_all_for_user(user_id)
                return False

            if entry.get("token_hash") != token_hash:
                logger.warning("Refresh token hash mismatch: jti=%s", jti)
                return False

            if entry.get("user_id") != user_id:
                logger.warning("Refresh token user mismatch: jti=%s", jti)
                return False

            if entry.get("expires_at", 0) < time.time():
                logger.info("Refresh token expired: jti=%s", jti)
                self._redis.delete(key)
                return False

            # Mark consumed
            entry["consumed"] = True
            ttl = self._redis.ttl(key)
            if ttl and ttl > 0:
                self._redis.setex(key, ttl, json.dumps(entry))
            return True

        except Exception as e:
            logger.warning("Redis token validate error: %s — denying request", str(e))
            return False

    def revoke_all_for_user(self, user_id: int):
        try:
            user_key = self._user_key(user_id)
            jtis = self._redis.smembers(user_key)
            if jtis:
                keys = [self._token_key(jti) for jti in jtis]
                self._redis.delete(*keys, user_key)
                logger.info("Revoked %d refresh tokens for user %s", len(jtis), user_id)
            else:
                self._redis.delete(user_key)
        except Exception as e:
            logger.warning("Redis revoke all error: %s", str(e))

    def revoke(self, jti: str):
        try:
            key = self._token_key(jti)
            raw = self._redis.get(key)
            if raw:
                entry = json.loads(raw)
                user_id = entry.get("user_id")
                self._redis.delete(key)
                if user_id:
                    self._redis.srem(self._user_key(user_id), jti)
        except Exception as e:
            logger.warning("Redis revoke error: %s", str(e))


# ─── Singleton: auto-select Redis or in-memory ──────────────────────────────

def _create_store():
    from app.security.redis import get_redis
    r = get_redis()
    if r is not None:
        return _RedisTokenStore(r)
    return _InMemoryTokenStore()


_store = None


def _get_store():
    global _store
    if _store is None:
        _store = _create_store()
    return _store


class _TokenStoreProxy:
    """Lazy proxy that defers creation until first use."""

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return _hash_token(raw_token)

    def store(self, raw_token: str, user_id: int, jti: str, expires_at: float):
        _get_store().store(raw_token, user_id, jti, expires_at)

    def validate_and_consume(self, raw_token: str, jti: str, user_id: int) -> bool:
        return _get_store().validate_and_consume(raw_token, jti, user_id)

    def revoke_all_for_user(self, user_id: int):
        _get_store().revoke_all_for_user(user_id)

    def revoke(self, jti: str):
        _get_store().revoke(jti)


refresh_token_store = _TokenStoreProxy()
