"""
In-memory TTL cache for Finnhub market data.

Reuses the same pattern as services/ai/cache.py but with separate
singletons for quote and candle data.

Features:
- Thread-safe-ish dict-based storage
- Per-key TTL with LRU eviction at capacity
- get_stale() for serving expired entries during rate-limit events
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, Optional, Tuple

from app.services.finnhub.config import CACHE_TTL_CANDLES_SECONDS, CACHE_TTL_QUOTE_SECONDS


class MarketDataCache:
    """In-memory cache with per-key TTL and stale-read support."""

    def __init__(self, default_ttl: int, max_size: int = 512):
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size

    @staticmethod
    def _make_key(*parts: Any) -> str:
        raw = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def get(self, *key_parts: Any) -> Optional[Any]:
        """Return cached value if not expired, else None."""
        key = self._make_key(*key_parts)
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            # Expired — leave in store for stale reads, return None
            return None
        return value

    def get_stale(self, *key_parts: Any) -> Optional[Any]:
        """Return cached value even if expired (for rate-limit fallback)."""
        key = self._make_key(*key_parts)
        entry = self._store.get(key)
        if entry is None:
            return None
        _, value = entry
        return value

    def set(self, value: Any, *key_parts: Any, ttl: Optional[int] = None) -> None:
        """Store a value with optional custom TTL."""
        key = self._make_key(*key_parts)
        expires_at = time.monotonic() + (ttl if ttl is not None else self._default_ttl)

        # Evict oldest if at capacity
        if len(self._store) >= self._max_size and key not in self._store:
            oldest_key = min(self._store, key=lambda k: self._store[k][0])
            self._store.pop(oldest_key, None)

        self._store[key] = (expires_at, value)

    def invalidate(self, *key_parts: Any) -> None:
        key = self._make_key(*key_parts)
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


# Module-level singletons
quote_cache = MarketDataCache(default_ttl=CACHE_TTL_QUOTE_SECONDS)
candles_cache = MarketDataCache(default_ttl=CACHE_TTL_CANDLES_SECONDS)
