"""
API routes for market quotes.
- GET  /api/quotes?symbols=AAPL,MSFT,SPY
- GET  /api/quotes/{symbol}
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.services.market_data import (
    fetch_quote,
    fetch_quotes,
    normalize_symbol,
    validate_symbol,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Quotes"])


@router.get("/quotes")
def get_quotes(symbols: str = Query(..., description="Comma-separated symbols (max 50)")):
    """Fetch quotes for multiple symbols."""
    raw_list = [s.strip() for s in symbols.split(",") if s.strip()]

    if not raw_list:
        raise HTTPException(status_code=400, detail="No symbols provided")
    if len(raw_list) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 symbols per request")

    quotes_dict, meta = fetch_quotes(raw_list)

    return {
        "quotes": quotes_dict,
        "meta": meta,
    }


@router.get("/quotes/{symbol}")
def get_single_quote(symbol: str):
    """Fetch a single quote."""
    normalized = normalize_symbol(symbol)
    if not validate_symbol(normalized):
        raise HTTPException(status_code=400, detail=f"Invalid symbol format: {symbol}")

    quote = fetch_quote(normalized)

    if quote.get("error") == "NO_QUOTE":
        raise HTTPException(
            status_code=404,
            detail={
                "symbol": normalized,
                "error": "NO_QUOTE",
                "message": quote.get("message", "No quote available"),
                "as_of": quote.get("as_of"),
            },
        )

    return quote
