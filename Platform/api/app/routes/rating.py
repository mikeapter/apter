"""
Apter Rating API endpoint.

GET /api/rating/{ticker} -- Apter Rating (1-10) composite research score.

Distinct from the Conviction Score. Uses a different weighting:
- Growth Profile (25%)
- Profitability (20%)
- Balance Sheet Strength (20%)
- Market Momentum (15%)
- Risk & Volatility Profile (20%)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException

from app.services.market_data import get_stock_metrics, normalize_symbol, validate_symbol

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Apter Rating"])

# In-memory cache
_rating_cache: Dict[str, dict] = {}
_RATING_CACHE_TTL = 300  # 5 minutes


def _get_cached(ticker: str) -> Optional[dict]:
    cached = _rating_cache.get(ticker)
    if cached and (time.time() - cached["_ts"]) < _RATING_CACHE_TTL:
        return {k: v for k, v in cached.items() if k != "_ts"}
    return None


def _set_cache(ticker: str, result: dict) -> None:
    _rating_cache[ticker] = {**result, "_ts": time.time()}


# ---------------------------------------------------------------------------
# Band labels (Non-RIA safe -- no buy/sell language)
# ---------------------------------------------------------------------------


def _get_band(score: float) -> str:
    if score >= 8.0:
        return "Strong Quantitative Positioning"
    elif score >= 6.0:
        return "Solid / Balanced"
    elif score >= 4.0:
        return "Mixed Profile"
    elif score >= 2.0:
        return "Weak Structure"
    return "Structurally Challenged"


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------


def _clamp(val: float, low: float = 0.0, high: float = 10.0) -> float:
    return max(low, min(high, val))


def _score_growth(metrics: dict) -> tuple[float, List[str]]:
    """Score the Growth Profile component (0-10)."""
    growth = metrics.get("growth", {})
    drivers = []

    rev_yoy = growth.get("revenue_growth_yoy")
    eps_yoy = growth.get("earnings_growth_yoy")
    fcf_yoy = growth.get("fcf_growth_yoy")
    rev_3y = growth.get("revenue_growth_3y_cagr")

    scores = []

    if rev_yoy is not None:
        # 0% = 4, 10% = 6, 20% = 8, 50%+ = 10
        s = _clamp(4 + rev_yoy * 0.12)
        scores.append(s)
        if rev_yoy > 15:
            drivers.append(f"Revenue growth of {rev_yoy:.1f}% exceeds market average")
        elif rev_yoy < 0:
            drivers.append(f"Revenue decline of {rev_yoy:.1f}% is a structural concern")

    if eps_yoy is not None:
        s = _clamp(4 + eps_yoy * 0.08)
        scores.append(s)
        if eps_yoy > 20:
            drivers.append(f"Earnings growth of {eps_yoy:.1f}% indicates strong profitability expansion")

    if fcf_yoy is not None:
        s = _clamp(4 + fcf_yoy * 0.06)
        scores.append(s)

    if rev_3y is not None:
        s = _clamp(4 + rev_3y * 0.15)
        scores.append(s)
        if rev_3y > 10:
            drivers.append(f"3Y revenue CAGR of {rev_3y:.1f}% shows durable growth")

    if not scores:
        return 5.0, ["Insufficient growth data"]

    return round(sum(scores) / len(scores), 1), drivers


def _score_profitability(metrics: dict) -> tuple[float, List[str]]:
    """Score the Profitability component (0-10)."""
    quality = metrics.get("quality", {})
    drivers = []

    roe = quality.get("roe")
    op_margin = quality.get("operating_margin")
    gross_margin = quality.get("gross_margin")
    fcf_margin = quality.get("fcf_margin")

    scores = []

    if roe is not None:
        # ROE 15% = 6, 25% = 8, 40%+ = 10
        s = _clamp(3 + roe * 0.175)
        scores.append(s)
        if roe > 25:
            drivers.append(f"ROE of {roe:.1f}% indicates high capital efficiency")

    if op_margin is not None:
        s = _clamp(3 + op_margin * 0.2)
        scores.append(s)
        if op_margin > 30:
            drivers.append(f"Operating margin of {op_margin:.1f}% demonstrates pricing power")

    if gross_margin is not None:
        s = _clamp(2 + gross_margin * 0.1)
        scores.append(s)

    if fcf_margin is not None:
        s = _clamp(3 + fcf_margin * 0.2)
        scores.append(s)

    if not scores:
        return 5.0, ["Insufficient profitability data"]

    return round(sum(scores) / len(scores), 1), drivers


def _score_balance_sheet(metrics: dict) -> tuple[float, List[str]]:
    """Score the Balance Sheet Strength component (0-10)."""
    risk = metrics.get("risk", {})
    drivers = []

    d2e = risk.get("debt_to_equity")
    ic = risk.get("interest_coverage")
    cr = risk.get("current_ratio")

    scores = []

    if d2e is not None:
        # Lower D/E is better: 0 = 10, 1 = 7, 3 = 4, 5+ = 2
        s = _clamp(10 - d2e * 1.6)
        scores.append(s)
        if d2e < 0.5:
            drivers.append(f"Low leverage (D/E {d2e:.2f}) provides financial flexibility")
        elif d2e > 3:
            drivers.append(f"High leverage (D/E {d2e:.2f}) increases financial risk")

    if ic is not None:
        # Higher is better: 5x = 6, 20x = 8, 50x+ = 10
        s = _clamp(4 + min(ic, 60) * 0.1)
        scores.append(s)
        if ic > 20:
            drivers.append(f"Interest coverage of {ic:.1f}x provides strong debt service capacity")

    if cr is not None:
        # 1.0 = 5, 1.5 = 7, 2.0+ = 9
        s = _clamp(cr * 4.5)
        scores.append(s)

    if not scores:
        return 5.0, ["Insufficient balance sheet data"]

    return round(sum(scores) / len(scores), 1), drivers


def _score_momentum(metrics: dict) -> tuple[float, List[str]]:
    """Score the Market Momentum component (0-10)."""
    momentum = metrics.get("momentum", {})
    drivers = []

    sma50 = momentum.get("price_vs_sma50")
    sma200 = momentum.get("price_vs_sma200")
    rsi = momentum.get("rsi_14")
    ret_3m = momentum.get("return_3m")

    scores = []

    if sma50 is not None:
        # Above SMA50 is positive: 0% = 5, 5% = 7, 10%+ = 9
        s = _clamp(5 + sma50 * 0.4)
        scores.append(s)
        if sma50 > 5:
            drivers.append("Trading above 50-day moving average with positive trend")

    if sma200 is not None:
        s = _clamp(5 + sma200 * 0.25)
        scores.append(s)

    if rsi is not None:
        # Bell curve: 50-65 is optimal (8-9), extremes are lower
        if 50 <= rsi <= 65:
            s = 8.5
        elif 40 <= rsi < 50 or 65 < rsi <= 70:
            s = 7.0
        elif rsi > 70:
            s = 5.5
            drivers.append(f"RSI at {rsi:.0f} indicates overbought conditions")
        else:
            s = 4.5
            drivers.append(f"RSI at {rsi:.0f} indicates oversold conditions")
        scores.append(s)

    if ret_3m is not None:
        s = _clamp(5 + ret_3m * 0.3)
        scores.append(s)

    if not scores:
        return 5.0, ["Insufficient momentum data"]

    return round(sum(scores) / len(scores), 1), drivers


def _score_risk_volatility(metrics: dict) -> tuple[float, List[str]]:
    """Score the Risk & Volatility Profile (0-10). Higher = lower risk."""
    risk = metrics.get("risk", {})
    drivers = []

    vol = risk.get("volatility_30d")
    drawdown = risk.get("max_drawdown_1y")
    beta = risk.get("beta")

    scores = []

    if vol is not None:
        # Lower vol is better: 10% = 9, 20% = 7, 40% = 4, 60%+ = 2
        s = _clamp(10 - vol * 0.13)
        scores.append(s)
        if vol > 35:
            drivers.append(f"Elevated 30-day volatility at {vol:.1f}%")
        elif vol < 18:
            drivers.append(f"Low volatility profile ({vol:.1f}%) supports stability")

    if drawdown is not None:
        # Less negative is better: -5% = 9, -15% = 7, -30% = 4, -50% = 1
        s = _clamp(10 + drawdown * 0.18)
        scores.append(s)

    if beta is not None:
        # Beta near 1 is neutral, lower is better for risk score
        if beta <= 1.0:
            s = _clamp(8 + (1 - beta) * 4)
        else:
            s = _clamp(8 - (beta - 1) * 4)
        scores.append(s)
        if beta > 1.5:
            drivers.append(f"Beta of {beta:.2f} implies amplified market sensitivity")

    if not scores:
        return 5.0, ["Insufficient risk data"]

    return round(sum(scores) / len(scores), 1), drivers


def _compute_rating(ticker: str) -> dict:
    """Compute the full Apter Rating for a ticker."""
    metrics = get_stock_metrics(ticker)

    if not metrics:
        return {
            "ticker": ticker,
            "rating": 5.0,
            "band": "Mixed Profile",
            "components": {
                "growth": {"score": 5.0, "weight": 0.25, "drivers": ["No data available"]},
                "profitability": {"score": 5.0, "weight": 0.20, "drivers": ["No data available"]},
                "balance_sheet": {"score": 5.0, "weight": 0.20, "drivers": ["No data available"]},
                "momentum": {"score": 5.0, "weight": 0.15, "drivers": ["No data available"]},
                "risk": {"score": 5.0, "weight": 0.20, "drivers": ["No data available"]},
            },
            "as_of": datetime.now(timezone.utc).isoformat(),
            "disclaimer": (
                "Apter Rating (1-10) is a proprietary composite research score derived "
                "from quantitative financial metrics, market structure indicators, and "
                "risk analysis. Informational only. Not investment advice."
            ),
        }

    growth_score, growth_drivers = _score_growth(metrics)
    profit_score, profit_drivers = _score_profitability(metrics)
    bs_score, bs_drivers = _score_balance_sheet(metrics)
    mom_score, mom_drivers = _score_momentum(metrics)
    risk_score, risk_drivers = _score_risk_volatility(metrics)

    # Weighted composite
    composite = (
        growth_score * 0.25
        + profit_score * 0.20
        + bs_score * 0.20
        + mom_score * 0.15
        + risk_score * 0.20
    )
    composite = round(_clamp(composite), 1)

    return {
        "ticker": ticker,
        "rating": composite,
        "band": _get_band(composite),
        "components": {
            "growth": {"score": growth_score, "weight": 0.25, "drivers": growth_drivers},
            "profitability": {"score": profit_score, "weight": 0.20, "drivers": profit_drivers},
            "balance_sheet": {"score": bs_score, "weight": 0.20, "drivers": bs_drivers},
            "momentum": {"score": mom_score, "weight": 0.15, "drivers": mom_drivers},
            "risk": {"score": risk_score, "weight": 0.20, "drivers": risk_drivers},
        },
        "as_of": datetime.now(timezone.utc).isoformat(),
        "disclaimer": (
            "Apter Rating (1-10) is a proprietary composite research score derived "
            "from quantitative financial metrics, market structure indicators, and "
            "risk analysis. Informational only. Not investment advice."
        ),
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/rating/{ticker}")
def get_rating(ticker: str):
    """Get Apter Rating for a single ticker."""
    symbol = normalize_symbol(ticker)
    if not validate_symbol(symbol):
        raise HTTPException(status_code=400, detail=f"Invalid ticker format: {ticker}")

    cached = _get_cached(symbol)
    if cached:
        return cached

    logger.info("Computing Apter Rating for %s", symbol)
    result = _compute_rating(symbol)
    _set_cache(symbol, result)
    return result
