"""
Market data API routes powered by Finnhub.

Endpoints:
    GET /api/market/quote?ticker=AAPL
    GET /api/market/candles?ticker=AAPL&resolution=D&from=UNIX&to=UNIX
    GET /api/market/profile?ticker=AAPL
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from app.services.finnhub.client import (
    FinnhubError,
    FinnhubRateLimited,
    get_candles,
    get_company_profile,
    get_quote,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["Market Data (Finnhub)"])

# Ticker validation regex — same as client.py
_TICKER_RE = re.compile(r"^[A-Z0-9.\-]{1,15}$")


def _validate_ticker_param(ticker: str) -> str:
    t = ticker.strip().upper()
    if not _TICKER_RE.match(t):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid ticker symbol: {ticker!r}. "
                "Allowed: A-Z, 0-9, '.', '-', max 15 chars."
            ),
        )
    return t


# ─── GET /api/market/quote ───


@router.get("/quote")
async def market_quote(
    ticker: str = Query(..., min_length=1, max_length=15, description="Stock symbol"),
) -> Dict[str, Any]:
    """
    Return a real-time-ish stock quote from Finnhub.
    Cached for ~20 seconds to respect rate limits.
    """
    t = _validate_ticker_param(ticker)

    try:
        return await get_quote(t)
    except FinnhubRateLimited:
        raise HTTPException(
            status_code=429,
            detail="Rate limit reached. Please retry.",
        )
    except FinnhubError as exc:
        logger.warning("Finnhub quote error for %s: %s", t, exc.detail)
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ─── GET /api/market/candles ───


@router.get("/candles")
async def market_candles(
    ticker: str = Query(..., min_length=1, max_length=15, description="Stock symbol"),
    resolution: str = Query("D", description="Candle resolution: 1, 5, 15, 30, 60, D, W, M"),
    from_ts: int = Query(..., alias="from", description="Start UNIX timestamp", gt=0),
    to_ts: int = Query(..., alias="to", description="End UNIX timestamp", gt=0),
) -> Dict[str, Any]:
    """
    Return OHLCV candle data from Finnhub.
    Cached for ~120 seconds.
    """
    t = _validate_ticker_param(ticker)

    if to_ts <= from_ts:
        raise HTTPException(
            status_code=400,
            detail="'to' must be greater than 'from'.",
        )

    try:
        return await get_candles(t, resolution, from_ts, to_ts)
    except FinnhubRateLimited:
        raise HTTPException(
            status_code=429,
            detail="Rate limit reached. Please retry.",
        )
    except FinnhubError as exc:
        logger.warning("Finnhub candles error for %s: %s", t, exc.detail)
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ─── GET /api/market/profile ───


@router.get("/profile")
async def market_profile(
    ticker: str = Query(..., min_length=1, max_length=15, description="Stock symbol"),
) -> Dict[str, Any]:
    """
    Return company profile from Finnhub.
    Cached for ~10 minutes.
    """
    t = _validate_ticker_param(ticker)

    try:
        return await get_company_profile(t)
    except FinnhubRateLimited:
        raise HTTPException(
            status_code=429,
            detail="Rate limit reached. Please retry.",
        )
    except FinnhubError as exc:
        logger.warning("Finnhub profile error for %s: %s", t, exc.detail)
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
