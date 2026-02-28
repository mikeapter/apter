"""
Market data tool endpoints.

These are called server-side by the AI service to gather context before
generating a response. They also serve as public-facing data endpoints.

Uses Finnhub as the primary live data source when FINNHUB_API_KEY is set.
Falls back to static mock data when the key is missing or the API call fails.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data", tags=["Market Data"])

# ---------------------------------------------------------------------------
# Finnhub config
# ---------------------------------------------------------------------------

_FINNHUB_BASE = "https://finnhub.io/api/v1"


def _fh_key() -> str | None:
    """Return the Finnhub API key (read at call time so hot-reload works)."""
    return os.getenv("FINNHUB_API_KEY") or None


# ---------------------------------------------------------------------------
# Quote cache (shared by live + mock paths)
# ---------------------------------------------------------------------------

_quote_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
_QUOTE_TTL = 60  # seconds — live quotes refresh every 60 s

_news_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
_NEWS_TTL = 600  # 10 min


# ---------------------------------------------------------------------------
# Finnhub helpers
# ---------------------------------------------------------------------------


def _finnhub_quote(ticker: str) -> Dict[str, Any] | None:
    """Fetch a live quote from Finnhub /quote. Returns None on failure."""
    key = _fh_key()
    if not key:
        return None
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(
                f"{_FINNHUB_BASE}/quote",
                params={"symbol": ticker, "token": key},
            )
        r.raise_for_status()
        d = r.json()
        # Finnhub returns c=0 for unknown tickers
        if d.get("c") and d["c"] > 0:
            return {
                "ticker": ticker,
                "price": round(d["c"], 2),
                "change": round(d.get("d") or 0, 2),
                "changePct": round(d.get("dp") or 0, 2),
                "volume": 0,  # Finnhub /quote doesn't include volume
                "open": round(d.get("o") or 0, 2),
                "high": round(d.get("h") or 0, 2),
                "low": round(d.get("l") or 0, 2),
                "prevClose": round(d.get("pc") or 0, 2),
                "source": "finnhub",
            }
    except Exception:
        logger.debug("Finnhub quote failed for %s", ticker, exc_info=True)
    return None


def _finnhub_news(ticker: str, limit: int = 5) -> List[Dict[str, str]] | None:
    """Fetch recent company news from Finnhub /company-news."""
    key = _fh_key()
    if not key:
        return None
    try:
        today = datetime.now(timezone.utc).date()
        from_date = (today - timedelta(days=7)).isoformat()
        to_date = today.isoformat()
        with httpx.Client(timeout=10) as client:
            r = client.get(
                f"{_FINNHUB_BASE}/company-news",
                params={
                    "symbol": ticker,
                    "from": from_date,
                    "to": to_date,
                    "token": key,
                },
            )
        r.raise_for_status()
        items = r.json()
        if not isinstance(items, list):
            return None
        result = []
        for item in items[:limit]:
            result.append({
                "headline": item.get("headline", ""),
                "source": item.get("source", ""),
                "date": datetime.fromtimestamp(
                    item.get("datetime", 0), tz=timezone.utc
                ).strftime("%Y-%m-%d") if item.get("datetime") else "",
                "sentiment": "neutral",  # Finnhub doesn't include sentiment
                "url": item.get("url", ""),
            })
        return result
    except Exception:
        logger.debug("Finnhub news failed for %s", ticker, exc_info=True)
    return None


# ---------------------------------------------------------------------------
# Mock data store (fallback when Finnhub unavailable)
# ---------------------------------------------------------------------------

_MOCK_QUOTES: Dict[str, Dict[str, Any]] = {
    "AAPL": {"ticker": "AAPL", "price": 234.56, "change": 3.21, "changePct": 1.39, "volume": 54_200_000},
    "MSFT": {"ticker": "MSFT", "price": 428.90, "change": 5.67, "changePct": 1.34, "volume": 22_100_000},
    "NVDA": {"ticker": "NVDA", "price": 876.32, "change": -12.43, "changePct": -1.40, "volume": 48_700_000},
    "GOOGL": {"ticker": "GOOGL", "price": 175.23, "change": 2.15, "changePct": 1.24, "volume": 28_300_000},
    "AMZN": {"ticker": "AMZN", "price": 198.45, "change": 1.89, "changePct": 0.96, "volume": 35_600_000},
    "META": {"ticker": "META", "price": 512.78, "change": 8.34, "changePct": 1.65, "volume": 18_900_000},
    "TSLA": {"ticker": "TSLA", "price": 245.67, "change": -4.56, "changePct": -1.82, "volume": 72_400_000},
    "SPY": {"ticker": "SPY", "price": 528.90, "change": 3.45, "changePct": 0.66, "volume": 65_000_000},
    "QQQ": {"ticker": "QQQ", "price": 456.78, "change": 4.12, "changePct": 0.91, "volume": 42_000_000},
    "JPM": {"ticker": "JPM", "price": 198.34, "change": 1.23, "changePct": 0.62, "volume": 12_800_000},
}

_MOCK_FUNDAMENTALS: Dict[str, Dict[str, Any]] = {
    "AAPL": {"marketCap": "3.62T", "peRatio": 29.3, "pegRatio": 2.1, "dividendYield": 0.51, "sector": "Technology", "industry": "Consumer Electronics"},
    "MSFT": {"marketCap": "3.18T", "peRatio": 34.2, "pegRatio": 2.4, "dividendYield": 0.72, "sector": "Technology", "industry": "Software"},
    "NVDA": {"marketCap": "2.15T", "peRatio": 48.7, "pegRatio": 1.8, "dividendYield": 0.02, "sector": "Technology", "industry": "Semiconductors"},
    "GOOGL": {"marketCap": "2.16T", "peRatio": 25.1, "pegRatio": 1.5, "dividendYield": 0.0, "sector": "Technology", "industry": "Internet Services"},
    "AMZN": {"marketCap": "2.04T", "peRatio": 42.8, "pegRatio": 2.0, "dividendYield": 0.0, "sector": "Consumer Cyclical", "industry": "E-Commerce"},
    "META": {"marketCap": "1.32T", "peRatio": 28.4, "pegRatio": 1.6, "dividendYield": 0.36, "sector": "Technology", "industry": "Social Media"},
    "TSLA": {"marketCap": "782B", "peRatio": 62.3, "pegRatio": 3.1, "dividendYield": 0.0, "sector": "Consumer Cyclical", "industry": "Auto Manufacturers"},
    "JPM": {"marketCap": "571B", "peRatio": 12.1, "pegRatio": 1.4, "dividendYield": 2.21, "sector": "Financials", "industry": "Banking"},
}

_MOCK_TECHNICALS: Dict[str, Dict[str, Any]] = {
    "AAPL": {"rsi14": 58, "sma50": 228.30, "sma200": 215.60, "macdSignal": "bullish", "atr14": 3.42, "realizedVol30d": 18.2},
    "MSFT": {"rsi14": 62, "sma50": 415.20, "sma200": 395.80, "macdSignal": "bullish", "atr14": 5.67, "realizedVol30d": 20.1},
    "NVDA": {"rsi14": 45, "sma50": 890.50, "sma200": 720.30, "macdSignal": "bearish", "atr14": 22.30, "realizedVol30d": 42.1},
    "GOOGL": {"rsi14": 55, "sma50": 170.40, "sma200": 158.90, "macdSignal": "neutral", "atr14": 2.89, "realizedVol30d": 22.5},
    "AMZN": {"rsi14": 54, "sma50": 192.30, "sma200": 178.60, "macdSignal": "bullish", "atr14": 3.15, "realizedVol30d": 24.3},
    "META": {"rsi14": 64, "sma50": 498.70, "sma200": 445.20, "macdSignal": "bullish", "atr14": 7.82, "realizedVol30d": 26.8},
    "TSLA": {"rsi14": 38, "sma50": 258.90, "sma200": 235.40, "macdSignal": "bearish", "atr14": 8.95, "realizedVol30d": 48.6},
    "JPM": {"rsi14": 52, "sma50": 195.60, "sma200": 183.20, "macdSignal": "neutral", "atr14": 2.34, "realizedVol30d": 16.4},
}

_MOCK_NEWS: Dict[str, List[Dict[str, str]]] = {
    "AAPL": [
        {"headline": "Apple expands services revenue to record quarter", "source": "Financial Times", "date": "2026-02-16", "sentiment": "positive"},
        {"headline": "iPhone supply chain signals stable production outlook", "source": "Reuters", "date": "2026-02-15", "sentiment": "neutral"},
        {"headline": "Apple AI features drive upgrade cycle expectations", "source": "Bloomberg", "date": "2026-02-14", "sentiment": "positive"},
    ],
    "MSFT": [
        {"headline": "Azure cloud revenue growth accelerates to 32% YoY", "source": "Bloomberg", "date": "2026-02-16", "sentiment": "positive"},
        {"headline": "Microsoft expands AI partnership with enterprise clients", "source": "Reuters", "date": "2026-02-15", "sentiment": "positive"},
    ],
    "NVDA": [
        {"headline": "NVIDIA faces increased competition in AI chip market", "source": "WSJ", "date": "2026-02-16", "sentiment": "negative"},
        {"headline": "Data center GPU demand remains strong despite price concerns", "source": "Bloomberg", "date": "2026-02-15", "sentiment": "neutral"},
    ],
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/quote")
def get_quote(ticker: str = Query(..., min_length=1, max_length=10)) -> Dict[str, Any]:
    t = ticker.upper()

    # Check cache first
    if t in _quote_cache:
        ts, cached = _quote_cache[t]
        if time.time() - ts < _QUOTE_TTL:
            return cached

    # Try Finnhub live quote
    live = _finnhub_quote(t)
    if live:
        _quote_cache[t] = (time.time(), live)
        return live

    # Fallback to mock
    if t in _MOCK_QUOTES:
        mock = {**_MOCK_QUOTES[t], "source": "mock"}
        return mock
    return {"ticker": t, "price": 0, "change": 0, "changePct": 0, "volume": 0, "error": "Ticker not found in dataset"}


@router.get("/fundamentals")
def get_fundamentals(ticker: str = Query(..., min_length=1, max_length=10)) -> Dict[str, Any]:
    t = ticker.upper()
    if t in _MOCK_FUNDAMENTALS:
        return {"ticker": t, **_MOCK_FUNDAMENTALS[t]}
    return {"ticker": t, "error": "No fundamental data available"}


@router.get("/financials")
def get_financials(ticker: str = Query(..., min_length=1, max_length=10)) -> Dict[str, Any]:
    t = ticker.upper()
    # Simplified financials from fundamentals
    fund = _MOCK_FUNDAMENTALS.get(t)
    if fund:
        return {
            "ticker": t,
            "marketCap": fund["marketCap"],
            "peRatio": fund["peRatio"],
            "pegRatio": fund["pegRatio"],
            "dividendYield": fund["dividendYield"],
        }
    return {"ticker": t, "error": "No financial data available"}


@router.get("/technicals")
def get_technicals(
    ticker: str = Query(..., min_length=1, max_length=10),
    window: int = Query(14, ge=5, le=200),
) -> Dict[str, Any]:
    t = ticker.upper()
    if t in _MOCK_TECHNICALS:
        return {"ticker": t, "window": window, **_MOCK_TECHNICALS[t]}
    return {"ticker": t, "window": window, "error": "No technical data available"}


@router.get("/news")
def get_news(
    ticker: str = Query(..., min_length=1, max_length=10),
    limit: int = Query(5, ge=1, le=20),
) -> Dict[str, Any]:
    t = ticker.upper()

    # Check cache
    if t in _news_cache:
        ts, cached = _news_cache[t]
        if time.time() - ts < _NEWS_TTL:
            items = cached.get("items", [])[:limit]
            return {"ticker": t, "count": len(items), "items": items, "source": cached.get("source", "cache")}

    # Try Finnhub live news
    live = _finnhub_news(t, limit=limit)
    if live is not None:
        result = {"ticker": t, "count": len(live), "items": live, "source": "finnhub"}
        _news_cache[t] = (time.time(), {"items": live, "source": "finnhub"})
        return result

    # Fallback to mock
    items = _MOCK_NEWS.get(t, [])[:limit]
    return {"ticker": t, "count": len(items), "items": items, "source": "mock"}


@router.get("/filings")
def get_filings(
    ticker: str = Query(..., min_length=1, max_length=10),
    type: Optional[str] = Query(None, pattern="^(10-K|10-Q|8-K)$"),
    limit: int = Query(5, ge=1, le=20),
) -> Dict[str, Any]:
    # Mock filings — in production, integrate with SEC EDGAR API
    t = ticker.upper()
    filings = [
        {"type": "10-K", "date": "2025-11-01", "description": f"{t} Annual Report FY2025"},
        {"type": "10-Q", "date": "2025-08-01", "description": f"{t} Quarterly Report Q3 2025"},
        {"type": "8-K", "date": "2025-07-15", "description": f"{t} Current Report — Earnings Release"},
    ]
    if type:
        filings = [f for f in filings if f["type"] == type]
    return {"ticker": t, "count": len(filings[:limit]), "filings": filings[:limit]}
