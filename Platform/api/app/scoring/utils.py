"""Utility functions for the scoring engine: percentile mapping, winsorization, missing data handling."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple


def winsorize(value: float, lower: float, upper: float) -> float:
    """Clamp a value within winsorization bounds."""
    return max(lower, min(upper, value))


def compute_percentile_rank(value: float, population: List[float]) -> float:
    """
    Compute the percentile rank of `value` within `population`.
    Returns a float in [0, 100].
    """
    if not population:
        return 50.0  # default to median if no population
    sorted_pop = sorted(population)
    n = len(sorted_pop)
    count_below = sum(1 for v in sorted_pop if v < value)
    count_equal = sum(1 for v in sorted_pop if v == value)
    percentile = ((count_below + 0.5 * count_equal) / n) * 100
    return max(0.0, min(100.0, percentile))


def percentile_to_score(percentile: float, higher_is_better: bool = True) -> float:
    """
    Convert a percentile rank (0–100) to a 0–10 score.
    If higher_is_better is False, invert the mapping.
    """
    if not higher_is_better:
        percentile = 100.0 - percentile
    score = percentile / 10.0
    return round(max(0.0, min(10.0, score)), 1)


def rsi_to_score(rsi: float, optimal_low: float = 50.0, optimal_high: float = 70.0) -> float:
    """
    Map RSI to a 0–10 score using a bell-curve centered on the optimal range.
    RSI in [optimal_low, optimal_high] scores highest.
    RSI near 0 or 100 (extreme oversold/overbought) scores lower.
    """
    if optimal_low <= rsi <= optimal_high:
        return 10.0
    if rsi < optimal_low:
        # Scale 0 -> low: score from 2 -> 10
        score = 2.0 + (rsi / optimal_low) * 8.0
    else:
        # Scale high -> 100: score from 10 -> 2
        remaining = 100.0 - optimal_high
        if remaining <= 0:
            return 2.0
        dist = rsi - optimal_high
        score = 10.0 - (dist / remaining) * 8.0
    return round(max(0.0, min(10.0, score)), 1)


def weighted_average(scores: Dict[str, float], weights: Dict[str, float]) -> float:
    """Compute weighted average from parallel dicts of scores and weights."""
    total_weight = 0.0
    total_value = 0.0
    for key, weight in weights.items():
        if key in scores and scores[key] is not None:
            total_value += scores[key] * weight
            total_weight += weight
    if total_weight == 0:
        return 5.0  # neutral default
    return round(total_value / total_weight, 1)


def count_missing_metrics(metrics: Dict[str, Optional[float]], expected_keys: List[str]) -> int:
    """Count how many expected metrics are missing (None)."""
    missing = 0
    for key in expected_keys:
        if key not in metrics or metrics[key] is None:
            missing += 1
    return missing


def compute_confidence(
    total_metrics: int,
    missing_count: int,
    has_peer_group: bool,
    penalty_per_missing: int = 5,
    no_peer_penalty: int = 10,
    min_confidence: int = 20,
) -> int:
    """
    Compute confidence score (0–100).
    Starts at 100, subtracts per missing metric and for peer group absence.
    """
    confidence = 100
    confidence -= missing_count * penalty_per_missing
    if not has_peer_group:
        confidence -= no_peer_penalty
    return max(min_confidence, min(100, confidence))


def get_market_wide_population(metric_name: str) -> List[float]:
    """
    Return a synthetic market-wide population for percentile computation.
    In production, this would query a database of all active stocks.
    For MVP, we use representative distributions for US large/mid caps.
    """
    populations = {
        # Quality
        "roe": [5, 8, 10, 12, 15, 18, 20, 22, 25, 28, 30, 35, 40, 45, 50],
        "roic": [3, 5, 7, 9, 11, 13, 15, 18, 20, 25, 30, 35],
        "gross_margin": [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80],
        "operating_margin": [-5, 0, 5, 8, 10, 12, 15, 18, 20, 25, 30, 35, 40],
        "fcf_margin": [-10, -5, 0, 3, 5, 8, 10, 12, 15, 18, 20, 25, 30],
        "asset_turnover": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.2, 1.5, 2.0],
        # Value (lower is better for most)
        "pe_ratio": [5, 8, 10, 12, 15, 18, 20, 22, 25, 28, 30, 35, 40, 50, 60, 80, 100],
        "pb_ratio": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0],
        "ps_ratio": [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0],
        "ev_ebitda": [3, 5, 7, 8, 10, 12, 14, 16, 18, 20, 25, 30, 40, 50],
        "fcf_yield": [-5, -2, 0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15],
        # Growth
        "revenue_growth_yoy": [-20, -10, -5, 0, 3, 5, 8, 10, 15, 20, 25, 30, 40, 50],
        "earnings_growth_yoy": [-50, -30, -15, -5, 0, 5, 10, 15, 20, 25, 30, 40, 60, 80, 100],
        "fcf_growth_yoy": [-50, -30, -15, 0, 5, 10, 15, 20, 30, 40, 50, 60],
        "revenue_growth_3y_cagr": [-10, -5, 0, 3, 5, 8, 10, 15, 20, 25, 30],
        "earnings_growth_3y_cagr": [-20, -10, 0, 5, 10, 15, 20, 25, 30, 40],
        # Momentum
        "price_vs_sma50": [-15, -10, -7, -5, -3, -1, 0, 1, 3, 5, 7, 10, 15, 20],
        "price_vs_sma200": [-30, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 40],
        "rsi_14": [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80],
        "return_1m": [-15, -10, -7, -5, -3, 0, 2, 4, 6, 8, 10, 15],
        "return_3m": [-25, -15, -10, -5, 0, 3, 5, 8, 12, 15, 20, 30],
        "return_6m": [-30, -20, -10, -5, 0, 5, 10, 15, 20, 25, 30, 40],
        # Risk (lower is better for most)
        "volatility_30d": [10, 15, 18, 20, 22, 25, 28, 30, 35, 40, 50, 60, 80],
        "max_drawdown_1y": [-60, -50, -40, -35, -30, -25, -20, -15, -10, -7, -5, -3],
        "debt_to_equity": [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 8.0],
        "interest_coverage": [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0, 10.0, 15.0, 20.0, 50.0],
        "current_ratio": [0.3, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
        "beta": [0.3, 0.5, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.0, 2.5],
    }
    return populations.get(metric_name, [])


def generate_drivers(
    pillar_scores: Dict[str, float],
    metric_scores: Dict[str, Dict[str, float]],
    pillar_weights: Dict[str, float],
) -> Tuple[list, list]:
    """
    Generate top positive and negative drivers from pillar/metric analysis.
    Returns (positive_drivers, negative_drivers).
    """
    positive = []
    negative = []

    # Pillar-level drivers
    avg_score = sum(pillar_scores.values()) / max(len(pillar_scores), 1)
    for pillar, score in pillar_scores.items():
        weight = pillar_weights.get(pillar, 0.2)
        impact = round((score - avg_score) * weight, 2)
        label = pillar.replace("_", " ").title()
        if impact > 0:
            positive.append({
                "name": f"Strong {label}",
                "impact": round(impact, 1),
                "detail": f"{label} score of {score}/10 is above average, contributing positively to the overall conviction.",
            })
        elif impact < -0.1:
            negative.append({
                "name": f"Weak {label}",
                "impact": round(impact, 1),
                "detail": f"{label} score of {score}/10 is below average, dragging overall conviction lower.",
            })

    # Sort by absolute impact
    positive.sort(key=lambda d: d["impact"], reverse=True)
    negative.sort(key=lambda d: d["impact"])

    return positive[:5], negative[:5]
