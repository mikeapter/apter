"""
Caching layer with explicit TTL and cache-busting.

Uses Redis if REDIS_URL is configured, else falls back to in-memory LRU.

TTL rules:
- quote: 30 seconds (real-time-ish)
- daily_prices: 6 hours
- fundamentals: 24 hours
- estimates: 12 hours
- snapshot: 60 seconds (composite)

Cache keys include ticker + endpoint + version for isolation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections import OrderedDict
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ─── TTL configuration ───


class CacheTTL(Enum):
    """Cache TTL in seconds by data type."""

    QUOTE = 30
    DAILY_PRICES = 21600  # 6 hours
    FUNDAMENTALS = 86400  # 24 hours
    ESTIMATES = 43200  # 12 hours
    SNAPSHOT = 60
    SCORE = 300  # 5 minutes


CACHE_VERSION = "v2"  # Bump to invalidate all cached data


# ─── In-memory LRU cache ───


class InMemoryCache:
    """Thread-safe-ish in-memory LRU cache with TTL."""

    def __init__(self, max_size: int = 2048) -> None:
        self._store: OrderedDict[str, dict] = OrderedDict()
        self._max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None

        if time.time() > entry["expires_at"]:
            self._store.pop(key, None)
            return None

        # Move to end (most recently used)
        self._store.move_to_end(key)
        return entry["value"]

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        # Evict oldest if at capacity
        while len(self._store) >= self._max_size:
            self._store.popitem(last=False)

        self._store[key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds,
            "created_at": time.time(),
        }
        self._store.move_to_end(key)

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def clear(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count

    def clear_prefix(self, prefix: str) -> int:
        """Delete all keys matching a prefix (e.g. ticker-specific invalidation)."""
        to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in to_delete:
            del self._store[k]
        return len(to_delete)

    @property
    def size(self) -> int:
        return len(self._store)


# ─── Redis cache (optional) ───


class RedisCache:
    """Redis-backed cache. Only used if REDIS_URL is set."""

    def __init__(self, redis_url: str) -> None:
        try:
            import redis

            self._client = redis.from_url(redis_url, decode_responses=True)
            self._client.ping()
            logger.info("Redis cache connected: %s", redis_url[:30] + "...")
        except Exception as e:
            logger.warning("Redis unavailable, falling back to in-memory: %s", e)
            raise

    def get(self, key: str) -> Optional[Any]:
        raw = self._client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._client.setex(key, ttl_seconds, json.dumps(value, default=str))

    def delete(self, key: str) -> bool:
        return bool(self._client.delete(key))

    def clear(self) -> int:
        # Only clear our namespaced keys
        keys = list(self._client.scan_iter(match=f"apter:{CACHE_VERSION}:*", count=500))
        if keys:
            return self._client.delete(*keys)
        return 0

    def clear_prefix(self, prefix: str) -> int:
        keys = list(self._client.scan_iter(match=f"{prefix}*", count=500))
        if keys:
            return self._client.delete(*keys)
        return 0

    @property
    def size(self) -> int:
        return len(list(self._client.scan_iter(match=f"apter:{CACHE_VERSION}:*", count=500)))


# ─── Cache manager (singleton) ───


class CacheManager:
    """
    Unified cache interface. Auto-selects Redis or in-memory.

    Usage:
        cache = get_cache()
        key = cache.make_key("AAPL", "snapshot")
        cached = cache.get(key)
        if cached is None:
            data = expensive_compute()
            cache.set(key, data, CacheTTL.SNAPSHOT)
    """

    def __init__(self) -> None:
        redis_url = os.getenv("REDIS_URL")
        self._backend: InMemoryCache | RedisCache

        if redis_url:
            try:
                self._backend = RedisCache(redis_url)
                self._backend_name = "redis"
                return
            except Exception:
                pass

        self._backend = InMemoryCache()
        self._backend_name = "in_memory"
        logger.info("Using in-memory LRU cache")

    @staticmethod
    def make_key(ticker: str, endpoint: str, extra: str = "") -> str:
        """Build a namespaced cache key."""
        parts = f"apter:{CACHE_VERSION}:{ticker}:{endpoint}"
        if extra:
            parts += f":{extra}"
        return parts

    def get(self, key: str) -> Optional[Any]:
        return self._backend.get(key)

    def set(self, key: str, value: Any, ttl: CacheTTL | int) -> None:
        ttl_seconds = ttl.value if isinstance(ttl, CacheTTL) else ttl
        self._backend.set(key, value, ttl_seconds)

    def delete(self, key: str) -> bool:
        return self._backend.delete(key)

    def invalidate_ticker(self, ticker: str) -> int:
        """Invalidate all cached data for a ticker (e.g. after earnings update)."""
        prefix = f"apter:{CACHE_VERSION}:{ticker}:"
        return self._backend.clear_prefix(prefix)

    def clear_all(self) -> int:
        """Clear the entire cache."""
        return self._backend.clear()

    @property
    def backend_name(self) -> str:
        return self._backend_name

    @property
    def size(self) -> int:
        return self._backend.size


# ─── Singleton ───

_cache_instance: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance
