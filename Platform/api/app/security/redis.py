# Platform/api/app/security/redis.py
"""
Optional Redis connection for security stores.

If REDIS_URL is set, provides a shared Redis client.
If not set or unreachable, returns None — callers fall back to in-memory.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_redis_client = None
_redis_checked = False


def get_redis():
    """
    Return a Redis client if available, otherwise None.
    Caches the result after first call.
    """
    global _redis_client, _redis_checked

    if _redis_checked:
        return _redis_client

    _redis_checked = True
    redis_url = os.getenv("REDIS_URL", "")

    if not redis_url:
        logger.info("REDIS_URL not set — security stores will use in-memory (not shared across workers)")
        return None

    try:
        import redis
        _redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        # Test the connection
        _redis_client.ping()
        logger.info("Redis connected — security stores will use Redis")
        return _redis_client
    except ImportError:
        logger.warning("redis package not installed — falling back to in-memory stores")
        return None
    except Exception as e:
        logger.warning("Redis connection failed (%s) — falling back to in-memory stores", str(e))
        _redis_client = None
        return None
