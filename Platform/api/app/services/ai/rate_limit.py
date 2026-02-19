"""Simple in-memory token-bucket rate limiter per user."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class _Bucket:
    tokens: float
    last_refill: float
    capacity: float
    refill_rate: float  # tokens per second

    def consume(self, cost: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


class RateLimiter:
    """Per-user rate limiter with configurable capacity and refill."""

    def __init__(
        self,
        capacity: float = 20.0,
        refill_rate: float = 0.5,  # ~30 requests per minute
    ):
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._buckets: Dict[str, _Bucket] = {}

    def allow(self, user_id: str | int, cost: float = 1.0) -> bool:
        key = str(user_id)
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(
                tokens=self._capacity,
                last_refill=time.monotonic(),
                capacity=self._capacity,
                refill_rate=self._refill_rate,
            )
            self._buckets[key] = bucket
        return bucket.consume(cost)


# Module-level singleton
ai_rate_limiter = RateLimiter()
