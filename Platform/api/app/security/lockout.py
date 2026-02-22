# Platform/api/app/security/lockout.py
"""
Brute-force protection: account lockout after repeated failed logins.

Tracks failures by (email, IP) tuple. After LOCKOUT_THRESHOLD failures
within the lockout window, the account is locked for LOCKOUT_DURATION_MINUTES.

Limitation: in-memory only — not shared across workers/processes.
For multi-worker deployments, swap with a Redis-backed implementation.
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


@dataclass
class _LockoutEntry:
    failures: int = 0
    first_failure: float = 0.0
    locked_until: float = 0.0
    timestamps: list[float] = field(default_factory=list)


class LoginLockout:
    """
    In-memory brute-force lockout store.

    Methods:
        check(request, email)    — raise 429 if locked out
        record_failure(request, email) — increment failure counter
        record_success(request, email) — reset failure counter
    """

    def __init__(
        self,
        threshold: int = LOCKOUT_THRESHOLD,
        lockout_minutes: int = LOCKOUT_DURATION_MINUTES,
    ):
        self.threshold = threshold
        self.lockout_seconds = lockout_minutes * 60
        self._entries: dict[str, _LockoutEntry] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = 600  # purge stale entries every 10 min

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _key(self, request: Request, email: str) -> str:
        ip = self._get_client_ip(request)
        return f"{email.lower().strip()}:{ip}"

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
        """Raise 429 if the account+IP is currently locked out."""
        key = self._key(request, email)
        with self._lock:
            self._maybe_cleanup()
            entry = self._entries.get(key)
            if entry and entry.locked_until > time.monotonic():
                remaining = int(entry.locked_until - time.monotonic()) + 1
                logger.warning(
                    "Lockout active for %s (remaining %ds)",
                    email,
                    remaining,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Account temporarily locked due to too many failed login attempts. Please try again later.",
                    headers={"Retry-After": str(remaining)},
                )

    def record_failure(self, request: Request, email: str):
        """Record a failed login attempt. Lock out if threshold reached."""
        key = self._key(request, email)
        now = time.monotonic()

        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                entry = _LockoutEntry()
                self._entries[key] = entry

            # Reset if the lockout window has passed
            if entry.locked_until and entry.locked_until < now:
                entry.failures = 0
                entry.timestamps.clear()
                entry.locked_until = 0.0

            entry.failures += 1
            entry.timestamps.append(now)

            if entry.failures >= self.threshold:
                entry.locked_until = now + self.lockout_seconds
                logger.warning(
                    "Account locked: %s after %d failures (lockout %d min)",
                    email,
                    entry.failures,
                    LOCKOUT_DURATION_MINUTES,
                )

    def record_success(self, request: Request, email: str):
        """Clear failure counter on successful login."""
        key = self._key(request, email)
        with self._lock:
            self._entries.pop(key, None)


# Singleton instance
login_lockout = LoginLockout()
