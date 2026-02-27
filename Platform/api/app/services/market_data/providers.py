"""
Market data provider interface and adapters.

To swap providers later:
1. Create a new class that implements MarketDataProvider
2. Change get_provider() to return your new class
3. All downstream code (compute_metrics, endpoints) works unchanged

Currently only InternalProvider is implemented (hardcoded MVP data).
Future providers: FinnhubProvider, PolygonProvider, FMPProvider, etc.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional

from app.services.market_data.schemas import (
    CompanyProfile,
    ForwardEstimates,
    FundamentalsTTM,
    QuarterlyFinancials,
    QuoteData,
)


class MarketDataProvider(ABC):
    """Abstract interface for market data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'finnhub', 'polygon', 'apter_internal')."""
        ...

    @abstractmethod
    def get_quote(self, ticker: str) -> QuoteData:
        """Current price, change, session info."""
        ...

    @abstractmethod
    def get_company_profile(self, ticker: str) -> CompanyProfile:
        """Company name, sector, market cap."""
        ...

    @abstractmethod
    def get_fundamentals_ttm(self, ticker: str) -> FundamentalsTTM:
        """Trailing twelve months fundamentals."""
        ...

    @abstractmethod
    def get_financials_quarterly(
        self, ticker: str, limit: int = 8
    ) -> List[QuarterlyFinancials]:
        """Recent quarterly financials."""
        ...

    @abstractmethod
    def get_estimates_forward(self, ticker: str) -> ForwardEstimates:
        """
        Forward consensus estimates (FY1/FY2).
        Returns ForwardEstimates with available=False if not supported.
        """
        ...


class InternalProvider(MarketDataProvider):
    """
    MVP provider using hardcoded internal data.

    Serves static data with proper metadata stamping.
    When you integrate a real provider, replace this class.
    """

    @property
    def name(self) -> str:
        return "apter_internal"

    def get_quote(self, ticker: str) -> QuoteData:
        from app.services.market_data import _STOCK_DB, _is_market_open

        start = time.monotonic_ns()
        now_iso = datetime.now(timezone.utc).isoformat()
        session = _is_market_open()

        stock = _STOCK_DB.get(ticker)
        latency = (time.monotonic_ns() - start) // 1_000_000

        if not stock:
            return QuoteData(
                symbol=ticker,
                price=0.0,
                change=0.0,
                change_pct=0.0,
                as_of=now_iso,
                session=session,
                delay_seconds=0,
                source=self.name,
                fetched_at=now_iso,
                provider_latency_ms=latency,
            )

        return QuoteData(
            symbol=ticker,
            price=stock["price"],
            change=stock["change"],
            change_pct=stock["change_pct"],
            market_cap=stock.get("market_cap"),
            as_of=now_iso,
            session=session,
            delay_seconds=0,
            source=self.name,
            fetched_at=now_iso,
            provider_latency_ms=latency,
        )

    def get_company_profile(self, ticker: str) -> CompanyProfile:
        from app.services.market_data import _STOCK_DB

        now_iso = datetime.now(timezone.utc).isoformat()
        stock = _STOCK_DB.get(ticker)

        if not stock:
            return CompanyProfile(
                symbol=ticker,
                name=f"{ticker} (Unknown)",
                source=self.name,
                fetched_at=now_iso,
            )

        return CompanyProfile(
            symbol=ticker,
            name=stock["name"],
            sector=stock.get("sector"),
            market_cap=stock.get("market_cap"),
            source=self.name,
            fetched_at=now_iso,
        )

    def get_fundamentals_ttm(self, ticker: str) -> FundamentalsTTM:
        from app.services.market_data import _METRIC_DB

        start = time.monotonic_ns()
        now_iso = datetime.now(timezone.utc).isoformat()
        metrics = _METRIC_DB.get(ticker)
        latency = (time.monotonic_ns() - start) // 1_000_000

        if not metrics:
            return FundamentalsTTM(
                symbol=ticker,
                source=self.name,
                fetched_at=now_iso,
            )

        quality = metrics.get("quality", {})
        value = metrics.get("value", {})
        growth = metrics.get("growth", {})
        momentum = metrics.get("momentum", {})
        risk = metrics.get("risk", {})

        return FundamentalsTTM(
            symbol=ticker,
            gross_margin=quality.get("gross_margin"),
            operating_margin=quality.get("operating_margin"),
            fcf_margin=quality.get("fcf_margin"),
            roe=quality.get("roe"),
            roic=quality.get("roic"),
            pe_ratio=value.get("pe_ratio"),
            pb_ratio=value.get("pb_ratio"),
            ps_ratio=value.get("ps_ratio"),
            ev_ebitda=value.get("ev_ebitda"),
            fcf_yield=value.get("fcf_yield"),
            revenue_growth_yoy=growth.get("revenue_growth_yoy"),
            earnings_growth_yoy=growth.get("earnings_growth_yoy"),
            fcf_growth_yoy=growth.get("fcf_growth_yoy"),
            price_vs_sma50=momentum.get("price_vs_sma50"),
            price_vs_sma200=momentum.get("price_vs_sma200"),
            rsi_14=momentum.get("rsi_14"),
            return_1m=momentum.get("return_1m"),
            return_3m=momentum.get("return_3m"),
            return_6m=momentum.get("return_6m"),
            volatility_30d=risk.get("volatility_30d"),
            max_drawdown_1y=risk.get("max_drawdown_1y"),
            debt_to_equity=risk.get("debt_to_equity"),
            interest_coverage=risk.get("interest_coverage"),
            current_ratio=risk.get("current_ratio"),
            beta=risk.get("beta"),
            period_end=metrics.get("_period_end", "2025-12-31"),
            source=self.name,
            fetched_at=now_iso,
        )

    def get_financials_quarterly(
        self, ticker: str, limit: int = 8
    ) -> List[QuarterlyFinancials]:
        # Internal provider does not have quarterly time series
        return []

    def get_estimates_forward(self, ticker: str) -> ForwardEstimates:
        now_iso = datetime.now(timezone.utc).isoformat()
        return ForwardEstimates(
            symbol=ticker,
            available=False,
            unavailable_reason="Forward consensus estimates are not available with the internal data source. Integrate a provider like FMP, Polygon, or Finnhub for FY1/FY2 estimates.",
            source=self.name,
            fetched_at=now_iso,
        )


# ─── Provider registry ───

_provider_instance: Optional[MarketDataProvider] = None


def get_provider() -> MarketDataProvider:
    """
    Get the active market data provider.

    To swap providers:
    1. Implement MarketDataProvider (e.g. FinnhubProvider)
    2. Change this function to return your provider
    """
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = InternalProvider()
    return _provider_instance


def set_provider(provider: MarketDataProvider) -> None:
    """Override the active provider (useful for testing)."""
    global _provider_instance
    _provider_instance = provider
