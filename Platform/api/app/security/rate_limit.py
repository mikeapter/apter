# Platform/api/app/security/rate_limit.py
"""
In-memory sliding-window rate limiter for auth endpoints.

Keyed by client IP (+ optional discriminator like email).
Thread-safe via a lock.

Limitation: in-memory only — not shared across workers/processes.
For multi-worker deployments, swap with a Redis-backed implementation.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request, status


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
        """Seconds until the oldest request in the window expires."""
        if not self.timestamps:
            return 0
        now = time.monotonic()
        oldest = self.timestamps[0]
        return max(1, int(self.window_seconds - (now - oldest)) + 1)


class AuthRateLimiter:
    """
    In-memory sliding-window rate limiter.

    Usage:
        limiter = AuthRateLimiter(max_requests=5, window_seconds=60)
        limiter.check(request)                # keyed by IP only
        limiter.check(request, "user@x.com")  # keyed by IP + email
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, _SlidingWindowCounter] = defaultdict(
            lambda: _SlidingWindowCounter(self.max_requests, self.window_seconds)
        )
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = 300  # purge stale keys every 5 min

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

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
        """
        Raise 429 if the rate limit is exceeded.
        Key = client_ip or client_ip:discriminator.
        """
        ip = self._get_client_ip(request)
        key = f"{ip}:{discriminator}" if discriminator else ip

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


# ── Pre-configured limiter instances (import in routes) ──────────────────────
# These use values from security config but are created lazily to allow
# config to be loaded first.

_login_limiter: Optional[AuthRateLimiter] = None
_refresh_limiter: Optional[AuthRateLimiter] = None
_register_limiter: Optional[AuthRateLimiter] = None


def get_login_limiter() -> AuthRateLimiter:
    global _login_limiter
    if _login_limiter is None:
        from app.security.config import RATE_LIMIT_LOGIN
        _login_limiter = AuthRateLimiter(max_requests=RATE_LIMIT_LOGIN, window_seconds=60)
    return _login_limiter


def get_refresh_limiter() -> AuthRateLimiter:
    global _refresh_limiter
    if _refresh_limiter is None:
        from app.security.config import RATE_LIMIT_REFRESH
        _refresh_limiter = AuthRateLimiter(max_requests=RATE_LIMIT_REFRESH, window_seconds=60)
    return _refresh_limiter


def get_register_limiter() -> AuthRateLimiter:
    global _register_limiter
    if _register_limiter is None:
        from app.security.config import RATE_LIMIT_REGISTER
        _register_limiter = AuthRateLimiter(max_requests=RATE_LIMIT_REGISTER, window_seconds=60)
    return _register_limiter
