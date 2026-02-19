"""
Apter Conviction Score — Overall composite scoring + risk gates.

Computes the weighted overall score from pillar scores,
then applies risk gates/caps/penalties from config.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import yaml

from app.scoring.pillars import compute_all_pillars
from app.scoring.utils import (
    compute_confidence,
    count_missing_metrics,
    generate_drivers,
    weighted_average,
)

# Load config once at module level
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(_CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)


def get_band(score: float) -> Dict[str, str]:
    """Determine the band (Bearish/Neutral/Bullish) for a score."""
    bands = CONFIG.get("bands", {})
    for _key, band in bands.items():
        if band["min"] <= score <= band["max"]:
            return {"label": band["label"], "color": band["color"]}
    # Default fallback
    if score < 4.0:
        return {"label": "Bearish", "color": "red"}
    elif score < 8.0:
        return {"label": "Neutral", "color": "yellow"}
    return {"label": "Bullish", "color": "green"}


def apply_risk_gates(
    overall_score: float,
    risk_metrics: Dict[str, Optional[float]],
    extra_flags: Dict[str, Any],
) -> Tuple[float, List[Dict]]:
    """
    Apply risk gates/caps/penalties after composite scoring.
    Returns (adjusted_score, list_of_applied_penalties_or_caps).
    """
    applied: List[Dict] = []
    gates = CONFIG.get("risk_gates", {})

    # Gate 1: Leverage Cap
    leverage_gate = gates.get("leverage_cap", {})
    if leverage_gate.get("enabled", False):
        d2e = risk_metrics.get("debt_to_equity")
        ic = risk_metrics.get("interest_coverage")
        conds = leverage_gate.get("conditions", {})
        cap = leverage_gate.get("cap_value", 7.4)

        trigger = False
        reason_parts = []
        if d2e is not None and d2e > conds.get("debt_to_equity_threshold", 5.0):
            trigger = True
            reason_parts.append(f"D/E ratio of {d2e:.1f} exceeds {conds['debt_to_equity_threshold']}")
        if ic is not None and ic < conds.get("interest_coverage_threshold", 1.5):
            trigger = True
            reason_parts.append(f"Interest coverage of {ic:.1f}x below {conds['interest_coverage_threshold']}x")

        if trigger and overall_score > cap:
            applied.append({
                "type": "cap",
                "name": "Leverage Cap",
                "value": cap,
                "reason": "; ".join(reason_parts),
            })
            overall_score = cap

    # Gate 2: Negative FCF Penalty
    fcf_gate = gates.get("negative_fcf_penalty", {})
    if fcf_gate.get("enabled", False):
        neg_fcf_q = extra_flags.get("consecutive_negative_fcf_quarters", 0)
        dilution = extra_flags.get("dilution_pct", 0)
        conds = fcf_gate.get("conditions", {})
        penalty_range = fcf_gate.get("penalty_range", [0.5, 1.5])

        if (neg_fcf_q >= conds.get("consecutive_negative_fcf_quarters", 4) and
                dilution > conds.get("dilution_pct_threshold", 5.0)):
            # Scale penalty based on severity
            severity = min(1.0, dilution / 20.0)  # 20% dilution = max severity
            penalty = penalty_range[0] + severity * (penalty_range[1] - penalty_range[0])
            penalty = round(penalty, 1)
            overall_score -= penalty
            applied.append({
                "type": "penalty",
                "name": "Negative FCF + Dilution",
                "value": -penalty,
                "reason": f"{neg_fcf_q} consecutive quarters of negative FCF with {dilution:.1f}% dilution.",
            })

    # Gate 3: Volatility Penalty
    vol_gate = gates.get("volatility_penalty", {})
    if vol_gate.get("enabled", False):
        vol = risk_metrics.get("volatility_30d")
        drawdown = risk_metrics.get("max_drawdown_1y")
        conds = vol_gate.get("conditions", {})
        penalty_range = vol_gate.get("penalty_range", [0.5, 2.0])

        trigger = False
        reason_parts = []
        severity = 0.0

        if vol is not None and vol > conds.get("volatility_30d_threshold", 60.0):
            trigger = True
            severity = max(severity, min(1.0, (vol - 60) / 40))
            reason_parts.append(f"30d volatility of {vol:.1f}% exceeds threshold")

        if drawdown is not None and drawdown < conds.get("max_drawdown_threshold", -40.0):
            trigger = True
            severity = max(severity, min(1.0, abs(drawdown + 40) / 30))
            reason_parts.append(f"Max drawdown of {drawdown:.1f}% exceeds threshold")

        if trigger:
            penalty = penalty_range[0] + severity * (penalty_range[1] - penalty_range[0])
            penalty = round(penalty, 1)
            overall_score -= penalty
            applied.append({
                "type": "penalty",
                "name": "High Volatility/Drawdown",
                "value": -penalty,
                "reason": "; ".join(reason_parts),
            })

    # Clamp final score
    overall_score = round(max(0.0, min(10.0, overall_score)), 1)
    return overall_score, applied


def compute_conviction_score(
    ticker: str,
    quality_metrics: Dict[str, Optional[float]],
    value_metrics: Dict[str, Optional[float]],
    growth_metrics: Dict[str, Optional[float]],
    momentum_metrics: Dict[str, Optional[float]],
    risk_metrics: Dict[str, Optional[float]],
    extra_flags: Optional[Dict[str, Any]] = None,
    has_peer_group: bool = False,
) -> Dict:
    """
    Full conviction score computation pipeline:
    1. Compute pillar scores
    2. Weighted overall
    3. Apply risk gates
    4. Generate drivers
    5. Compute confidence
    6. Return full response payload
    """
    if extra_flags is None:
        extra_flags = {}

    # Step 1: Pillar scores
    pillar_scores = compute_all_pillars(
        quality_metrics, value_metrics, growth_metrics,
        momentum_metrics, risk_metrics, CONFIG,
    )

    # Step 2: Weighted overall
    pillar_weights = CONFIG.get("pillar_weights", {})
    raw_overall = weighted_average(pillar_scores, pillar_weights)

    # Step 3: Risk gates
    overall_score, penalties = apply_risk_gates(raw_overall, risk_metrics, extra_flags)

    # Step 4: Drivers
    metric_scores = {
        "quality": quality_metrics,
        "value": value_metrics,
        "growth": growth_metrics,
        "momentum": momentum_metrics,
        "risk": risk_metrics,
    }
    positive_drivers, negative_drivers = generate_drivers(
        pillar_scores, metric_scores, pillar_weights,
    )

    # Step 5: Confidence
    all_metrics = {}
    for m in [quality_metrics, value_metrics, growth_metrics, momentum_metrics, risk_metrics]:
        all_metrics.update(m)
    all_expected = []
    for section in ["quality_metrics", "value_metrics", "growth_metrics", "momentum_metrics", "risk_metrics"]:
        all_expected.extend(CONFIG.get(section, {}).keys())
    missing = count_missing_metrics(all_metrics, all_expected)
    confidence = compute_confidence(
        total_metrics=len(all_expected),
        missing_count=missing,
        has_peer_group=has_peer_group,
        penalty_per_missing=CONFIG.get("confidence", {}).get("missing_metric_penalty", 5),
        no_peer_penalty=CONFIG.get("confidence", {}).get("no_peer_group_penalty", 10),
        min_confidence=CONFIG.get("confidence", {}).get("min_confidence", 20),
    )

    # Step 6: Build response
    band = get_band(overall_score)

    return {
        "ticker": ticker.upper(),
        "overall_score": overall_score,
        "band": band,
        "pillars": pillar_scores,
        "drivers": {
            "positive": positive_drivers,
            "negative": negative_drivers,
        },
        "penalties_and_caps_applied": penalties,
        "confidence": confidence,
        "model_version": CONFIG.get("model_version", "apter_conviction_v1.0"),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
