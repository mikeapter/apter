"""
Finnhub configuration — reads from environment variables.

Required:
    FINNHUB_API_KEY          — Your Finnhub API key (server-side only)

Optional:
    CACHE_TTL_QUOTE_SECONDS  — TTL for quote cache entries  (default 20)
    CACHE_TTL_CANDLES_SECONDS — TTL for candles cache entries (default 120)
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "").strip()
CACHE_TTL_QUOTE_SECONDS: int = int(os.getenv("CACHE_TTL_QUOTE_SECONDS", "20"))
CACHE_TTL_CANDLES_SECONDS: int = int(os.getenv("CACHE_TTL_CANDLES_SECONDS", "120"))

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


def is_configured() -> bool:
    return bool(FINNHUB_API_KEY)


def log_status() -> None:
    if is_configured():
        logger.info("Finnhub integration: ENABLED (API key set)")
    else:
        logger.warning(
            "Finnhub integration: DISABLED — set FINNHUB_API_KEY to enable"
        )
