"""
Tests for the caching layer.

Validates:
- TTL expiration works correctly
- LRU eviction works
- Cache key generation is consistent
- Prefix-based invalidation works
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.cache import CacheTTL, InMemoryCache, CacheManager


class TestInMemoryCache:
    """Tests for the in-memory LRU cache."""

    def test_set_and_get(self):
        cache = InMemoryCache(max_size=100)
        cache.set("k1", {"value": 42}, ttl_seconds=60)
        assert cache.get("k1") == {"value": 42}

    def test_ttl_expiration(self):
        cache = InMemoryCache(max_size=100)
        cache.set("k1", "hello", ttl_seconds=1)
        assert cache.get("k1") == "hello"
        time.sleep(1.1)
        assert cache.get("k1") is None

    def test_missing_key_returns_none(self):
        cache = InMemoryCache(max_size=100)
        assert cache.get("nonexistent") is None

    def test_lru_eviction(self):
        cache = InMemoryCache(max_size=3)
        cache.set("a", 1, ttl_seconds=60)
        cache.set("b", 2, ttl_seconds=60)
        cache.set("c", 3, ttl_seconds=60)
        # Adding a 4th should evict "a" (oldest)
        cache.set("d", 4, ttl_seconds=60)
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("d") == 4

    def test_lru_access_updates_order(self):
        cache = InMemoryCache(max_size=3)
        cache.set("a", 1, ttl_seconds=60)
        cache.set("b", 2, ttl_seconds=60)
        cache.set("c", 3, ttl_seconds=60)
        # Access "a" to make it recently used
        cache.get("a")
        # Adding "d" should now evict "b" (oldest untouched)
        cache.set("d", 4, ttl_seconds=60)
        assert cache.get("a") == 1
        assert cache.get("b") is None

    def test_delete(self):
        cache = InMemoryCache(max_size=100)
        cache.set("k1", "val", ttl_seconds=60)
        assert cache.delete("k1") is True
        assert cache.get("k1") is None
        assert cache.delete("k1") is False

    def test_clear(self):
        cache = InMemoryCache(max_size=100)
        cache.set("a", 1, ttl_seconds=60)
        cache.set("b", 2, ttl_seconds=60)
        count = cache.clear()
        assert count == 2
        assert cache.size == 0

    def test_clear_prefix(self):
        cache = InMemoryCache(max_size=100)
        cache.set("apter:v2:AAPL:snapshot", 1, ttl_seconds=60)
        cache.set("apter:v2:AAPL:quote", 2, ttl_seconds=60)
        cache.set("apter:v2:MSFT:snapshot", 3, ttl_seconds=60)
        count = cache.clear_prefix("apter:v2:AAPL:")
        assert count == 2
        assert cache.get("apter:v2:AAPL:snapshot") is None
        assert cache.get("apter:v2:MSFT:snapshot") == 3

    def test_size(self):
        cache = InMemoryCache(max_size=100)
        assert cache.size == 0
        cache.set("a", 1, ttl_seconds=60)
        assert cache.size == 1
        cache.set("b", 2, ttl_seconds=60)
        assert cache.size == 2


class TestCacheManager:
    """Tests for the CacheManager wrapper."""

    def test_make_key(self):
        key = CacheManager.make_key("AAPL", "snapshot")
        assert "AAPL" in key
        assert "snapshot" in key
        assert "apter:" in key

    def test_make_key_with_extra(self):
        key = CacheManager.make_key("AAPL", "snapshot", "v2")
        assert "v2" in key

    def test_make_key_consistency(self):
        k1 = CacheManager.make_key("MSFT", "quote")
        k2 = CacheManager.make_key("MSFT", "quote")
        assert k1 == k2

    def test_make_key_uniqueness(self):
        k1 = CacheManager.make_key("AAPL", "snapshot")
        k2 = CacheManager.make_key("MSFT", "snapshot")
        assert k1 != k2

    def test_cache_ttl_enum(self):
        assert CacheTTL.QUOTE.value == 30
        assert CacheTTL.FUNDAMENTALS.value == 86400
        assert CacheTTL.ESTIMATES.value == 43200
        assert CacheTTL.SNAPSHOT.value == 60


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
