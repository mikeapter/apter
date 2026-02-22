# Platform/api/app/security/lockout.py
"""
Brute-force protection: account lockout after repeated failed logins.

Uses Redis if available, otherwise falls back to in-memory.
Tracks failures by (email, IP) tuple. After LOCKOUT_THRESHOLD failures,
the account is locked for LOCKOUT_DURATION_MINUTES.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from fastapi import HTTPException, Request, status

from app.security.config import LOCKOUT_DURATION_MINUTES, LOCKOUT_THRESHOLD

logger = logging.getLogger(__name__)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _make_key(request: Request, email: str) -> str:
    ip = _get_client_ip(request)
    return f"lockout:{email.lower().strip()}:{ip}"


# ─── In-memory implementation ────────────────────────────────────────────────

@dataclass
class _LockoutEntry:
    failures: int = 0
    first_failure: float = 0.0
    locked_until: float = 0.0
    timestamps: list[float] = field(default_factory=list)


class _InMemoryLockout:
    """In-memory brute-force lockout store (single-worker only)."""

    def __init__(self, threshold: int, lockout_seconds: int):
        self.threshold = threshold
        self.lockout_seconds = lockout_seconds
        self._entries: dict[str, _LockoutEntry] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = 600

    def _maybe_cleanup(self):
        now = time.monotonic()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        stale = [
            k for k, v in self._entries.items()
            if v.locked_until < now and (not v.timestamps or v.timestamps[-1] < now - self.lockout_seconds * 2)
        ]
        for k in stale:
            del self._entries[k]

    def check(self, request: Request, email: str):
        key = _make_key(request, email)
        with self._lock:
            self._maybe_cleanup()
            entry = self._entries.get(key)
            if entry and entry.locked_until > time.monotonic():
                remaining = int(entry.locked_until - time.monotonic()) + 1
                logger.warning("Lockout active for %s (remaining %ds)", email, remaining)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Account temporarily locked due to too many failed login attempts. Please try again later.",
                    headers={"Retry-After": str(remaining)},
                )

    def record_failure(self, request: Request, email: str):
        key = _make_key(request, email)
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                entry = _LockoutEntry()
                self._entries[key] = entry
            if entry.locked_until and entry.locked_until < now:
                entry.failures = 0
                entry.timestamps.clear()
                entry.locked_until = 0.0
            entry.failures += 1
            entry.timestamps.append(now)
            if entry.failures >= self.threshold:
                entry.locked_until = now + self.lockout_seconds
                logger.warning("Account locked: %s after %d failures", email, entry.failures)

    def record_success(self, request: Request, email: str):
        key = _make_key(request, email)
        with self._lock:
            self._entries.pop(key, None)


# ─── Redis implementation ────────────────────────────────────────────────────

class _RedisLockout:
    """Redis-backed brute-force lockout (shared across workers)."""

    def __init__(self, redis_client, threshold: int, lockout_seconds: int):
        self._redis = redis_client
        self.threshold = threshold
        self.lockout_seconds = lockout_seconds

    def check(self, request: Request, email: str):
        key = _make_key(request, email)
        try:
            lock_key = f"{key}:locked"
            ttl = self._redis.ttl(lock_key)
            if ttl and ttl > 0:
                logger.warning("Lockout active for %s (remaining %ds)", email, ttl)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Account temporarily locked due to too many failed login attempts. Please try again later.",
                    headers={"Retry-After": str(ttl)},
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Redis lockout check error: %s — allowing request", str(e))

    def record_failure(self, request: Request, email: str):
        key = _make_key(request, email)
        try:
            fail_key = f"{key}:failures"
            pipe = self._redis.pipeline()
            pipe.incr(fail_key)
            pipe.expire(fail_key, self.lockout_seconds * 2)  # Auto-cleanup
            results = pipe.execute()

            failures = results[0]
            if failures >= self.threshold:
                lock_key = f"{key}:locked"
                self._redis.setex(lock_key, self.lockout_seconds, "1")
                logger.warning("Account locked: %s after %d failures", email, failures)
        except Exception as e:
            logger.warning("Redis lockout record error: %s", str(e))

    def record_success(self, request: Request, email: str):
        key = _make_key(request, email)
        try:
            self._redis.delete(f"{key}:failures", f"{key}:locked")
        except Exception as e:
            logger.warning("Redis lockout clear error: %s", str(e))


# ─── Singleton: auto-select Redis or in-memory ──────────────────────────────

def _create_lockout():
    from app.security.redis import get_redis
    lockout_seconds = LOCKOUT_DURATION_MINUTES * 60
    r = get_redis()
    if r is not None:
        return _RedisLockout(r, threshold=LOCKOUT_THRESHOLD, lockout_seconds=lockout_seconds)
    return _InMemoryLockout(threshold=LOCKOUT_THRESHOLD, lockout_seconds=lockout_seconds)


_login_lockout = None


def _get_lockout():
    global _login_lockout
    if _login_lockout is None:
        _login_lockout = _create_lockout()
    return _login_lockout


class _LockoutProxy:
    """Lazy proxy that defers creation until first use."""

    def check(self, request: Request, email: str):
        _get_lockout().check(request, email)

    def record_failure(self, request: Request, email: str):
        _get_lockout().record_failure(request, email)

    def record_success(self, request: Request, email: str):
        _get_lockout().record_success(request, email)


login_lockout = _LockoutProxy()
