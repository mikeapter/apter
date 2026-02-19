"""Simple in-memory TTL cache for AI responses."""

from __future__ import annotations

import hashlib
import json
import time
import os
from typing import Any, Dict, Optional


_DEFAULT_TTL = int(os.getenv("AI_CACHE_TTL_SECONDS", "300"))


class TTLCache:
    """Thread-safe-ish in-memory cache with per-key TTL."""

    def __init__(self, default_ttl: int = _DEFAULT_TTL, max_size: int = 256):
        self._store: Dict[str, tuple[float, Any]] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size

    def _make_key(self, *parts: Any) -> str:
        raw = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def get(self, *key_parts: Any) -> Optional[Any]:
        key = self._make_key(*key_parts)
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, value: Any, *key_parts: Any, ttl: int | None = None) -> None:
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


# Module-level singleton
ai_cache = TTLCache()
