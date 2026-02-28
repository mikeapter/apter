"""
Pydantic models for market data pipeline.

Every metric carries:
- value (nullable)
- label: "TTM" | "MRQ" | "Forward FY1" | "Forward FY2"
- data_as_of: ISO date of the underlying data period
- source: data provider name
- null_reason: explanation when value is None
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ─── Atomic metric with metadata ───


class MetricValue(BaseModel):
    value: Optional[float] = None
    label: str  # "TTM", "MRQ", "Forward FY1", "Forward FY2"
    data_as_of: Optional[str] = None  # ISO date e.g. "2025-12-31"
    source: str = "apter_internal"
    null_reason: Optional[str] = None


# ─── Quote ───


class QuoteData(BaseModel):
    symbol: str
    price: float
    change: float
    change_pct: float
    market_cap: Optional[float] = None
    volume: Optional[int] = None
    as_of: str  # ISO datetime
    session: str  # REGULAR | AFTER_HOURS | PRE_MARKET | CLOSED
    delay_seconds: int = 0
    source: str = "apter_internal"
    fetched_at: str  # ISO datetime UTC
    provider_latency_ms: int = 0


# ─── Company profile ───


class CompanyProfile(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    source: str = "apter_internal"
    fetched_at: str = ""


# ─── Raw fundamentals from provider (TTM) ───


class FundamentalsTTM(BaseModel):
    symbol: str
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    eps: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    fcf_margin: Optional[float] = None
    roe: Optional[float] = None
    roic: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    interest_coverage: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    fcf_yield: Optional[float] = None
    beta: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    earnings_growth_yoy: Optional[float] = None
    fcf_growth_yoy: Optional[float] = None
    volatility_30d: Optional[float] = None
    max_drawdown_1y: Optional[float] = None
    # Momentum
    price_vs_sma50: Optional[float] = None
    price_vs_sma200: Optional[float] = None
    rsi_14: Optional[float] = None
    return_1m: Optional[float] = None
    return_3m: Optional[float] = None
    return_6m: Optional[float] = None
    # Period
    period_end: Optional[str] = None  # ISO date of last fiscal period end
    source: str = "apter_internal"
    fetched_at: str = ""


# ─── Quarterly financials ───


class QuarterlyFinancials(BaseModel):
    symbol: str
    fiscal_quarter: str  # e.g. "Q4 2025"
    period_end: str  # ISO date
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    eps: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    source: str = "apter_internal"
    fetched_at: str = ""


# ─── Forward estimates ───


class ForwardEstimates(BaseModel):
    symbol: str
    fy1_revenue: Optional[float] = None
    fy1_eps: Optional[float] = None
    fy1_pe: Optional[float] = None
    fy1_label: str = "FY2025"
    fy2_revenue: Optional[float] = None
    fy2_eps: Optional[float] = None
    fy2_pe: Optional[float] = None
    fy2_label: str = "FY2026"
    peg_forward: Optional[float] = None
    source: str = "apter_internal"
    fetched_at: str = ""
    data_as_of: Optional[str] = None
    available: bool = False
    unavailable_reason: Optional[str] = None


# ─── Standardized metrics output ───


class StandardizedMetrics(BaseModel):
    """All computed metrics with labels, timestamps, and sources."""

    ticker: str

    # Valuation
    pe_trailing: MetricValue
    pe_forward_fy1: MetricValue
    pe_forward_fy2: MetricValue
    peg_forward: MetricValue

    # Growth
    revenue_yoy_ttm: MetricValue
    eps_yoy_ttm: MetricValue

    # Profitability
    gross_margin_ttm: MetricValue
    operating_margin_ttm: MetricValue
    roe_ttm: MetricValue

    # Balance Sheet
    debt_to_equity_mrq: MetricValue

    # Risk
    beta: MetricValue
    realized_vol_30d: MetricValue

    # Metadata
    data_as_of: str  # Earliest period end across all metrics
    source: str
    fetched_at: str


# ─── Data quality / staleness ───


class DataQuality(BaseModel):
    stale_flags: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    provider: str = "apter_internal"
    last_updated: str = ""


# ─── Full snapshot response ───


class StockSnapshot(BaseModel):
    ticker: str
    quote: QuoteData
    profile: CompanyProfile
    fundamentals: StandardizedMetrics
    forward: ForwardEstimates
    data_quality: DataQuality
