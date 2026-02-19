"""
Apter Conviction Score — Pillar Calculations

Each pillar function takes raw metric values and returns a 0–10 score.
Metrics are converted to percentiles against market-wide distributions,
then mapped to 0–10 scores, then combined via config-driven weights.
"""

from __future__ import annotations

from typing import Dict, Optional

from app.scoring.utils import (
    compute_percentile_rank,
    get_market_wide_population,
    percentile_to_score,
    rsi_to_score,
    weighted_average,
    winsorize,
)


def _score_metric(
    value: Optional[float],
    metric_name: str,
    higher_is_better: bool = True,
    winsor_low: float = 2.0,
    winsor_high: float = 98.0,
) -> Optional[float]:
    """Score a single metric: winsorize -> percentile -> 0-10."""
    if value is None:
        return None

    population = get_market_wide_population(metric_name)
    if not population:
        return 5.0  # neutral if no population data

    # Winsorize by clamping to population bounds with small margin
    sorted_pop = sorted(population)
    low_bound = sorted_pop[max(0, int(len(sorted_pop) * winsor_low / 100))]
    high_bound = sorted_pop[min(len(sorted_pop) - 1, int(len(sorted_pop) * winsor_high / 100))]
    clamped = winsorize(value, low_bound, high_bound)

    percentile = compute_percentile_rank(clamped, population)
    return percentile_to_score(percentile, higher_is_better)


def compute_quality_score(
    metrics: Dict[str, Optional[float]],
    metric_config: Dict[str, Dict],
) -> float:
    """Compute the Quality pillar score (0–10)."""
    scores = {}
    weights = {}

    for name, cfg in metric_config.items():
        raw = metrics.get(name)
        score = _score_metric(raw, name, cfg.get("higher_is_better", True))
        if score is not None:
            scores[name] = score
            weights[name] = cfg["weight"]

    return weighted_average(scores, weights)


def compute_value_score(
    metrics: Dict[str, Optional[float]],
    metric_config: Dict[str, Dict],
) -> float:
    """Compute the Value pillar score (0–10)."""
    scores = {}
    weights = {}

    for name, cfg in metric_config.items():
        raw = metrics.get(name)
        score = _score_metric(raw, name, cfg.get("higher_is_better", True))
        if score is not None:
            scores[name] = score
            weights[name] = cfg["weight"]

    return weighted_average(scores, weights)


def compute_growth_score(
    metrics: Dict[str, Optional[float]],
    metric_config: Dict[str, Dict],
) -> float:
    """Compute the Growth pillar score (0–10)."""
    scores = {}
    weights = {}

    for name, cfg in metric_config.items():
        raw = metrics.get(name)
        score = _score_metric(raw, name, cfg.get("higher_is_better", True))
        if score is not None:
            scores[name] = score
            weights[name] = cfg["weight"]

    return weighted_average(scores, weights)


def compute_momentum_score(
    metrics: Dict[str, Optional[float]],
    metric_config: Dict[str, Dict],
) -> float:
    """
    Compute the Momentum/Trend pillar score (0–10).
    RSI uses a bell-curve mapping instead of linear percentile.
    """
    scores = {}
    weights = {}

    for name, cfg in metric_config.items():
        raw = metrics.get(name)
        if raw is None:
            continue

        if name == "rsi_14":
            opt = cfg.get("optimal_range", [50, 70])
            score = rsi_to_score(raw, opt[0], opt[1])
        else:
            score = _score_metric(raw, name, cfg.get("higher_is_better", True))

        if score is not None:
            scores[name] = score
            weights[name] = cfg["weight"]

    return weighted_average(scores, weights)


def compute_risk_score(
    metrics: Dict[str, Optional[float]],
    metric_config: Dict[str, Dict],
) -> float:
    """
    Compute the Risk pillar score (0–10).
    Higher score = LOWER risk (better).
    Most risk metrics are higher_is_better=False.
    """
    scores = {}
    weights = {}

    for name, cfg in metric_config.items():
        raw = metrics.get(name)
        score = _score_metric(raw, name, cfg.get("higher_is_better", True))
        if score is not None:
            scores[name] = score
            weights[name] = cfg["weight"]

    return weighted_average(scores, weights)


def compute_all_pillars(
    quality_metrics: Dict[str, Optional[float]],
    value_metrics: Dict[str, Optional[float]],
    growth_metrics: Dict[str, Optional[float]],
    momentum_metrics: Dict[str, Optional[float]],
    risk_metrics: Dict[str, Optional[float]],
    config: Dict,
) -> Dict[str, float]:
    """
    Compute all five pillar scores.
    Returns {"quality": X, "value": X, "growth": X, "momentum": X, "risk": X}.
    """
    return {
        "quality": compute_quality_score(quality_metrics, config.get("quality_metrics", {})),
        "value": compute_value_score(value_metrics, config.get("value_metrics", {})),
        "growth": compute_growth_score(growth_metrics, config.get("growth_metrics", {})),
        "momentum": compute_momentum_score(momentum_metrics, config.get("momentum_metrics", {})),
        "risk": compute_risk_score(risk_metrics, config.get("risk_metrics", {})),
    }
