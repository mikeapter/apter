"""
Market Data Service — Single source of truth for all quote/price data.

Backward-compatible re-exports from the original market_data.py module.
All existing imports (fetch_quote, fetch_quotes, normalize_symbol, etc.)
continue to work unchanged.

New code should import from submodules:
- app.services.market_data.providers
- app.services.market_data.compute_metrics
- app.services.market_data.schemas
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# ─── Symbol normalization ───

_SYMBOL_RE = re.compile(r"^[A-Z]{1,5}(?:\.[A-Z])?$")


def normalize_symbol(raw: str) -> str:
    """
    Normalize a stock symbol:
    - Strip whitespace, uppercase
    - Convert BRK-B -> BRK.B
    - Remove $ prefix
    """
    s = raw.strip().upper()
    s = s.lstrip("$")
    s = s.replace("-", ".")
    return s


def validate_symbol(symbol: str) -> bool:
    """Check if a normalized symbol is valid."""
    return bool(_SYMBOL_RE.match(symbol))


# ─── In-memory quote cache ───

_quote_cache: Dict[str, dict] = {}
_cache_ttl_regular = 5  # seconds during market hours
_cache_ttl_after = 30
_cache_ttl_closed = 300


def _is_market_open() -> str:
    """Rough market session detection. Returns REGULAR, AFTER_HOURS, PRE_MARKET, or CLOSED."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    weekday = now.weekday()

    if weekday >= 5:  # Weekend
        return "CLOSED"
    if 14 <= hour < 21:
        return "REGULAR"
    if 9 <= hour < 14:
        return "PRE_MARKET"
    if 21 <= hour < 24:
        return "AFTER_HOURS"
    return "CLOSED"


def _cache_ttl() -> int:
    session = _is_market_open()
    if session == "REGULAR":
        return _cache_ttl_regular
    if session in ("AFTER_HOURS", "PRE_MARKET"):
        return _cache_ttl_after
    return _cache_ttl_closed


# ─── Internal stock data (MVP fallback) ───

_STOCK_DB: Dict[str, dict] = {
    "AAPL": {"price": 234.56, "change": 3.21, "change_pct": 1.39, "name": "Apple Inc.", "sector": "Technology", "market_cap": 3580e9},
    "MSFT": {"price": 428.90, "change": 5.67, "change_pct": 1.34, "name": "Microsoft Corporation", "sector": "Technology", "market_cap": 3180e9},
    "NVDA": {"price": 876.32, "change": -12.45, "change_pct": -1.40, "name": "NVIDIA Corporation", "sector": "Technology", "market_cap": 2150e9},
    "GOOGL": {"price": 178.45, "change": 1.23, "change_pct": 0.69, "name": "Alphabet Inc.", "sector": "Technology", "market_cap": 2200e9},
    "AMZN": {"price": 212.78, "change": 4.56, "change_pct": 2.19, "name": "Amazon.com Inc.", "sector": "Consumer Discretionary", "market_cap": 2180e9},
    "META": {"price": 612.34, "change": 8.91, "change_pct": 1.48, "name": "Meta Platforms Inc.", "sector": "Technology", "market_cap": 1560e9},
    "TSLA": {"price": 342.18, "change": -8.76, "change_pct": -2.49, "name": "Tesla Inc.", "sector": "Consumer Discretionary", "market_cap": 1090e9},
    "SPY": {"price": 512.34, "change": 2.45, "change_pct": 0.48, "name": "SPDR S&P 500 ETF Trust", "sector": "Broad Market ETF", "market_cap": None},
    "QQQ": {"price": 438.67, "change": 3.12, "change_pct": 0.72, "name": "Invesco QQQ Trust", "sector": "Technology ETF", "market_cap": None},
    "JPM": {"price": 198.45, "change": 1.89, "change_pct": 0.96, "name": "JPMorgan Chase & Co.", "sector": "Financials", "market_cap": 680e9},
    "BRK.B": {"price": 458.12, "change": 2.34, "change_pct": 0.51, "name": "Berkshire Hathaway Inc.", "sector": "Financials", "market_cap": 1050e9},
    "V": {"price": 312.45, "change": 1.67, "change_pct": 0.54, "name": "Visa Inc.", "sector": "Financials", "market_cap": 580e9},
    "UNH": {"price": 542.18, "change": -3.12, "change_pct": -0.57, "name": "UnitedHealth Group", "sector": "Healthcare", "market_cap": 500e9},
    "JNJ": {"price": 156.78, "change": 0.89, "change_pct": 0.57, "name": "Johnson & Johnson", "sector": "Healthcare", "market_cap": 380e9},
    "WMT": {"price": 178.90, "change": 1.23, "change_pct": 0.69, "name": "Walmart Inc.", "sector": "Consumer Staples", "market_cap": 480e9},
    "XOM": {"price": 108.45, "change": -1.56, "change_pct": -1.42, "name": "Exxon Mobil Corporation", "sector": "Energy", "market_cap": 460e9},
    "PG": {"price": 167.34, "change": 0.78, "change_pct": 0.47, "name": "Procter & Gamble Co.", "sector": "Consumer Staples", "market_cap": 395e9},
    "MA": {"price": 498.12, "change": 3.45, "change_pct": 0.70, "name": "Mastercard Inc.", "sector": "Financials", "market_cap": 460e9},
    "HD": {"price": 389.56, "change": 2.10, "change_pct": 0.54, "name": "The Home Depot Inc.", "sector": "Consumer Discretionary", "market_cap": 390e9},
    "DIS": {"price": 112.34, "change": -0.67, "change_pct": -0.59, "name": "The Walt Disney Company", "sector": "Communication Services", "market_cap": 205e9},
}

# ─── Metric data for scoring (MVP mock with realistic values) ───
# period_end represents the last fiscal quarter end for these metrics

_METRIC_DB: Dict[str, dict] = {
    "AAPL": {
        "quality": {"roe": 171.0, "roic": 56.0, "gross_margin": 46.2, "operating_margin": 31.5, "fcf_margin": 26.8, "asset_turnover": 1.15},
        "value": {"pe_ratio": 29.3, "pb_ratio": 48.5, "ps_ratio": 8.1, "ev_ebitda": 22.4, "fcf_yield": 3.5},
        "growth": {"revenue_growth_yoy": 8.2, "earnings_growth_yoy": 10.5, "fcf_growth_yoy": 12.1, "revenue_growth_3y_cagr": 7.8, "earnings_growth_3y_cagr": 9.2},
        "momentum": {"price_vs_sma50": 3.2, "price_vs_sma200": 8.5, "rsi_14": 58.0, "return_1m": 4.1, "return_3m": 7.8, "return_6m": 12.3},
        "risk": {"volatility_30d": 18.2, "max_drawdown_1y": -12.5, "debt_to_equity": 1.8, "interest_coverage": 42.5, "current_ratio": 0.99, "beta": 1.2},
        "_period_end": "2025-12-28",  # Apple fiscal Q1 2026 (ends late Dec)
    },
    "MSFT": {
        "quality": {"roe": 38.5, "roic": 28.0, "gross_margin": 69.8, "operating_margin": 44.6, "fcf_margin": 33.2, "asset_turnover": 0.52},
        "value": {"pe_ratio": 34.2, "pb_ratio": 12.8, "ps_ratio": 13.2, "ev_ebitda": 25.1, "fcf_yield": 2.9},
        "growth": {"revenue_growth_yoy": 15.2, "earnings_growth_yoy": 18.4, "fcf_growth_yoy": 20.1, "revenue_growth_3y_cagr": 13.5, "earnings_growth_3y_cagr": 16.2},
        "momentum": {"price_vs_sma50": 5.1, "price_vs_sma200": 12.3, "rsi_14": 64.0, "return_1m": 5.8, "return_3m": 10.2, "return_6m": 18.5},
        "risk": {"volatility_30d": 16.5, "max_drawdown_1y": -10.2, "debt_to_equity": 0.42, "interest_coverage": 48.0, "current_ratio": 1.77, "beta": 0.92},
        "_period_end": "2025-12-31",
    },
    "NVDA": {
        "quality": {"roe": 115.0, "roic": 78.0, "gross_margin": 74.5, "operating_margin": 62.3, "fcf_margin": 45.2, "asset_turnover": 1.42},
        "value": {"pe_ratio": 48.7, "pb_ratio": 52.3, "ps_ratio": 28.5, "ev_ebitda": 38.2, "fcf_yield": 1.8},
        "growth": {"revenue_growth_yoy": 122.0, "earnings_growth_yoy": 168.0, "fcf_growth_yoy": 145.0, "revenue_growth_3y_cagr": 55.0, "earnings_growth_3y_cagr": 72.0},
        "momentum": {"price_vs_sma50": -2.5, "price_vs_sma200": 15.0, "rsi_14": 48.0, "return_1m": -3.2, "return_3m": 5.1, "return_6m": 22.0},
        "risk": {"volatility_30d": 42.1, "max_drawdown_1y": -25.3, "debt_to_equity": 0.41, "interest_coverage": 132.0, "current_ratio": 4.17, "beta": 1.68},
        "_period_end": "2026-01-26",  # NVDA fiscal Q4 2026 (ends late Jan)
    },
    "GOOGL": {
        "quality": {"roe": 28.5, "roic": 22.0, "gross_margin": 57.2, "operating_margin": 30.5, "fcf_margin": 22.8, "asset_turnover": 0.68},
        "value": {"pe_ratio": 22.8, "pb_ratio": 6.5, "ps_ratio": 6.8, "ev_ebitda": 16.2, "fcf_yield": 4.5},
        "growth": {"revenue_growth_yoy": 12.5, "earnings_growth_yoy": 28.0, "fcf_growth_yoy": 15.2, "revenue_growth_3y_cagr": 11.0, "earnings_growth_3y_cagr": 18.5},
        "momentum": {"price_vs_sma50": 1.8, "price_vs_sma200": 6.5, "rsi_14": 55.0, "return_1m": 2.1, "return_3m": 5.5, "return_6m": 10.8},
        "risk": {"volatility_30d": 22.4, "max_drawdown_1y": -14.2, "debt_to_equity": 0.06, "interest_coverage": 285.0, "current_ratio": 2.1, "beta": 1.05},
        "_period_end": "2025-12-31",
    },
    "AMZN": {
        "quality": {"roe": 22.8, "roic": 12.5, "gross_margin": 48.5, "operating_margin": 10.5, "fcf_margin": 8.2, "asset_turnover": 1.12},
        "value": {"pe_ratio": 38.1, "pb_ratio": 8.2, "ps_ratio": 3.5, "ev_ebitda": 18.5, "fcf_yield": 2.8},
        "growth": {"revenue_growth_yoy": 12.8, "earnings_growth_yoy": 45.0, "fcf_growth_yoy": 55.0, "revenue_growth_3y_cagr": 11.5, "earnings_growth_3y_cagr": 35.0},
        "momentum": {"price_vs_sma50": 4.2, "price_vs_sma200": 10.5, "rsi_14": 61.0, "return_1m": 5.2, "return_3m": 8.5, "return_6m": 15.2},
        "risk": {"volatility_30d": 26.8, "max_drawdown_1y": -18.5, "debt_to_equity": 0.58, "interest_coverage": 18.5, "current_ratio": 1.05, "beta": 1.15},
        "_period_end": "2025-12-31",
    },
    "META": {
        "quality": {"roe": 33.8, "roic": 25.0, "gross_margin": 81.5, "operating_margin": 41.2, "fcf_margin": 32.5, "asset_turnover": 0.58},
        "value": {"pe_ratio": 24.6, "pb_ratio": 8.5, "ps_ratio": 9.8, "ev_ebitda": 16.8, "fcf_yield": 3.8},
        "growth": {"revenue_growth_yoy": 22.5, "earnings_growth_yoy": 35.0, "fcf_growth_yoy": 28.0, "revenue_growth_3y_cagr": 14.0, "earnings_growth_3y_cagr": 22.0},
        "momentum": {"price_vs_sma50": 3.5, "price_vs_sma200": 18.2, "rsi_14": 59.0, "return_1m": 4.8, "return_3m": 12.5, "return_6m": 25.0},
        "risk": {"volatility_30d": 28.5, "max_drawdown_1y": -16.8, "debt_to_equity": 0.28, "interest_coverage": 62.0, "current_ratio": 2.68, "beta": 1.22},
        "_period_end": "2025-12-31",
    },
    "TSLA": {
        "quality": {"roe": 22.0, "roic": 15.5, "gross_margin": 18.2, "operating_margin": 8.5, "fcf_margin": 5.2, "asset_turnover": 0.92},
        "value": {"pe_ratio": 68.4, "pb_ratio": 14.5, "ps_ratio": 8.5, "ev_ebitda": 42.5, "fcf_yield": 1.2},
        "growth": {"revenue_growth_yoy": 2.5, "earnings_growth_yoy": -15.0, "fcf_growth_yoy": -22.0, "revenue_growth_3y_cagr": 25.0, "earnings_growth_3y_cagr": -5.0},
        "momentum": {"price_vs_sma50": -5.2, "price_vs_sma200": -2.8, "rsi_14": 42.0, "return_1m": -8.5, "return_3m": -12.0, "return_6m": -5.5},
        "risk": {"volatility_30d": 52.3, "max_drawdown_1y": -35.2, "debt_to_equity": 0.08, "interest_coverage": 22.0, "current_ratio": 1.72, "beta": 2.05},
        "_period_end": "2025-12-31",
    },
    "SPY": {
        "quality": {"roe": 18.0, "roic": 12.0, "gross_margin": 35.0, "operating_margin": 15.0, "fcf_margin": 10.0, "asset_turnover": 0.6},
        "value": {"pe_ratio": 21.4, "pb_ratio": 4.5, "ps_ratio": 2.8, "ev_ebitda": 14.5, "fcf_yield": 4.2},
        "growth": {"revenue_growth_yoy": 5.5, "earnings_growth_yoy": 8.2, "fcf_growth_yoy": 6.5, "revenue_growth_3y_cagr": 6.0, "earnings_growth_3y_cagr": 7.5},
        "momentum": {"price_vs_sma50": 2.1, "price_vs_sma200": 7.5, "rsi_14": 56.0, "return_1m": 2.5, "return_3m": 5.0, "return_6m": 10.0},
        "risk": {"volatility_30d": 12.8, "max_drawdown_1y": -8.5, "debt_to_equity": 0.8, "interest_coverage": 12.0, "current_ratio": 1.5, "beta": 1.0},
        "_period_end": "2025-12-31",
    },
    "QQQ": {
        "quality": {"roe": 25.0, "roic": 18.0, "gross_margin": 52.0, "operating_margin": 28.0, "fcf_margin": 18.0, "asset_turnover": 0.7},
        "value": {"pe_ratio": 28.7, "pb_ratio": 8.2, "ps_ratio": 6.5, "ev_ebitda": 20.5, "fcf_yield": 3.2},
        "growth": {"revenue_growth_yoy": 12.5, "earnings_growth_yoy": 15.0, "fcf_growth_yoy": 14.0, "revenue_growth_3y_cagr": 10.5, "earnings_growth_3y_cagr": 13.0},
        "momentum": {"price_vs_sma50": 3.0, "price_vs_sma200": 10.0, "rsi_14": 57.0, "return_1m": 3.2, "return_3m": 7.5, "return_6m": 14.0},
        "risk": {"volatility_30d": 21.3, "max_drawdown_1y": -12.0, "debt_to_equity": 0.5, "interest_coverage": 15.0, "current_ratio": 1.8, "beta": 1.1},
        "_period_end": "2025-12-31",
    },
    "JPM": {
        "quality": {"roe": 17.2, "roic": 3.5, "gross_margin": 62.0, "operating_margin": 38.5, "fcf_margin": 20.0, "asset_turnover": 0.06},
        "value": {"pe_ratio": 12.1, "pb_ratio": 2.0, "ps_ratio": 3.8, "ev_ebitda": 8.5, "fcf_yield": 7.2},
        "growth": {"revenue_growth_yoy": 8.5, "earnings_growth_yoy": 12.0, "fcf_growth_yoy": 10.0, "revenue_growth_3y_cagr": 7.0, "earnings_growth_3y_cagr": 10.0},
        "momentum": {"price_vs_sma50": 2.8, "price_vs_sma200": 15.0, "rsi_14": 60.0, "return_1m": 3.5, "return_3m": 8.0, "return_6m": 18.0},
        "risk": {"volatility_30d": 14.8, "max_drawdown_1y": -8.0, "debt_to_equity": 1.2, "interest_coverage": 3.5, "current_ratio": 0.85, "beta": 1.08},
        "_period_end": "2025-12-31",
    },
}


def get_stock_metrics(symbol: str) -> Optional[dict]:
    """Get all metric categories for a symbol. Returns None if unknown."""
    return _METRIC_DB.get(symbol)


def get_stock_db() -> Dict[str, dict]:
    """Get the full stock database (for provider use)."""
    return _STOCK_DB


def get_metric_db() -> Dict[str, dict]:
    """Get the full metric database (for provider use)."""
    return _METRIC_DB


def _finnhub_quote(symbol: str) -> dict | None:
    """Fetch a live quote from Finnhub. Returns None on failure."""
    key = os.getenv("FINNHUB_API_KEY")
    if not key:
        return None
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": symbol, "token": key},
            )
        r.raise_for_status()
        d = r.json()
        if d.get("c") and d["c"] > 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            return {
                "symbol": symbol,
                "price": round(d["c"], 2),
                "change": round(d.get("d") or 0, 2),
                "change_pct": round(d.get("dp") or 0, 2),
                "as_of": now_iso,
                "session": _is_market_open(),
                "delay_seconds": 0,
                "source": "finnhub",
            }
    except Exception:
        logger.debug("Finnhub quote failed for %s", symbol, exc_info=True)
    return None


def fetch_quote(symbol: str) -> dict:
    """
    Fetch a single quote. Uses cache if fresh.
    Tries Finnhub live data first, falls back to internal DB.
    Returns structured quote dict with all required fields.
    """
    symbol = normalize_symbol(symbol)

    # Check cache
    cached = _quote_cache.get(symbol)
    ttl = _cache_ttl()
    if cached and (time.time() - cached["_cached_at"]) < ttl:
        result = {k: v for k, v in cached.items() if k != "_cached_at"}
        return result

    # Try Finnhub live quote
    live = _finnhub_quote(symbol)
    if live:
        _quote_cache[symbol] = {**live, "_cached_at": time.time()}
        return live

    session = _is_market_open()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Fallback: internal DB
    stock = _STOCK_DB.get(symbol)
    if stock:
        quote = {
            "symbol": symbol,
            "price": stock["price"],
            "change": stock["change"],
            "change_pct": stock["change_pct"],
            "as_of": now_iso,
            "session": session,
            "delay_seconds": 0,
            "source": "apter_internal",
        }
        _quote_cache[symbol] = {**quote, "_cached_at": time.time()}
        return quote

    # No quote available
    return {
        "symbol": symbol,
        "price": 0,
        "change": 0,
        "change_pct": 0,
        "as_of": now_iso,
        "session": session,
        "delay_seconds": 0,
        "source": "none",
        "error": "NO_QUOTE",
        "message": f"No quote data available for {symbol}",
    }


def fetch_quotes(symbols: List[str]) -> Tuple[Dict[str, dict], dict]:
    """
    Fetch quotes for multiple symbols.
    Returns (quotes_dict, meta_dict).
    """
    quotes = {}
    max_delay = 0

    for raw_sym in symbols:
        sym = normalize_symbol(raw_sym)
        if not validate_symbol(sym):
            quotes[sym] = {
                "symbol": sym,
                "error": "INVALID_SYMBOL",
                "message": f"Invalid symbol format: {sym}",
                "as_of": datetime.now(timezone.utc).isoformat(),
            }
            continue

        q = fetch_quote(sym)
        quotes[sym] = q
        max_delay = max(max_delay, q.get("delay_seconds", 0))

    meta = {
        "serverTime": datetime.now(timezone.utc).isoformat(),
        "maxDelaySeconds": max_delay,
        "symbolCount": len(symbols),
    }

    return quotes, meta


def get_stock_name(symbol: str) -> str:
    """Get company name for a symbol."""
    stock = _STOCK_DB.get(normalize_symbol(symbol))
    return stock["name"] if stock else f"{symbol} (Unknown)"
