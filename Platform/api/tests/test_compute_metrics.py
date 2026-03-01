"""
Tests for compute_metrics module.

Validates:
- Correct null handling when fields are missing
- TTM/MRQ/Forward labels are set correctly
- Staleness detection works for old data
- Forward estimate unavailability is handled gracefully
"""

import sys
import os

# Ensure the api package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone, timedelta

from app.services.market_data.schemas import (
    FundamentalsTTM,
    ForwardEstimates,
    MetricValue,
    QuoteData,
)
from app.services.market_data.compute_metrics import (
    compute_staleness,
    compute_standardized_metrics,
)


def _make_quote(symbol: str = "TEST", price: float = 100.0) -> QuoteData:
    now = datetime.now(timezone.utc).isoformat()
    return QuoteData(
        symbol=symbol,
        price=price,
        change=1.0,
        change_pct=1.0,
        as_of=now,
        session="CLOSED",
        source="test",
        fetched_at=now,
        provider_latency_ms=0,
    )


def _make_fundamentals(
    symbol: str = "TEST",
    pe: float | None = 25.0,
    roe: float | None = 15.0,
    rev_growth: float | None = 10.0,
    period_end: str | None = "2025-12-31",
) -> FundamentalsTTM:
    now = datetime.now(timezone.utc).isoformat()
    return FundamentalsTTM(
        symbol=symbol,
        pe_ratio=pe,
        roe=roe,
        revenue_growth_yoy=rev_growth,
        earnings_growth_yoy=12.0,
        gross_margin=45.0,
        operating_margin=30.0,
        debt_to_equity=0.5,
        beta=1.1,
        volatility_30d=20.0,
        period_end=period_end,
        source="test",
        fetched_at=now,
    )


def _make_forward_unavailable(symbol: str = "TEST") -> ForwardEstimates:
    now = datetime.now(timezone.utc).isoformat()
    return ForwardEstimates(
        symbol=symbol,
        available=False,
        unavailable_reason="Not supported by test provider",
        source="test",
        fetched_at=now,
    )


def _make_forward_available(symbol: str = "TEST") -> ForwardEstimates:
    now = datetime.now(timezone.utc).isoformat()
    return ForwardEstimates(
        symbol=symbol,
        fy1_pe=22.0,
        fy2_pe=20.0,
        peg_forward=1.5,
        available=True,
        source="test",
        fetched_at=now,
        data_as_of="2025-12-31",
    )


class TestComputeMetrics:
    """Tests for compute_standardized_metrics."""

    def test_all_metrics_present(self):
        """When all data is provided, no nulls in core metrics."""
        quote = _make_quote()
        fund = _make_fundamentals()
        fwd = _make_forward_unavailable()

        result = compute_standardized_metrics("TEST", fund, quote, fwd)

        assert result.ticker == "TEST"
        assert result.pe_trailing.value == 25.0
        assert result.pe_trailing.label == "TTM"
        assert result.roe_ttm.value == 15.0
        assert result.roe_ttm.label == "TTM"
        assert result.revenue_yoy_ttm.value == 10.0
        assert result.debt_to_equity_mrq.label == "MRQ"
        assert result.beta.value == 1.1

    def test_null_pe_returns_null_reason(self):
        """When PE is None, null_reason is set."""
        quote = _make_quote()
        fund = _make_fundamentals(pe=None)
        fwd = _make_forward_unavailable()

        result = compute_standardized_metrics("TEST", fund, quote, fwd)

        assert result.pe_trailing.value is None
        assert result.pe_trailing.null_reason is not None
        assert "not available" in result.pe_trailing.null_reason.lower()

    def test_null_roe_returns_null_reason(self):
        """When ROE is None, null_reason is set."""
        quote = _make_quote()
        fund = _make_fundamentals(roe=None)
        fwd = _make_forward_unavailable()

        result = compute_standardized_metrics("TEST", fund, quote, fwd)

        assert result.roe_ttm.value is None
        assert result.roe_ttm.null_reason is not None

    def test_forward_unavailable_nulls(self):
        """When forward estimates unavailable, forward metrics are null."""
        quote = _make_quote()
        fund = _make_fundamentals()
        fwd = _make_forward_unavailable()

        result = compute_standardized_metrics("TEST", fund, quote, fwd)

        assert result.pe_forward_fy1.value is None
        assert "Forward FY1" in result.pe_forward_fy1.label
        assert result.pe_forward_fy1.null_reason is not None
        assert result.pe_forward_fy2.value is None
        assert result.peg_forward.value is None

    def test_forward_available_values(self):
        """When forward estimates are available, values are populated."""
        quote = _make_quote()
        fund = _make_fundamentals()
        fwd = _make_forward_available()

        result = compute_standardized_metrics("TEST", fund, quote, fwd)

        assert result.pe_forward_fy1.value == 22.0
        assert result.pe_forward_fy2.value == 20.0
        assert result.peg_forward.value == 1.5

    def test_labels_correct(self):
        """All label values are in the expected set."""
        quote = _make_quote()
        fund = _make_fundamentals()
        fwd = _make_forward_unavailable()

        result = compute_standardized_metrics("TEST", fund, quote, fwd)

        valid_labels = {"TTM", "MRQ", "Forward FY1", "Forward FY2", "Forward", "30-Day"}
        for field_name in [
            "pe_trailing", "pe_forward_fy1", "pe_forward_fy2", "peg_forward",
            "revenue_yoy_ttm", "eps_yoy_ttm", "gross_margin_ttm",
            "operating_margin_ttm", "roe_ttm", "debt_to_equity_mrq",
            "beta", "realized_vol_30d",
        ]:
            metric: MetricValue = getattr(result, field_name)
            assert metric.label in valid_labels, f"{field_name} has unexpected label: {metric.label}"

    def test_data_as_of_set(self):
        """data_as_of should match the period_end from fundamentals."""
        quote = _make_quote()
        fund = _make_fundamentals(period_end="2025-09-30")
        fwd = _make_forward_unavailable()

        result = compute_standardized_metrics("TEST", fund, quote, fwd)

        assert result.data_as_of == "2025-09-30"

    def test_empty_fundamentals(self):
        """When no fundamental data exists, all metrics are null with reasons."""
        quote = _make_quote()
        now = datetime.now(timezone.utc).isoformat()
        fund = FundamentalsTTM(symbol="UNKNOWN", source="test", fetched_at=now)
        fwd = _make_forward_unavailable()

        result = compute_standardized_metrics("UNKNOWN", fund, quote, fwd)

        assert result.pe_trailing.value is None
        assert result.roe_ttm.value is None
        assert result.revenue_yoy_ttm.value is None


class TestStaleness:
    """Tests for compute_staleness."""

    def test_fresh_data_no_flags(self):
        """Recent data should have no staleness flags."""
        quote = _make_quote()
        fund = _make_fundamentals(period_end="2025-12-31")
        fwd = _make_forward_unavailable()
        metrics = compute_standardized_metrics("TEST", fund, quote, fwd)

        quality = compute_staleness(fund, fwd, metrics)

        assert "fundamentals_old" not in quality.stale_flags

    def test_old_period_triggers_stale(self):
        """Period older than 120 days triggers fundamentals_old."""
        old_date = (datetime.now(timezone.utc) - timedelta(days=150)).strftime("%Y-%m-%d")
        quote = _make_quote()
        fund = _make_fundamentals(period_end=old_date)
        fwd = _make_forward_unavailable()
        metrics = compute_standardized_metrics("TEST", fund, quote, fwd)

        quality = compute_staleness(fund, fwd, metrics)

        assert "fundamentals_old" in quality.stale_flags

    def test_no_forward_estimates_flag(self):
        """When forward estimates unavailable, flag is set."""
        quote = _make_quote()
        fund = _make_fundamentals()
        fwd = _make_forward_unavailable()
        metrics = compute_standardized_metrics("TEST", fund, quote, fwd)

        quality = compute_staleness(fund, fwd, metrics)

        assert "no_forward_estimates" in quality.stale_flags

    def test_forward_available_no_flag(self):
        """When forward estimates are available, no_forward_estimates flag not set."""
        quote = _make_quote()
        fund = _make_fundamentals()
        fwd = _make_forward_available()
        metrics = compute_standardized_metrics("TEST", fund, quote, fwd)

        quality = compute_staleness(fund, fwd, metrics)

        assert "no_forward_estimates" not in quality.stale_flags

    def test_missing_fields_detected(self):
        """When metrics are null, they appear in missing_fields."""
        quote = _make_quote()
        now = datetime.now(timezone.utc).isoformat()
        fund = FundamentalsTTM(symbol="EMPTY", source="test", fetched_at=now)
        fwd = _make_forward_unavailable()
        metrics = compute_standardized_metrics("EMPTY", fund, quote, fwd)

        quality = compute_staleness(fund, fwd, metrics)

        assert "pe_trailing" in quality.missing_fields
        assert "roe_ttm" in quality.missing_fields
        assert "revenue_yoy_ttm" in quality.missing_fields

    def test_provider_name_set(self):
        """Provider name should come from fundamentals source."""
        quote = _make_quote()
        fund = _make_fundamentals()
        fwd = _make_forward_unavailable()
        metrics = compute_standardized_metrics("TEST", fund, quote, fwd)

        quality = compute_staleness(fund, fwd, metrics)

        assert quality.provider == "test"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
