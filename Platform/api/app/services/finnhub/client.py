"""
Async Finnhub API client using httpx.

Methods:
    get_quote(ticker)  -> normalized quote dict
    get_candles(ticker, resolution, from_, to)  -> normalized OHLCV dict
    get_company_profile(ticker) -> company profile dict

All methods:
- Check cache first (serve cached if fresh)
- Call Finnhub via httpx on miss
- Handle 429 by returning stale cache or raising
- Normalize responses to a stable schema
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, Optional

import httpx

from app.services.finnhub.cache import candles_cache, quote_cache
from app.services.finnhub.config import FINNHUB_API_KEY, FINNHUB_BASE_URL, is_configured

logger = logging.getLogger(__name__)

# ─── Ticker validation ───
_TICKER_RE = re.compile(r"^[A-Z0-9.\-]{1,15}$")


def validate_ticker(ticker: str) -> str:
    """
    Validate and normalize a ticker symbol.
    Allows A-Z, 0-9, '.', '-', max length 15.
    Raises ValueError on bad input.
    """
    t = ticker.strip().upper()
    if not _TICKER_RE.match(t):
        raise ValueError(
            f"Invalid ticker symbol: {ticker!r}. "
            "Allowed: A-Z, 0-9, '.', '-', max 15 chars."
        )
    return t


# ─── HTTP client singleton ───
_http_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            base_url=FINNHUB_BASE_URL,
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers={"X-Finnhub-Token": FINNHUB_API_KEY},
        )
    return _http_client


class FinnhubError(Exception):
    """Raised when Finnhub returns an unexpected error."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Finnhub {status_code}: {detail}")


class FinnhubRateLimited(FinnhubError):
    """Raised on 429 — caller should try stale cache."""

    def __init__(self):
        super().__init__(429, "Rate limit reached. Please retry.")


# ─── Quote ───


async def get_quote(ticker: str) -> Dict[str, Any]:
    """
    Fetch a real-time-ish quote from Finnhub.

    Returns:
        {
            "ticker": "AAPL",
            "price": 234.56,
            "change": 3.21,
            "percent_change": 1.39,
            "high": 236.10,
            "low": 231.80,
            "open": 232.00,
            "prev_close": 231.35,
            "ts": 1708099200,
            "source": "finnhub"
        }
    """
    t = validate_ticker(ticker)

    if not is_configured():
        raise FinnhubError(503, "Finnhub is not configured — set FINNHUB_API_KEY")

    # Cache check
    cached = quote_cache.get("quote", t)
    if cached is not None:
        return cached

    # Call Finnhub /quote?symbol=AAPL
    client = _get_client()
    try:
        resp = await client.get("/quote", params={"symbol": t})
    except httpx.HTTPError as exc:
        logger.error("Finnhub quote network error for %s: %s", t, exc)
        stale = quote_cache.get_stale("quote", t)
        if stale is not None:
            logger.info("Serving stale quote cache for %s", t)
            return stale
        raise FinnhubError(502, f"Failed to reach Finnhub: {exc}") from exc

    if resp.status_code == 429:
        stale = quote_cache.get_stale("quote", t)
        if stale is not None:
            logger.info("Rate limited — serving stale quote for %s", t)
            return stale
        raise FinnhubRateLimited()

    if resp.status_code != 200:
        raise FinnhubError(resp.status_code, resp.text[:200])

    data = resp.json()

    # Finnhub returns: c, d, dp, h, l, o, pc, t
    # c=current, d=change, dp=percent change, h=high, l=low, o=open, pc=prev close, t=timestamp
    if data.get("c") is None or data.get("c") == 0:
        raise FinnhubError(404, f"No quote data for ticker: {t}")

    result: Dict[str, Any] = {
        "ticker": t,
        "price": data["c"],
        "change": data["d"],
        "percent_change": data["dp"],
        "high": data["h"],
        "low": data["l"],
        "open": data["o"],
        "prev_close": data["pc"],
        "ts": data["t"],
        "source": "finnhub",
    }

    quote_cache.set(result, "quote", t)
    return result


# ─── Candles ───

_VALID_RESOLUTIONS = {"1", "5", "15", "30", "60", "D", "W", "M"}


async def get_candles(
    ticker: str,
    resolution: str,
    from_ts: int,
    to_ts: int,
) -> Dict[str, Any]:
    """
    Fetch OHLCV candle data from Finnhub.

    Args:
        ticker:     Symbol (e.g. "AAPL")
        resolution: Candle resolution: 1, 5, 15, 30, 60, D, W, M
        from_ts:    Start UNIX timestamp
        to_ts:      End UNIX timestamp

    Returns:
        {
            "ticker": "AAPL",
            "resolution": "D",
            "from": 1707000000,
            "to": 1708000000,
            "t": [...],  # timestamps
            "o": [...],  # open
            "h": [...],  # high
            "l": [...],  # low
            "c": [...],  # close
            "v": [...],  # volume
            "source": "finnhub"
        }
    """
    t = validate_ticker(ticker)

    if resolution not in _VALID_RESOLUTIONS:
        raise ValueError(
            f"Invalid resolution: {resolution!r}. "
            f"Allowed: {', '.join(sorted(_VALID_RESOLUTIONS))}"
        )

    if not is_configured():
        raise FinnhubError(503, "Finnhub is not configured — set FINNHUB_API_KEY")

    # Cache check
    cache_key = ("candles", t, resolution, from_ts, to_ts)
    cached = candles_cache.get(*cache_key)
    if cached is not None:
        return cached

    # Call Finnhub /stock/candle
    client = _get_client()
    params = {
        "symbol": t,
        "resolution": resolution,
        "from": from_ts,
        "to": to_ts,
    }

    try:
        resp = await client.get("/stock/candle", params=params)
    except httpx.HTTPError as exc:
        logger.error("Finnhub candles network error for %s: %s", t, exc)
        stale = candles_cache.get_stale(*cache_key)
        if stale is not None:
            logger.info("Serving stale candles cache for %s", t)
            return stale
        raise FinnhubError(502, f"Failed to reach Finnhub: {exc}") from exc

    if resp.status_code == 429:
        stale = candles_cache.get_stale(*cache_key)
        if stale is not None:
            logger.info("Rate limited — serving stale candles for %s", t)
            return stale
        raise FinnhubRateLimited()

    if resp.status_code != 200:
        raise FinnhubError(resp.status_code, resp.text[:200])

    data = resp.json()

    # Finnhub candle response has "s" status field: "ok" or "no_data"
    if data.get("s") != "ok":
        raise FinnhubError(
            404,
            f"No candle data for {t} ({resolution}, {from_ts}-{to_ts})",
        )

    result: Dict[str, Any] = {
        "ticker": t,
        "resolution": resolution,
        "from": from_ts,
        "to": to_ts,
        "t": data.get("t", []),
        "o": data.get("o", []),
        "h": data.get("h", []),
        "l": data.get("l", []),
        "c": data.get("c", []),
        "v": data.get("v", []),
        "source": "finnhub",
    }

    candles_cache.set(result, *cache_key)
    return result


# ─── Company Profile (optional) ───


async def get_company_profile(ticker: str) -> Dict[str, Any]:
    """
    Fetch company profile from Finnhub /stock/profile2.

    Returns:
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "country": "US",
            "currency": "USD",
            "exchange": "NASDAQ NMS - GLOBAL MARKET",
            "ipo": "1980-12-12",
            "market_cap": 3620000,
            "industry": "Technology",
            "logo": "https://...",
            "weburl": "https://...",
            "source": "finnhub"
        }
    """
    t = validate_ticker(ticker)

    if not is_configured():
        raise FinnhubError(503, "Finnhub is not configured — set FINNHUB_API_KEY")

    # Cache with a longer TTL — profiles don't change often
    cached = quote_cache.get("profile", t)
    if cached is not None:
        return cached

    client = _get_client()
    try:
        resp = await client.get("/stock/profile2", params={"symbol": t})
    except httpx.HTTPError as exc:
        logger.error("Finnhub profile network error for %s: %s", t, exc)
        stale = quote_cache.get_stale("profile", t)
        if stale is not None:
            return stale
        raise FinnhubError(502, f"Failed to reach Finnhub: {exc}") from exc

    if resp.status_code == 429:
        stale = quote_cache.get_stale("profile", t)
        if stale is not None:
            return stale
        raise FinnhubRateLimited()

    if resp.status_code != 200:
        raise FinnhubError(resp.status_code, resp.text[:200])

    data = resp.json()

    if not data.get("name"):
        raise FinnhubError(404, f"No profile data for ticker: {t}")

    result: Dict[str, Any] = {
        "ticker": t,
        "name": data.get("name", ""),
        "country": data.get("country", ""),
        "currency": data.get("currency", ""),
        "exchange": data.get("exchange", ""),
        "ipo": data.get("ipo", ""),
        "market_cap": data.get("marketCapitalization", 0),
        "industry": data.get("finnhubIndustry", ""),
        "logo": data.get("logo", ""),
        "weburl": data.get("weburl", ""),
        "source": "finnhub",
    }

    # Cache profile for 10 minutes
    quote_cache.set(result, "profile", t, ttl=600)
    return result
