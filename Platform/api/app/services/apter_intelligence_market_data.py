"""
Apter Intelligence — Live Market Data Fetcher.

Isolated data layer for the Apter Intelligence chat endpoint.
Does NOT share code with the existing market_data.py or data.py routes.

Provider priority:
  1. POLYGON_API_KEY  → Polygon.io REST v2/v3
  2. FMP_API_KEY      → Financial Modeling Prep
  3. Neither          → returns "unavailable" stubs
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_TIMEOUT = 8.0  # seconds per request
_MAX_RETRIES = 2
_BACKOFF_BASE = 0.5  # seconds

_POLYGON_KEY: Optional[str] = None
_FMP_KEY: Optional[str] = None


def _load_keys() -> None:
    global _POLYGON_KEY, _FMP_KEY
    _POLYGON_KEY = os.getenv("POLYGON_API_KEY", "").strip() or None
    _FMP_KEY = os.getenv("FMP_API_KEY", "").strip() or None


def _provider() -> str:
    _load_keys()
    if _POLYGON_KEY:
        return "polygon"
    if _FMP_KEY:
        return "fmp"
    return "none"


# ---------------------------------------------------------------------------
# Ticker sanitization
# ---------------------------------------------------------------------------

_TICKER_RE = re.compile(r"^[A-Z]{1,5}(?:[.\-][A-Z]{1,2})?$")


def sanitize_ticker(raw: str) -> Optional[str]:
    t = raw.strip().upper().replace("-", ".")
    if _TICKER_RE.match(t):
        return t
    return None


# ---------------------------------------------------------------------------
# HTTP helpers with retry + backoff
# ---------------------------------------------------------------------------


async def _request(
    client: httpx.AsyncClient, url: str, params: dict | None = None
) -> Optional[dict]:
    """GET with retry, backoff, and 429 handling."""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = await client.get(url, params=params, timeout=_TIMEOUT)
            if resp.status_code == 429:
                wait = _BACKOFF_BASE * (2**attempt)
                logger.warning("Rate limited (429) on %s — retrying in %.1fs", url, wait)
                await asyncio.sleep(wait)
                continue
            if resp.status_code >= 500:
                wait = _BACKOFF_BASE * (2**attempt)
                logger.warning("Server error %d on %s — retrying in %.1fs", resp.status_code, url, wait)
                await asyncio.sleep(wait)
                continue
            if resp.status_code != 200:
                logger.warning("HTTP %d from %s", resp.status_code, url)
                return None
            return resp.json()
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            if attempt < _MAX_RETRIES:
                wait = _BACKOFF_BASE * (2**attempt)
                logger.warning("Request error %s — retrying in %.1fs", exc, wait)
                await asyncio.sleep(wait)
            else:
                logger.error("Request failed after retries: %s", exc)
                return None
    return None


# ---------------------------------------------------------------------------
# Polygon.io adapters
# ---------------------------------------------------------------------------


async def _polygon_quote(client: httpx.AsyncClient, ticker: str) -> dict:
    data = await _request(
        client,
        f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev",
        params={"adjusted": "true", "apiKey": _POLYGON_KEY},
    )
    if not data or not data.get("results"):
        return {"ticker": ticker, "source": "polygon", "error": "NO_QUOTE"}
    r = data["results"][0]
    return {
        "ticker": ticker,
        "price": r.get("c", 0),
        "open": r.get("o", 0),
        "high": r.get("h", 0),
        "low": r.get("l", 0),
        "volume": r.get("v", 0),
        "change": round(r.get("c", 0) - r.get("o", 0), 2),
        "source": "polygon",
    }


async def _polygon_profile(client: httpx.AsyncClient, ticker: str) -> dict:
    data = await _request(
        client,
        f"https://api.polygon.io/v3/reference/tickers/{ticker}",
        params={"apiKey": _POLYGON_KEY},
    )
    if not data or not data.get("results"):
        return {"ticker": ticker, "source": "polygon", "error": "NO_PROFILE"}
    r = data["results"]
    return {
        "ticker": ticker,
        "name": r.get("name", ticker),
        "market_cap": r.get("market_cap"),
        "description": (r.get("description") or "")[:300],
        "sector": r.get("sic_description", ""),
        "homepage": r.get("homepage_url", ""),
        "source": "polygon",
    }


async def _polygon_fundamentals(client: httpx.AsyncClient, ticker: str) -> dict:
    data = await _request(
        client,
        f"https://api.polygon.io/vX/reference/financials",
        params={
            "ticker": ticker,
            "limit": "1",
            "timeframe": "annual",
            "apiKey": _POLYGON_KEY,
        },
    )
    if not data or not data.get("results"):
        return {"ticker": ticker, "source": "polygon", "error": "NO_FUNDAMENTALS"}
    r = data["results"][0]
    fs = r.get("financials", {})
    inc = fs.get("income_statement", {})
    bs = fs.get("balance_sheet", {})
    return {
        "ticker": ticker,
        "period": r.get("fiscal_period", ""),
        "fiscal_year": r.get("fiscal_year", ""),
        "revenue": inc.get("revenues", {}).get("value"),
        "net_income": inc.get("net_income_loss", {}).get("value"),
        "total_assets": bs.get("assets", {}).get("value"),
        "total_equity": bs.get("equity", {}).get("value"),
        "source": "polygon",
    }


async def _polygon_earnings(client: httpx.AsyncClient, ticker: str) -> dict:
    # Polygon doesn't have a direct earnings-surprise endpoint on free tier,
    # so we re-use financials quarterly
    data = await _request(
        client,
        f"https://api.polygon.io/vX/reference/financials",
        params={
            "ticker": ticker,
            "limit": "4",
            "timeframe": "quarterly",
            "apiKey": _POLYGON_KEY,
        },
    )
    if not data or not data.get("results"):
        return {"ticker": ticker, "source": "polygon", "error": "NO_EARNINGS"}
    quarters = []
    for r in data["results"]:
        inc = r.get("financials", {}).get("income_statement", {})
        quarters.append({
            "period": r.get("fiscal_period", ""),
            "fiscal_year": r.get("fiscal_year", ""),
            "revenue": inc.get("revenues", {}).get("value"),
            "eps": inc.get("basic_earnings_per_share", {}).get("value"),
        })
    return {"ticker": ticker, "quarters": quarters, "source": "polygon"}


# ---------------------------------------------------------------------------
# FMP adapters
# ---------------------------------------------------------------------------


async def _fmp_quote(client: httpx.AsyncClient, ticker: str) -> dict:
    data = await _request(
        client,
        f"https://financialmodelingprep.com/api/v3/quote/{ticker}",
        params={"apikey": _FMP_KEY},
    )
    if not data or not isinstance(data, list) or len(data) == 0:
        return {"ticker": ticker, "source": "fmp", "error": "NO_QUOTE"}
    r = data[0]
    return {
        "ticker": ticker,
        "price": r.get("price", 0),
        "open": r.get("open", 0),
        "high": r.get("dayHigh", 0),
        "low": r.get("dayLow", 0),
        "volume": r.get("volume", 0),
        "change": r.get("change", 0),
        "change_pct": r.get("changesPercentage", 0),
        "pe_ratio": r.get("pe"),
        "market_cap": r.get("marketCap"),
        "source": "fmp",
    }


async def _fmp_profile(client: httpx.AsyncClient, ticker: str) -> dict:
    data = await _request(
        client,
        f"https://financialmodelingprep.com/api/v3/profile/{ticker}",
        params={"apikey": _FMP_KEY},
    )
    if not data or not isinstance(data, list) or len(data) == 0:
        return {"ticker": ticker, "source": "fmp", "error": "NO_PROFILE"}
    r = data[0]
    return {
        "ticker": ticker,
        "name": r.get("companyName", ticker),
        "market_cap": r.get("mktCap"),
        "description": (r.get("description") or "")[:300],
        "sector": r.get("sector", ""),
        "industry": r.get("industry", ""),
        "source": "fmp",
    }


async def _fmp_fundamentals(client: httpx.AsyncClient, ticker: str) -> dict:
    data = await _request(
        client,
        f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}",
        params={"limit": "1", "apikey": _FMP_KEY},
    )
    if not data or not isinstance(data, list) or len(data) == 0:
        return {"ticker": ticker, "source": "fmp", "error": "NO_FUNDAMENTALS"}
    r = data[0]
    return {
        "ticker": ticker,
        "period": r.get("period", ""),
        "fiscal_year": r.get("calendarYear", ""),
        "revenue": r.get("revenue"),
        "net_income": r.get("netIncome"),
        "gross_profit": r.get("grossProfit"),
        "operating_income": r.get("operatingIncome"),
        "eps": r.get("eps"),
        "source": "fmp",
    }


async def _fmp_earnings(client: httpx.AsyncClient, ticker: str) -> dict:
    data = await _request(
        client,
        f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}",
        params={"period": "quarter", "limit": "4", "apikey": _FMP_KEY},
    )
    if not data or not isinstance(data, list) or len(data) == 0:
        return {"ticker": ticker, "source": "fmp", "error": "NO_EARNINGS"}
    quarters = []
    for r in data:
        quarters.append({
            "period": r.get("period", ""),
            "fiscal_year": r.get("calendarYear", ""),
            "revenue": r.get("revenue"),
            "eps": r.get("eps"),
            "net_income": r.get("netIncome"),
        })
    return {"ticker": ticker, "quarters": quarters, "source": "fmp"}


# ---------------------------------------------------------------------------
# Unavailable stubs
# ---------------------------------------------------------------------------


def _unavailable(ticker: str, endpoint: str) -> dict:
    return {
        "ticker": ticker,
        "source": "none",
        "error": "UNAVAILABLE",
        "message": "Live data temporarily unavailable.",
    }


# ---------------------------------------------------------------------------
# Public API — provider-agnostic
# ---------------------------------------------------------------------------


async def get_quote(ticker: str) -> dict:
    provider = _provider()
    async with httpx.AsyncClient() as client:
        if provider == "polygon":
            return await _polygon_quote(client, ticker)
        if provider == "fmp":
            return await _fmp_quote(client, ticker)
    return _unavailable(ticker, "quote")


async def get_profile(ticker: str) -> dict:
    provider = _provider()
    async with httpx.AsyncClient() as client:
        if provider == "polygon":
            return await _polygon_profile(client, ticker)
        if provider == "fmp":
            return await _fmp_profile(client, ticker)
    return _unavailable(ticker, "profile")


async def get_fundamentals(ticker: str) -> dict:
    provider = _provider()
    async with httpx.AsyncClient() as client:
        if provider == "polygon":
            return await _polygon_fundamentals(client, ticker)
        if provider == "fmp":
            return await _fmp_fundamentals(client, ticker)
    return _unavailable(ticker, "fundamentals")


async def get_earnings(ticker: str) -> dict:
    provider = _provider()
    async with httpx.AsyncClient() as client:
        if provider == "polygon":
            return await _polygon_earnings(client, ticker)
        if provider == "fmp":
            return await _fmp_earnings(client, ticker)
    return _unavailable(ticker, "earnings")


async def get_all_data(ticker: str) -> Dict[str, Any]:
    """Fetch quote, profile, fundamentals, and earnings concurrently."""
    quote, profile, fundamentals, earnings = await asyncio.gather(
        get_quote(ticker),
        get_profile(ticker),
        get_fundamentals(ticker),
        get_earnings(ticker),
        return_exceptions=True,
    )

    def _safe(val: Any) -> dict:
        if isinstance(val, Exception):
            logger.warning("Data fetch exception: %s", val)
            return {"error": str(val)}
        return val

    return {
        "quote": _safe(quote),
        "profile": _safe(profile),
        "fundamentals": _safe(fundamentals),
        "earnings": _safe(earnings),
    }


async def build_context(tickers: List[str]) -> Dict[str, Any]:
    """
    Build a combined context dict for all requested tickers.
    Returns {ticker: {quote, profile, fundamentals, earnings}, ...} + meta.
    """
    now = datetime.now(timezone.utc).isoformat()
    provider = _provider()

    results = await asyncio.gather(
        *(get_all_data(t) for t in tickers),
        return_exceptions=True,
    )

    context: Dict[str, Any] = {}
    has_live = False

    for ticker, result in zip(tickers, results):
        if isinstance(result, Exception):
            context[ticker] = {"error": str(result)}
        else:
            context[ticker] = result
            # Check if at least one section has live data
            for section in result.values():
                if isinstance(section, dict) and section.get("source") not in ("none", None):
                    if "error" not in section:
                        has_live = True

    data_quality = "live" if has_live else ("partial" if provider != "none" else "unavailable")

    return {
        "tickers": context,
        "meta": {
            "provider": provider,
            "data_quality": data_quality,
            "fetched_at": now,
        },
    }
