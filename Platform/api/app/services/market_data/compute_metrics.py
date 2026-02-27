"""
Standardized metric computation.

Takes raw provider data and produces MetricValue objects with:
- value (nullable float)
- label: "TTM" | "MRQ" | "Forward FY1" | "Forward FY2"
- data_as_of: date string
- source: provider name
- null_reason: explanation if value is None
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.services.market_data.schemas import (
    DataQuality,
    ForwardEstimates,
    FundamentalsTTM,
    MetricValue,
    QuoteData,
    StandardizedMetrics,
)


def _metric(
    value: Optional[float],
    label: str,
    data_as_of: Optional[str],
    source: str,
    null_reason: Optional[str] = None,
) -> MetricValue:
    """Helper to build a MetricValue, auto-setting null_reason if value is None."""
    if value is None and null_reason is None:
        null_reason = f"{label} data not available from {source}"
    return MetricValue(
        value=value,
        label=label,
        data_as_of=data_as_of,
        source=source,
        null_reason=null_reason if value is None else None,
    )


def compute_standardized_metrics(
    ticker: str,
    fundamentals: FundamentalsTTM,
    quote: QuoteData,
    forward: Optional[ForwardEstimates] = None,
) -> StandardizedMetrics:
    """
    Compute all standardized metrics from raw provider data.

    Each metric carries its label (TTM/MRQ/Forward) and data_as_of date.
    Null values include a reason string.
    """
    source = fundamentals.source
    period_end = fundamentals.period_end
    now_iso = datetime.now(timezone.utc).isoformat()

    # ─── Valuation ───

    pe_trailing = _metric(
        value=fundamentals.pe_ratio,
        label="TTM",
        data_as_of=period_end,
        source=source,
    )

    # Forward P/E from estimates
    fy1_pe: Optional[float] = None
    fy2_pe: Optional[float] = None
    peg_fwd: Optional[float] = None
    fy1_reason: Optional[str] = None
    fy2_reason: Optional[str] = None
    peg_reason: Optional[str] = None

    if forward and forward.available:
        fy1_pe = forward.fy1_pe
        fy2_pe = forward.fy2_pe
        peg_fwd = forward.peg_forward
    else:
        reason = "Forward estimates unavailable with current data source"
        fy1_reason = reason
        fy2_reason = reason
        peg_reason = reason

    pe_forward_fy1 = _metric(
        value=fy1_pe,
        label="Forward FY1",
        data_as_of=forward.data_as_of if forward else None,
        source=forward.source if forward else source,
        null_reason=fy1_reason,
    )

    pe_forward_fy2 = _metric(
        value=fy2_pe,
        label="Forward FY2",
        data_as_of=forward.data_as_of if forward else None,
        source=forward.source if forward else source,
        null_reason=fy2_reason,
    )

    peg_forward = _metric(
        value=peg_fwd,
        label="Forward",
        data_as_of=forward.data_as_of if forward else None,
        source=forward.source if forward else source,
        null_reason=peg_reason,
    )

    # ─── Growth ───

    revenue_yoy_ttm = _metric(
        value=fundamentals.revenue_growth_yoy,
        label="TTM",
        data_as_of=period_end,
        source=source,
    )

    eps_yoy_ttm = _metric(
        value=fundamentals.earnings_growth_yoy,
        label="TTM",
        data_as_of=period_end,
        source=source,
    )

    # ─── Profitability ───

    gross_margin_ttm = _metric(
        value=fundamentals.gross_margin,
        label="TTM",
        data_as_of=period_end,
        source=source,
    )

    operating_margin_ttm = _metric(
        value=fundamentals.operating_margin,
        label="TTM",
        data_as_of=period_end,
        source=source,
    )

    roe_ttm = _metric(
        value=fundamentals.roe,
        label="TTM",
        data_as_of=period_end,
        source=source,
    )

    # ─── Balance Sheet (most recent quarter) ───

    debt_to_equity_mrq = _metric(
        value=fundamentals.debt_to_equity,
        label="MRQ",
        data_as_of=period_end,
        source=source,
    )

    # ─── Risk ───

    beta_metric = _metric(
        value=fundamentals.beta,
        label="TTM",
        data_as_of=period_end,
        source=source,
    )

    vol_30d = _metric(
        value=fundamentals.volatility_30d,
        label="30-Day",
        data_as_of=now_iso[:10],  # Volatility is as of today
        source=source,
    )

    return StandardizedMetrics(
        ticker=ticker,
        pe_trailing=pe_trailing,
        pe_forward_fy1=pe_forward_fy1,
        pe_forward_fy2=pe_forward_fy2,
        peg_forward=peg_forward,
        revenue_yoy_ttm=revenue_yoy_ttm,
        eps_yoy_ttm=eps_yoy_ttm,
        gross_margin_ttm=gross_margin_ttm,
        operating_margin_ttm=operating_margin_ttm,
        roe_ttm=roe_ttm,
        debt_to_equity_mrq=debt_to_equity_mrq,
        beta=beta_metric,
        realized_vol_30d=vol_30d,
        data_as_of=period_end or "unknown",
        source=source,
        fetched_at=now_iso,
    )


def compute_staleness(
    fundamentals: FundamentalsTTM,
    forward: Optional[ForwardEstimates],
    standardized: StandardizedMetrics,
) -> DataQuality:
    """
    Detect stale or missing data and produce quality flags.

    Staleness rules:
    - fundamentals_old: period_end > 120 days ago
    - estimates_old: forward data_as_of > 30 days ago
    - no_fundamentals: no fundamental data at all
    - no_forward_estimates: forward estimates not available
    """
    now = datetime.now(timezone.utc)
    stale_flags: list[str] = []
    missing_fields: list[str] = []

    # Check fundamentals staleness
    if fundamentals.period_end:
        try:
            period_dt = datetime.fromisoformat(fundamentals.period_end)
            if period_dt.tzinfo is None:
                period_dt = period_dt.replace(tzinfo=timezone.utc)
            days_old = (now - period_dt).days
            if days_old > 120:
                stale_flags.append("fundamentals_old")
        except (ValueError, TypeError):
            stale_flags.append("fundamentals_period_unparseable")
    else:
        if fundamentals.pe_ratio is None and fundamentals.roe is None:
            stale_flags.append("no_fundamentals")

    # Check forward estimates
    if forward and not forward.available:
        stale_flags.append("no_forward_estimates")
    elif forward and forward.data_as_of:
        try:
            est_dt = datetime.fromisoformat(forward.data_as_of)
            if est_dt.tzinfo is None:
                est_dt = est_dt.replace(tzinfo=timezone.utc)
            if (now - est_dt).days > 30:
                stale_flags.append("estimates_old")
        except (ValueError, TypeError):
            pass

    # Check missing fields
    for field_name in [
        "pe_trailing",
        "revenue_yoy_ttm",
        "eps_yoy_ttm",
        "gross_margin_ttm",
        "operating_margin_ttm",
        "roe_ttm",
        "debt_to_equity_mrq",
        "beta",
        "realized_vol_30d",
    ]:
        metric: MetricValue = getattr(standardized, field_name)
        if metric.value is None:
            missing_fields.append(field_name)

    return DataQuality(
        stale_flags=stale_flags,
        missing_fields=missing_fields,
        provider=fundamentals.source,
        last_updated=fundamentals.fetched_at,
    )
