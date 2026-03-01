# Platform/api/app/security/rate_limit.py
"""
Sliding-window rate limiter for auth endpoints.

Uses Redis sorted sets if available, otherwise falls back to in-memory.
Keyed by client IP (+ optional discriminator like email).
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ─── In-memory implementation ────────────────────────────────────────────────

class _SlidingWindowCounter:
    """Per-key sliding window counter."""

    __slots__ = ("timestamps", "window_seconds", "max_requests")

    def __init__(self, max_requests: int, window_seconds: int):
        self.timestamps: list[float] = []
        self.window_seconds = window_seconds
        self.max_requests = max_requests

    def allow(self) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        self.timestamps = [t for t in self.timestamps if t > cutoff]
        if len(self.timestamps) >= self.max_requests:
            return False
        self.timestamps.append(now)
        return True

    @property
    def retry_after(self) -> int:
        if not self.timestamps:
            return 0
        now = time.monotonic()
        oldest = self.timestamps[0]
        return max(1, int(self.window_seconds - (now - oldest)) + 1)


class _InMemoryRateLimiter:
    """In-memory sliding-window rate limiter (single-worker only)."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, _SlidingWindowCounter] = defaultdict(
            lambda: _SlidingWindowCounter(self.max_requests, self.window_seconds)
        )
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = 300

    def _maybe_cleanup(self):
        now = time.monotonic()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        cutoff = now - self.window_seconds * 2
        stale = [
            k for k, v in self._buckets.items()
            if not v.timestamps or v.timestamps[-1] < cutoff
        ]
        for k in stale:
            del self._buckets[k]

    def check(self, request: Request, discriminator: Optional[str] = None):
        ip = _get_client_ip(request)
        key = f"rl:{ip}:{discriminator}" if discriminator else f"rl:{ip}"

        with self._lock:
            self._maybe_cleanup()
            bucket = self._buckets[key]
            if not bucket.allow():
                retry_after = bucket.retry_after
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )


# ─── Redis implementation ────────────────────────────────────────────────────

class _RedisRateLimiter:
    """Redis-backed sliding-window rate limiter (shared across workers)."""

    def __init__(self, redis_client, max_requests: int = 5, window_seconds: int = 60):
        self._redis = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def check(self, request: Request, discriminator: Optional[str] = None):
        ip = _get_client_ip(request)
        key = f"rl:{ip}:{discriminator}" if discriminator else f"rl:{ip}"

        try:
            now = time.time()
            cutoff = now - self.window_seconds

            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(key, "-inf", cutoff)  # Remove expired entries
            pipe.zcard(key)                              # Count remaining
            pipe.zadd(key, {str(uuid.uuid4()): now})     # Add this request
            pipe.expire(key, self.window_seconds + 1)    # Auto-cleanup
            results = pipe.execute()

            count = results[1]  # zcard result

            if count >= self.max_requests:
                # Get oldest entry to calculate retry_after
                oldest = self._redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = max(1, int(self.window_seconds - (now - oldest[0][1])) + 1)
                else:
                    retry_after = self.window_seconds
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )
        except HTTPException:
            raise
        except Exception as e:
            # Redis failure — log and allow (fail open for availability)
            logger.warning("Redis rate limit error: %s — allowing request", str(e))


# ─── Factory: auto-select Redis or in-memory ─────────────────────────────────

def _create_limiter(max_requests: int, window_seconds: int):
    from app.security.redis import get_redis
    r = get_redis()
    if r is not None:
        return _RedisRateLimiter(r, max_requests=max_requests, window_seconds=window_seconds)
    return _InMemoryRateLimiter(max_requests=max_requests, window_seconds=window_seconds)


_login_limiter = None
_refresh_limiter = None
_register_limiter = None


def get_login_limiter():
    global _login_limiter
    if _login_limiter is None:
        from app.security.config import RATE_LIMIT_LOGIN
        _login_limiter = _create_limiter(max_requests=RATE_LIMIT_LOGIN, window_seconds=60)
    return _login_limiter


def get_refresh_limiter():
    global _refresh_limiter
    if _refresh_limiter is None:
        from app.security.config import RATE_LIMIT_REFRESH
        _refresh_limiter = _create_limiter(max_requests=RATE_LIMIT_REFRESH, window_seconds=60)
    return _refresh_limiter


def get_register_limiter():
    global _register_limiter
    if _register_limiter is None:
        from app.security.config import RATE_LIMIT_REGISTER
        _register_limiter = _create_limiter(max_requests=RATE_LIMIT_REGISTER, window_seconds=60)
    return _register_limiter
