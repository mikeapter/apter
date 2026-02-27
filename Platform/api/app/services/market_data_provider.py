"""
Deterministic market data provider.

Design goals:
- Fetch quotes for a list of symbols.
- Compute change and change_percent from price & previous_close.
- Validate all numeric values.
- Provide timestamps and structured errors.
- Prefer RapidAPI Yahoo Finance if key present; otherwise use public query1 endpoint.
"""

from __future__ import annotations

import os
import time
import math
import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple

import httpx

logger = logging.getLogger(__name__)


# ─── Data classes ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    previous_close: float
    change: float
    change_percent: float
    day_high: Optional[float]
    day_low: Optional[float]
    timestamp_utc: str  # ISO string from provider or generated at fetch time


@dataclass(frozen=True)
class QuoteError:
    symbol: str
    error: str


# ─── Protocol for swappable providers ───────────────────────────────────────

class MarketDataProvider(Protocol):
    async def quote(self, symbols: List[str]) -> Tuple[Dict[str, Quote], List[QuoteError]]:
        ...


# ─── Validation helpers ────────────────────────────────────────────────────

def _is_finite_number(x: Any) -> bool:
    """Check if a value is a finite number (not NaN, not inf)."""
    try:
        v = float(x)
        return math.isfinite(v)
    except Exception:
        return False


def _to_float_or_none(x: Any) -> Optional[float]:
    """Safely convert to float, returning None on failure."""
    if x is None:
        return None
    return float(x) if _is_finite_number(x) else None


def _compute_change(price: float, prev: float) -> Tuple[float, float]:
    """Compute absolute change and percent change from price and previous close."""
    change = price - prev
    if prev == 0:
        return change, float("nan")
    pct = (change / prev) * 100.0
    return change, pct


# ─── HTTP helper with retries ──────────────────────────────────────────────

async def _request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: Dict[str, str],
    params: Dict[str, Any],
    timeout: float = 12.0,
    retries: int = 2,
) -> httpx.Response:
    """Make an HTTP request with exponential backoff retries on 429/5xx."""
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            resp = await client.request(
                method, url, headers=headers, params=params, timeout=timeout,
            )
            # Retry on 429 / 5xx
            if resp.status_code in (429, 500, 502, 503, 504):
                raise httpx.HTTPStatusError(
                    f"retryable status {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            return resp
        except Exception as e:
            last_exc = e
            backoff = 0.6 * (2 ** attempt)
            logger.warning(
                "Market data request failed (attempt %s/%s): %s; backoff=%.2fs",
                attempt + 1, retries + 1, e, backoff,
            )
            await asyncio.sleep(backoff)
    assert last_exc is not None
    raise last_exc


# ─── Yahoo Finance provider ────────────────────────────────────────────────

class YahooFinanceProvider:
    """
    Uses Yahoo Finance quote API.

    Priority order:
    1) RapidAPI (if YF_RAPIDAPI_KEY set): apidojo endpoint (more stable for some deployments)
    2) Public endpoint: https://query1.finance.yahoo.com/v7/finance/quote
    """

    def __init__(self) -> None:
        self.rapid_key = os.getenv("YF_RAPIDAPI_KEY", "").strip()
        self.rapid_host = os.getenv(
            "YF_RAPIDAPI_HOST",
            "apidojo-yahoo-finance-v1.p.rapidapi.com",
        ).strip()
        self.user_agent = os.getenv(
            "USER_AGENT",
            "ApterFinancial/1.0 (+https://apterfinancial.com)",
        ).strip()

    async def quote(
        self, symbols: List[str],
    ) -> Tuple[Dict[str, Quote], List[QuoteError]]:
        symbols = [s.strip().upper() for s in symbols if s and s.strip()]
        if not symbols:
            return {}, [QuoteError(symbol="*", error="No symbols provided")]

        if self.rapid_key:
            return await self._quote_rapid(symbols)
        return await self._quote_public(symbols)

    # ── Public Yahoo Finance endpoint ───────────────────────────────────

    async def _quote_public(
        self, symbols: List[str],
    ) -> Tuple[Dict[str, Quote], List[QuoteError]]:
        url = "https://query1.finance.yahoo.com/v7/finance/quote"
        params = {"symbols": ",".join(symbols)}
        headers = {"User-Agent": self.user_agent}

        quotes: Dict[str, Quote] = {}
        errors: List[QuoteError] = []

        async with httpx.AsyncClient() as client:
            resp = await _request_with_retries(
                client, "GET", url, headers=headers, params=params,
            )
            if resp.status_code != 200:
                return {}, [
                    QuoteError(
                        symbol="*",
                        error=f"Yahoo public quote failed: {resp.status_code}",
                    ),
                ]
            data = resp.json()
            result = (data.get("quoteResponse") or {}).get("result") or []

        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        seen: set[str] = set()

        for item in result:
            sym = (item.get("symbol") or "").upper()
            if not sym:
                continue
            seen.add(sym)

            price = item.get("regularMarketPrice")
            prev = item.get("regularMarketPreviousClose")
            if not _is_finite_number(price) or not _is_finite_number(prev):
                errors.append(
                    QuoteError(symbol=sym, error="Missing/invalid price or previous close"),
                )
                continue

            price_f = float(price)
            prev_f = float(prev)
            chg, pct = _compute_change(price_f, prev_f)
            day_high = _to_float_or_none(item.get("regularMarketDayHigh"))
            day_low = _to_float_or_none(item.get("regularMarketDayLow"))

            quotes[sym] = Quote(
                symbol=sym,
                price=price_f,
                previous_close=prev_f,
                change=float(chg),
                change_percent=float(pct),
                day_high=day_high,
                day_low=day_low,
                timestamp_utc=now_iso,
            )

        # Report explicitly missing symbols
        for sym in symbols:
            if sym not in seen:
                errors.append(
                    QuoteError(symbol=sym, error="Symbol not returned by provider"),
                )

        return quotes, errors

    # ── RapidAPI Yahoo Finance endpoint ─────────────────────────────────

    async def _quote_rapid(
        self, symbols: List[str],
    ) -> Tuple[Dict[str, Quote], List[QuoteError]]:
        url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/market/v2/get-quotes"
        params = {"region": "US", "symbols": ",".join(symbols)}
        headers = {
            "X-RapidAPI-Key": self.rapid_key,
            "X-RapidAPI-Host": self.rapid_host,
            "User-Agent": self.user_agent,
        }

        quotes: Dict[str, Quote] = {}
        errors: List[QuoteError] = []

        async with httpx.AsyncClient() as client:
            resp = await _request_with_retries(
                client, "GET", url, headers=headers, params=params,
            )
            if resp.status_code != 200:
                return {}, [
                    QuoteError(
                        symbol="*",
                        error=f"RapidAPI quote failed: {resp.status_code}",
                    ),
                ]
            data = resp.json()
            result = (data.get("quoteResponse") or {}).get("result") or []

        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        seen: set[str] = set()

        for item in result:
            sym = (item.get("symbol") or "").upper()
            if not sym:
                continue
            seen.add(sym)

            price = item.get("regularMarketPrice")
            prev = item.get("regularMarketPreviousClose")
            if not _is_finite_number(price) or not _is_finite_number(prev):
                errors.append(
                    QuoteError(symbol=sym, error="Missing/invalid price or previous close"),
                )
                continue

            price_f = float(price)
            prev_f = float(prev)
            chg, pct = _compute_change(price_f, prev_f)
            day_high = _to_float_or_none(item.get("regularMarketDayHigh"))
            day_low = _to_float_or_none(item.get("regularMarketDayLow"))

            quotes[sym] = Quote(
                symbol=sym,
                price=price_f,
                previous_close=prev_f,
                change=float(chg),
                change_percent=float(pct),
                day_high=day_high,
                day_low=day_low,
                timestamp_utc=now_iso,
            )

        for sym in symbols:
            if sym not in seen:
                errors.append(
                    QuoteError(symbol=sym, error="Symbol not returned by provider"),
                )

        return quotes, errors


# ─── Factory ────────────────────────────────────────────────────────────────

def get_market_data_provider() -> MarketDataProvider:
    """Return the configured market data provider. Easy to swap later."""
    return YahooFinanceProvider()
