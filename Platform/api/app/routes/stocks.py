"""
Stock snapshot endpoint — single call for all stock page data.

GET /api/stocks/{ticker}/snapshot
  ?force_refresh=false   (bypass cache; admin/dev only)

Returns:
{
  ticker,
  quote: { price, change, ... , source, fetched_at },
  profile: { name, sector, market_cap, ... },
  fundamentals: { standardized metrics with labels + as_of + sources },
  forward: { fy1, fy2 estimates if available },
  data_quality: { stale_flags, missing_fields, provider }
}
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.services.cache import CacheTTL, get_cache
from app.services.market_data import normalize_symbol, validate_symbol
from app.services.market_data.compute_metrics import (
    compute_staleness,
    compute_standardized_metrics,
)
from app.services.market_data.providers import get_provider
from app.services.market_data.schemas import StockSnapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Stocks"])


@router.get("/stocks/{ticker}/snapshot")
def get_stock_snapshot(
    ticker: str,
    force_refresh: bool = Query(False, description="Bypass cache (dev/admin only)"),
):
    """
    Full stock snapshot: quote + profile + standardized fundamentals + forward estimates + data quality.
    """
    symbol = normalize_symbol(ticker)
    if not validate_symbol(symbol):
        raise HTTPException(status_code=400, detail=f"Invalid ticker format: {ticker}")

    cache = get_cache()
    cache_key = cache.make_key(symbol, "snapshot")

    # Check cache unless force_refresh
    if not force_refresh:
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for snapshot %s", symbol)
            return cached

    logger.info("Computing snapshot for %s (force_refresh=%s)", symbol, force_refresh)

    provider = get_provider()

    # Fetch all data from provider
    quote = provider.get_quote(symbol)
    profile = provider.get_company_profile(symbol)
    fundamentals_raw = provider.get_fundamentals_ttm(symbol)
    forward = provider.get_estimates_forward(symbol)

    # Compute standardized metrics
    standardized = compute_standardized_metrics(
        ticker=symbol,
        fundamentals=fundamentals_raw,
        quote=quote,
        forward=forward,
    )

    # Compute data quality / staleness
    data_quality = compute_staleness(fundamentals_raw, forward, standardized)

    snapshot = StockSnapshot(
        ticker=symbol,
        quote=quote,
        profile=profile,
        fundamentals=standardized,
        forward=forward,
        data_quality=data_quality,
    )

    # Cache the result
    result = snapshot.model_dump()
    cache.set(cache_key, result, CacheTTL.SNAPSHOT)

    return result


@router.post("/stocks/{ticker}/refresh")
def refresh_stock_data(ticker: str):
    """
    Force-refresh cached data for a ticker.
    Useful after earnings updates or data corrections.
    """
    symbol = normalize_symbol(ticker)
    if not validate_symbol(symbol):
        raise HTTPException(status_code=400, detail=f"Invalid ticker format: {ticker}")

    cache = get_cache()
    cleared = cache.invalidate_ticker(symbol)

    return {
        "ticker": symbol,
        "cleared_entries": cleared,
        "message": f"Cache cleared for {symbol}. Next request will fetch fresh data.",
    }
