"""
API routes for Apter Conviction Score.
- GET  /api/score/{ticker}
- POST /api/score/batch
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException

from app.scoring.overall import compute_conviction_score
from app.scoring.schema import BatchScoreRequest, BatchScoreResponse, ConvictionScoreResponse
from app.services.market_data import get_stock_metrics, normalize_symbol, validate_symbol

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Scoring"])

# ─── In-memory TTL cache for scores ───
_score_cache: Dict[str, dict] = {}
_SCORE_CACHE_TTL = 300  # 5 minutes


def _get_cached(ticker: str) -> Optional[dict]:
    cached = _score_cache.get(ticker)
    if cached and (time.time() - cached["_ts"]) < _SCORE_CACHE_TTL:
        return {k: v for k, v in cached.items() if k != "_ts"}
    return None


def _set_cache(ticker: str, result: dict) -> None:
    _score_cache[ticker] = {**result, "_ts": time.time()}


def _compute_for_ticker(ticker: str) -> dict:
    """Compute conviction score for a single ticker."""
    symbol = normalize_symbol(ticker)

    # Check cache first
    cached = _get_cached(symbol)
    if cached:
        return cached

    metrics = get_stock_metrics(symbol)

    if metrics:
        result = compute_conviction_score(
            ticker=symbol,
            quality_metrics=metrics.get("quality", {}),
            value_metrics=metrics.get("value", {}),
            growth_metrics=metrics.get("growth", {}),
            momentum_metrics=metrics.get("momentum", {}),
            risk_metrics=metrics.get("risk", {}),
            has_peer_group=False,  # MVP: market-wide percentiles
        )
    else:
        # Unknown ticker: return neutral score with low confidence
        result = compute_conviction_score(
            ticker=symbol,
            quality_metrics={},
            value_metrics={},
            growth_metrics={},
            momentum_metrics={},
            risk_metrics={},
            has_peer_group=False,
        )

    _set_cache(symbol, result)
    return result


@router.get("/score/{ticker}")
def get_score(ticker: str):
    """Get conviction score for a single ticker."""
    symbol = normalize_symbol(ticker)
    if not validate_symbol(symbol):
        raise HTTPException(status_code=400, detail=f"Invalid ticker format: {ticker}")

    logger.info("Computing conviction score for %s", symbol)
    result = _compute_for_ticker(symbol)
    return result


@router.post("/score/batch")
def batch_score(request: BatchScoreRequest):
    """Get conviction scores for multiple tickers (max 50)."""
    results = []
    errors = []

    for raw_ticker in request.tickers:
        symbol = normalize_symbol(raw_ticker)
        if not validate_symbol(symbol):
            errors.append({"ticker": raw_ticker, "error": f"Invalid ticker format: {raw_ticker}"})
            continue
        try:
            result = _compute_for_ticker(symbol)
            results.append(result)
        except Exception as e:
            logger.error("Error scoring %s: %s", symbol, str(e))
            errors.append({"ticker": symbol, "error": str(e)})

    return {"results": results, "errors": errors}
