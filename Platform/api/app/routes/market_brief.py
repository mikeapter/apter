"""
API route for the Market Intelligence Brief.

GET /api/market-brief
  - Returns a deterministic brief built from live market quotes.
  - Caches the result for MARKET_CACHE_TTL_SECONDS (default 300).
  - Response includes cacheAgeSeconds and asOfUtc so the UI can show "cached" state.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter

from app.services.market_data_provider import get_market_data_provider
from app.services.market_brief import build_brief

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Market Brief"])

# ─── In-memory cache ───────────────────────────────────────────────────────

_cache_ttl: int = int(os.getenv("MARKET_CACHE_TTL_SECONDS", "300"))
_cached_response: Optional[Dict[str, Any]] = None
_cached_at: float = 0.0

# Default symbols for the brief
BRIEF_SYMBOLS = [
    "SPY", "QQQ", "DIA", "IWM",  # Major indices
    "^VIX",                        # Volatility
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",  # Mega caps
    "TLT", "GLD",                  # Bonds & gold
]


@router.get("/market-brief")
async def get_market_brief() -> Dict[str, Any]:
    """
    Return the current Market Intelligence Brief.
    Cached for MARKET_CACHE_TTL_SECONDS (env, default 300s).
    """
    global _cached_response, _cached_at

    now = time.time()
    age = now - _cached_at if _cached_at > 0 else float("inf")

    # Serve from cache if fresh
    if _cached_response is not None and age < _cache_ttl:
        return {
            **_cached_response,
            "cacheAgeSeconds": int(age),
        }

    # Fetch fresh quotes
    try:
        provider = get_market_data_provider()
        quotes, errors = await provider.quote(BRIEF_SYMBOLS)

        if not quotes:
            logger.warning("No quotes returned; errors: %s", errors)
            # If we have a stale cache, serve it with a flag
            if _cached_response is not None:
                return {
                    **_cached_response,
                    "cacheAgeSeconds": int(age),
                    "stale": True,
                    "fetchError": "No quotes returned from provider",
                }
            return {
                "error": "Unable to fetch market data",
                "details": [{"symbol": e.symbol, "error": e.error} for e in errors],
                "cacheAgeSeconds": 0,
                "asOfUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }

        # Build the brief
        brief = build_brief(quotes)

        # Serialize
        response: Dict[str, Any] = {
            "asOfUtc": brief.asOfUtc,
            "narrative": brief.narrative,
            "regime": brief.regime,
            "volatility": {
                "label": brief.volatility.label,
                "value": brief.volatility.value,
                "method": brief.volatility.method,
            },
            "breadth": {
                "label": brief.breadth.label,
                "green": brief.breadth.green,
                "red": brief.breadth.red,
                "total": brief.breadth.total,
                "explanation": brief.breadth.explanation,
            },
            "whatChanged": brief.what_changed,
            "catalysts": brief.catalysts,
            "quotes": brief.quotes,
            "symbols": brief.symbols,
            "cacheAgeSeconds": 0,
        }

        if errors:
            response["quoteErrors"] = [
                {"symbol": e.symbol, "error": e.error} for e in errors
            ]

        # Update cache
        _cached_response = response
        _cached_at = now

        return response

    except Exception as exc:
        logger.exception("Failed to build market brief: %s", exc)

        # Serve stale cache if available
        if _cached_response is not None:
            return {
                **_cached_response,
                "cacheAgeSeconds": int(age),
                "stale": True,
                "fetchError": str(exc),
            }

        return {
            "error": "Failed to fetch market data",
            "details": str(exc),
            "cacheAgeSeconds": 0,
            "asOfUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
