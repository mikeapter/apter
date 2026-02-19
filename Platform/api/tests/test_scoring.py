"""Unit tests for the Apter Conviction Score scoring engine."""

import sys
import os

# Add the api directory to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.scoring.utils import (
    winsorize,
    compute_percentile_rank,
    percentile_to_score,
    rsi_to_score,
    weighted_average,
    count_missing_metrics,
    compute_confidence,
)
from app.scoring.pillars import compute_all_pillars
from app.scoring.overall import compute_conviction_score, get_band, apply_risk_gates, CONFIG


def test_winsorize():
    assert winsorize(5.0, 0.0, 10.0) == 5.0
    assert winsorize(-5.0, 0.0, 10.0) == 0.0
    assert winsorize(15.0, 0.0, 10.0) == 10.0
    assert winsorize(0.0, 0.0, 10.0) == 0.0
    assert winsorize(10.0, 0.0, 10.0) == 10.0


def test_percentile_rank():
    population = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    # Value at median
    rank = compute_percentile_rank(5.5, population)
    assert 40 < rank < 60
    # Value at bottom
    rank_low = compute_percentile_rank(1, population)
    assert rank_low < 15
    # Value at top
    rank_high = compute_percentile_rank(10, population)
    assert rank_high > 85
    # Empty population
    assert compute_percentile_rank(5.0, []) == 50.0


def test_percentile_to_score():
    assert percentile_to_score(100.0, True) == 10.0
    assert percentile_to_score(0.0, True) == 0.0
    assert percentile_to_score(50.0, True) == 5.0
    # Inversion for lower-is-better
    assert percentile_to_score(100.0, False) == 0.0
    assert percentile_to_score(0.0, False) == 10.0


def test_rsi_to_score():
    # Optimal range (50-70) should score 10
    assert rsi_to_score(60.0) == 10.0
    assert rsi_to_score(55.0) == 10.0
    # Extreme oversold
    score_low = rsi_to_score(10.0)
    assert 0 < score_low < 5
    # Extreme overbought
    score_high = rsi_to_score(90.0)
    assert 0 < score_high < 5


def test_weighted_average():
    scores = {"a": 8.0, "b": 6.0, "c": 4.0}
    weights = {"a": 0.5, "b": 0.3, "c": 0.2}
    result = weighted_average(scores, weights)
    expected = (8.0 * 0.5 + 6.0 * 0.3 + 4.0 * 0.2) / 1.0
    assert abs(result - round(expected, 1)) < 0.2

    # Missing keys handled
    scores2 = {"a": 8.0}
    result2 = weighted_average(scores2, weights)
    assert result2 == 8.0  # Only key "a" contributes


def test_count_missing_metrics():
    metrics = {"a": 1.0, "b": None, "c": 3.0}
    expected = ["a", "b", "c", "d"]
    assert count_missing_metrics(metrics, expected) == 2  # b=None, d=missing


def test_compute_confidence():
    # Full data with peers
    assert compute_confidence(30, 0, True) == 100
    # Missing metrics
    assert compute_confidence(30, 5, True) == 75
    # No peer group
    assert compute_confidence(30, 0, False) == 90
    # Minimum floor
    assert compute_confidence(30, 20, False) == 20


def test_get_band():
    assert get_band(0.0)["label"] == "Bearish"
    assert get_band(3.9)["label"] == "Bearish"
    assert get_band(4.0)["label"] == "Neutral"
    assert get_band(7.9)["label"] == "Neutral"
    assert get_band(8.0)["label"] == "Bullish"
    assert get_band(10.0)["label"] == "Bullish"


def test_apply_risk_gates_leverage_cap():
    # Extreme leverage should cap at 7.4
    score, penalties = apply_risk_gates(
        overall_score=9.0,
        risk_metrics={"debt_to_equity": 8.0, "interest_coverage": 0.8},
        extra_flags={},
    )
    assert score <= 7.4
    assert len(penalties) >= 1
    assert penalties[0]["type"] == "cap"


def test_apply_risk_gates_no_trigger():
    # Safe metrics — no penalties
    score, penalties = apply_risk_gates(
        overall_score=8.0,
        risk_metrics={"debt_to_equity": 0.5, "interest_coverage": 20.0, "volatility_30d": 15.0, "max_drawdown_1y": -5.0},
        extra_flags={},
    )
    assert score == 8.0
    assert len(penalties) == 0


def test_apply_risk_gates_volatility_penalty():
    score, penalties = apply_risk_gates(
        overall_score=8.0,
        risk_metrics={"volatility_30d": 80.0, "max_drawdown_1y": -50.0},
        extra_flags={},
    )
    assert score < 8.0
    vol_penalties = [p for p in penalties if "Volatil" in p["name"]]
    assert len(vol_penalties) >= 1


def test_compute_conviction_score_full():
    result = compute_conviction_score(
        ticker="AAPL",
        quality_metrics={"roe": 171.0, "roic": 56.0, "gross_margin": 46.2, "operating_margin": 31.5, "fcf_margin": 26.8, "asset_turnover": 1.15},
        value_metrics={"pe_ratio": 29.3, "pb_ratio": 48.5, "ps_ratio": 8.1, "ev_ebitda": 22.4, "fcf_yield": 3.5},
        growth_metrics={"revenue_growth_yoy": 8.2, "earnings_growth_yoy": 10.5, "fcf_growth_yoy": 12.1, "revenue_growth_3y_cagr": 7.8, "earnings_growth_3y_cagr": 9.2},
        momentum_metrics={"price_vs_sma50": 3.2, "price_vs_sma200": 8.5, "rsi_14": 58.0, "return_1m": 4.1, "return_3m": 7.8, "return_6m": 12.3},
        risk_metrics={"volatility_30d": 18.2, "max_drawdown_1y": -12.5, "debt_to_equity": 1.8, "interest_coverage": 42.5, "current_ratio": 0.99, "beta": 1.2},
        has_peer_group=False,
    )

    assert result["ticker"] == "AAPL"
    assert 0.0 <= result["overall_score"] <= 10.0
    assert result["band"]["label"] in ("Bearish", "Neutral", "Bullish")
    assert "quality" in result["pillars"]
    assert "value" in result["pillars"]
    assert "growth" in result["pillars"]
    assert "momentum" in result["pillars"]
    assert "risk" in result["pillars"]
    assert "positive" in result["drivers"]
    assert "negative" in result["drivers"]
    assert 0 <= result["confidence"] <= 100
    assert result["model_version"] == "apter_conviction_v1.0"
    assert result["computed_at"]  # ISO timestamp present


def test_compute_conviction_score_empty_metrics():
    """With empty metrics, should return neutral score with low confidence."""
    result = compute_conviction_score(
        ticker="UNKNOWN",
        quality_metrics={},
        value_metrics={},
        growth_metrics={},
        momentum_metrics={},
        risk_metrics={},
        has_peer_group=False,
    )

    assert result["ticker"] == "UNKNOWN"
    assert result["overall_score"] == 5.0  # Neutral default
    assert result["confidence"] <= 30  # Very low confidence
    assert result["band"]["label"] == "Neutral"


def test_compute_conviction_score_tsla_volatile():
    """TSLA should get hit by volatility penalty with vol=52.3 and drawdown=-35.2."""
    result = compute_conviction_score(
        ticker="TSLA",
        quality_metrics={"roe": 22.0, "roic": 15.5, "gross_margin": 18.2, "operating_margin": 8.5, "fcf_margin": 5.2, "asset_turnover": 0.92},
        value_metrics={"pe_ratio": 68.4, "pb_ratio": 14.5, "ps_ratio": 8.5, "ev_ebitda": 42.5, "fcf_yield": 1.2},
        growth_metrics={"revenue_growth_yoy": 2.5, "earnings_growth_yoy": -15.0, "fcf_growth_yoy": -22.0, "revenue_growth_3y_cagr": 25.0, "earnings_growth_3y_cagr": -5.0},
        momentum_metrics={"price_vs_sma50": -5.2, "price_vs_sma200": -2.8, "rsi_14": 42.0, "return_1m": -8.5, "return_3m": -12.0, "return_6m": -5.5},
        risk_metrics={"volatility_30d": 52.3, "max_drawdown_1y": -35.2, "debt_to_equity": 0.08, "interest_coverage": 22.0, "current_ratio": 1.72, "beta": 2.05},
        has_peer_group=False,
    )

    # TSLA should score lower overall
    assert result["overall_score"] < 7.0
    assert result["band"]["label"] in ("Bearish", "Neutral")


def test_pillar_scores_bounded():
    """All pillar scores must be in [0, 10]."""
    result = compute_conviction_score(
        ticker="TEST",
        quality_metrics={"roe": 200.0, "gross_margin": 90.0},
        value_metrics={"pe_ratio": 5.0, "fcf_yield": 15.0},
        growth_metrics={"revenue_growth_yoy": 100.0},
        momentum_metrics={"rsi_14": 99.0, "return_1m": 50.0},
        risk_metrics={"volatility_30d": 5.0, "beta": 0.3},
    )

    for pillar, score in result["pillars"].items():
        assert 0.0 <= score <= 10.0, f"{pillar} score {score} out of bounds"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
