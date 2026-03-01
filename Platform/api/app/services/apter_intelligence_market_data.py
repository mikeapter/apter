"""
Apter Intelligence — Live Market Data Fetcher.

Isolated data layer for the Apter Intelligence chat endpoint.
Does NOT share code with the existing market_data.py or data.py routes.

Provider priority:
  1. FINNHUB_API_KEY   → Finnhub.io
  2. POLYGON_API_KEY   → Polygon.io REST v2/v3
  3. FMP_API_KEY        → Financial Modeling Prep
  4. None configured    → returns "unavailable" stubs
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

_FINNHUB_KEY: Optional[str] = None
_POLYGON_KEY: Optional[str] = None
_FMP_KEY: Optional[str] = None


def _load_keys() -> None:
    global _FINNHUB_KEY, _POLYGON_KEY, _FMP_KEY
    _FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "").strip() or None
    _POLYGON_KEY = os.getenv("POLYGON_API_KEY", "").strip() or None
    _FMP_KEY = os.getenv("FMP_API_KEY", "").strip() or None


def _provider() -> str:
    _load_keys()
    if _FINNHUB_KEY:
        logger.info("[Apter Intelligence] Provider: finnhub (key length=%d)", len(_FINNHUB_KEY))
        return "finnhub"
    if _POLYGON_KEY:
        logger.info("[Apter Intelligence] Provider: polygon")
        return "polygon"
    if _FMP_KEY:
        logger.info("[Apter Intelligence] Provider: fmp")
        return "fmp"
    logger.warning(
        "[Apter Intelligence] No data provider configured — "
        "FINNHUB_API_KEY=%s, POLYGON_API_KEY=%s, FMP_API_KEY=%s",
        "SET" if os.getenv("FINNHUB_API_KEY") else "EMPTY",
        "SET" if os.getenv("POLYGON_API_KEY") else "EMPTY",
        "SET" if os.getenv("FMP_API_KEY") else "EMPTY",
    )
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


async def _request_list(
    client: httpx.AsyncClient, url: str, params: dict | None = None
) -> Optional[list]:
    """Same as _request but expects a JSON list response."""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = await client.get(url, params=params, timeout=_TIMEOUT)
            if resp.status_code == 429:
                wait = _BACKOFF_BASE * (2**attempt)
                await asyncio.sleep(wait)
                continue
            if resp.status_code >= 500:
                wait = _BACKOFF_BASE * (2**attempt)
                await asyncio.sleep(wait)
                continue
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data if isinstance(data, list) else None
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_BACKOFF_BASE * (2**attempt))
            else:
                logger.error("Request failed after retries: %s", exc)
                return None
    return None


# ---------------------------------------------------------------------------
# Finnhub adapters
# ---------------------------------------------------------------------------


async def _finnhub_quote(client: httpx.AsyncClient, ticker: str) -> dict:
    data = await _request(
        client,
        "https://finnhub.io/api/v1/quote",
        params={"symbol": ticker, "token": _FINNHUB_KEY},
    )
    if not data or data.get("c") is None or data.get("c") == 0:
        return {"ticker": ticker, "source": "finnhub", "error": "NO_QUOTE"}
    return {
        "ticker": ticker,
        "price": data.get("c", 0),
        "open": data.get("o", 0),
        "high": data.get("h", 0),
        "low": data.get("l", 0),
        "prev_close": data.get("pc", 0),
        "change": data.get("d", 0),
        "change_pct": data.get("dp", 0),
        "source": "finnhub",
    }


async def _finnhub_profile(client: httpx.AsyncClient, ticker: str) -> dict:
    data = await _request(
        client,
        "https://finnhub.io/api/v1/stock/profile2",
        params={"symbol": ticker, "token": _FINNHUB_KEY},
    )
    if not data or not data.get("name"):
        return {"ticker": ticker, "source": "finnhub", "error": "NO_PROFILE"}
    return {
        "ticker": ticker,
        "name": data.get("name", ticker),
        "market_cap": data.get("marketCapitalization"),
        "sector": data.get("finnhubIndustry", ""),
        "country": data.get("country", ""),
        "exchange": data.get("exchange", ""),
        "ipo_date": data.get("ipo", ""),
        "homepage": data.get("weburl", ""),
        "source": "finnhub",
    }


async def _finnhub_fundamentals(client: httpx.AsyncClient, ticker: str) -> dict:
    data = await _request(
        client,
        "https://finnhub.io/api/v1/stock/metric",
        params={"symbol": ticker, "metric": "all", "token": _FINNHUB_KEY},
    )
    if not data or not data.get("metric"):
        return {"ticker": ticker, "source": "finnhub", "error": "NO_FUNDAMENTALS"}
    m = data["metric"]
    return {
        "ticker": ticker,
        "pe_ratio": m.get("peNormalizedAnnual"),
        "pb_ratio": m.get("pbAnnual"),
        "ps_ratio": m.get("psAnnual"),
        "dividend_yield": m.get("dividendYieldIndicatedAnnual"),
        "roe": m.get("roeTTM"),
        "roa": m.get("roaTTM"),
        "gross_margin": m.get("grossMarginTTM"),
        "operating_margin": m.get("operatingMarginTTM"),
        "net_margin": m.get("netProfitMarginTTM"),
        "debt_to_equity": m.get("totalDebt/totalEquityAnnual"),
        "current_ratio": m.get("currentRatioAnnual"),
        "revenue_growth": m.get("revenueGrowthTTMYoy"),
        "eps_growth": m.get("epsGrowthTTMYoy"),
        "52w_high": m.get("52WeekHigh"),
        "52w_low": m.get("52WeekLow"),
        "beta": m.get("beta"),
        "market_cap": m.get("marketCapitalization"),
        "source": "finnhub",
    }


async def _finnhub_earnings(client: httpx.AsyncClient, ticker: str) -> dict:
    data = await _request_list(
        client,
        "https://finnhub.io/api/v1/stock/earnings",
        params={"symbol": ticker, "limit": 4, "token": _FINNHUB_KEY},
    )
    if not data:
        return {"ticker": ticker, "source": "finnhub", "error": "NO_EARNINGS"}
    quarters = []
    for r in data[:4]:
        quarters.append({
            "period": r.get("period", ""),
            "actual_eps": r.get("actual"),
            "estimate_eps": r.get("estimate"),
            "surprise": r.get("surprise"),
            "surprise_pct": r.get("surprisePercent"),
        })
    return {"ticker": ticker, "quarters": quarters, "source": "finnhub"}


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
        "https://api.polygon.io/vX/reference/financials",
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
    data = await _request(
        client,
        "https://api.polygon.io/vX/reference/financials",
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
    data = await _request_list(
        client,
        f"https://financialmodelingprep.com/api/v3/quote/{ticker}",
        params={"apikey": _FMP_KEY},
    )
    if not data or len(data) == 0:
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
    data = await _request_list(
        client,
        f"https://financialmodelingprep.com/api/v3/profile/{ticker}",
        params={"apikey": _FMP_KEY},
    )
    if not data or len(data) == 0:
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
    data = await _request_list(
        client,
        f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}",
        params={"limit": "1", "apikey": _FMP_KEY},
    )
    if not data or len(data) == 0:
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
    data = await _request_list(
        client,
        f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}",
        params={"period": "quarter", "limit": "4", "apikey": _FMP_KEY},
    )
    if not data or len(data) == 0:
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
# Finnhub symbol search (company name → ticker resolution)
# ---------------------------------------------------------------------------


async def search_symbol(query: str) -> Optional[str]:
    """
    Use Finnhub /search to resolve a company name or keyword to a ticker symbol.
    Returns the best-matching US stock ticker, or None.
    """
    _load_keys()
    if not _FINNHUB_KEY:
        logger.warning("[Apter Intelligence] Cannot search symbols — no FINNHUB_API_KEY")
        return None

    try:
        async with httpx.AsyncClient() as client:
            data = await _request(
                client,
                "https://finnhub.io/api/v1/search",
                params={"q": query, "token": _FINNHUB_KEY},
            )
        if not data or not data.get("result"):
            logger.info("[Apter Intelligence] Symbol search for '%s' returned no results", query)
            return None

        # Prefer "Common Stock" types on major US exchanges
        for r in data["result"]:
            symbol = r.get("symbol", "")
            rtype = r.get("type", "")
            # Skip non-stock results, ADRs with suffixes, crypto, etc.
            if rtype in ("Common Stock", "EQS") and "." not in symbol:
                logger.info("[Apter Intelligence] Symbol search '%s' → %s (%s)", query, symbol, r.get("description", ""))
                return symbol

        # Fallback: return first result regardless of type
        first = data["result"][0]
        symbol = first.get("symbol", "")
        if symbol and "." not in symbol:
            logger.info("[Apter Intelligence] Symbol search '%s' → %s (fallback)", query, symbol)
            return symbol

        return None
    except Exception as exc:
        logger.error("[Apter Intelligence] Symbol search error for '%s': %s", query, exc)
        return None


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

_DISPATCH = {
    "finnhub": {
        "quote": _finnhub_quote,
        "profile": _finnhub_profile,
        "fundamentals": _finnhub_fundamentals,
        "earnings": _finnhub_earnings,
    },
    "polygon": {
        "quote": _polygon_quote,
        "profile": _polygon_profile,
        "fundamentals": _polygon_fundamentals,
        "earnings": _polygon_earnings,
    },
    "fmp": {
        "quote": _fmp_quote,
        "profile": _fmp_profile,
        "fundamentals": _fmp_fundamentals,
        "earnings": _fmp_earnings,
    },
}


async def _fetch(endpoint: str, ticker: str) -> dict:
    provider = _provider()
    fns = _DISPATCH.get(provider)
    if not fns:
        logger.warning("[Apter Intelligence] No dispatch for provider=%s, ticker=%s, endpoint=%s", provider, ticker, endpoint)
        return _unavailable(ticker, endpoint)
    try:
        async with httpx.AsyncClient() as client:
            result = await fns[endpoint](client, ticker)
            if result.get("error"):
                logger.warning("[Apter Intelligence] %s/%s/%s returned error: %s", provider, ticker, endpoint, result.get("error"))
            return result
    except Exception as exc:
        logger.error("[Apter Intelligence] Exception fetching %s/%s/%s: %s", provider, ticker, endpoint, exc)
        return _unavailable(ticker, endpoint)


async def get_quote(ticker: str) -> dict:
    return await _fetch("quote", ticker)


async def get_profile(ticker: str) -> dict:
    return await _fetch("profile", ticker)


async def get_fundamentals(ticker: str) -> dict:
    return await _fetch("fundamentals", ticker)


async def get_earnings(ticker: str) -> dict:
    return await _fetch("earnings", ticker)


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

    logger.info(
        "[Apter Intelligence] build_context: tickers=%s provider=%s data_quality=%s has_live=%s",
        tickers, provider, data_quality, has_live,
    )

    return {
        "tickers": context,
        "meta": {
            "provider": provider,
            "data_quality": data_quality,
            "fetched_at": now,
        },
    }
