from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from Core.signals.base import AlphaContext, SignalDecision
from Core.signals.structural import TrendPersistenceSignal, VolatilityExpansionSignal, LiquiditySeekingSignal, DealerGammaSignal
from Core.signals.statistical import MeanReversionSignal, LeadLagSignal, IntradaySeasonalitySignal
from Core.signals.execution import QueuePositionSignal, SpreadCaptureSignal, SlippageMinSignal, AdverseSelectionSignal


LOG = logging.getLogger("alpha_stack")


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing alpha stack config: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML must be a mapping at top-level: {path}")
    return data


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


@dataclass(frozen=True)
class AlphaStackDecision:
    allowed: bool
    direction: int
    alpha_score: float
    confidence: float
    urgency_tier: str
    module_results: Dict[str, SignalDecision]
    execution_hints: Dict[str, Any]
    reason: str

    def to_meta(self) -> Dict[str, Any]:
        return {
            "alpha": {
                "allowed": self.allowed,
                "direction": self.direction,
                "score": self.alpha_score,
                "confidence": self.confidence,
                "urgency": self.urgency_tier,
                "reason": self.reason,
                "modules": {
                    k: {
                        "kind": v.kind,
                        "active": v.active,
                        "direction": v.direction,
                        "score": v.score,
                        "confidence": v.confidence,
                        "urgency": v.urgency_tier(),
                        "reason": v.reason,
                        "outputs": v.outputs,
                    }
                    for k, v in self.module_results.items()
                },
                "execution_hints": dict(self.execution_hints),
            }
        }


class AlphaStack:
    """STEP 13: Strategy 'Alpha Source Stack' as modular signal components."""

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.cfg = _load_yaml(config_path)

        self.modules = {
            # Structural
            "trend_persistence": TrendPersistenceSignal(),
            "volatility_expansion": VolatilityExpansionSignal(),
            "liquidity_seeking": LiquiditySeekingSignal(),
            "dealer_gamma": DealerGammaSignal(),
            # Statistical
            "mean_reversion": MeanReversionSignal(),
            "lead_lag": LeadLagSignal(),
            "intraday_seasonality": IntradaySeasonalitySignal(),
            # Execution
            "queue_position": QueuePositionSignal(),
            "spread_capture": SpreadCaptureSignal(),
            "slippage_min": SlippageMinSignal(),
            "adverse_selection": AdverseSelectionSignal(),
        }

    def decide(self, ctx: AlphaContext) -> AlphaStackDecision:
        cfg = self.cfg.get("alpha_stack", {}) or {}

        mod_cfgs = cfg.get("modules", {}) or {}
        min_abs = float(cfg.get("min_abs_score_to_trade", 1.0))
        min_active = int(cfg.get("min_active_modules", 1))

        results: Dict[str, SignalDecision] = {}
        active_scores: List[Tuple[str, float, float]] = []  # (name, score, weight)

        for name, module in self.modules.items():
            mcfg = mod_cfgs.get(name, {}) or {}
            if not bool(mcfg.get("enabled", True)):
                results[name] = SignalDecision(module=name, kind=module.kind, active=False, reason="disabled")
                continue

            try:
                dec = module.compute(ctx, mcfg)
            except Exception as e:  # defensive - never crash trading path
                dec = SignalDecision(module=name, kind=module.kind, active=False, reason=f"error:{e}")

            results[name] = dec

            # Only structural + statistical contribute to alpha direction/score
            if dec.active and dec.kind in ("structural", "statistical") and dec.direction != 0:
                w = float(mcfg.get("weight", 1.0))
                active_scores.append((name, dec.score, w))

        # Aggregate alpha score
        alpha_score = 0.0
        for _, score, w in active_scores:
            alpha_score += float(score) * float(w)

        direction = _sign(alpha_score)
        abs_score = abs(alpha_score)
        active_count = len(active_scores)

        # Confidence: weighted mean of module confidences + clamp
        conf = 0.0
        denom = 0.0
        for name, module_dec in results.items():
            if module_dec.active and module_dec.kind in ("structural", "statistical"):
                w = float((mod_cfgs.get(name, {}) or {}).get("weight", 1.0))
                conf += module_dec.confidence * w
                denom += w
        confidence = _clamp(conf / denom, 0.0, 1.0) if denom > 0 else 0.0

        # Execution hints pass-through
        execution_hints: Dict[str, Any] = {}
        for name, dec in results.items():
            if dec.active and dec.kind == "execution":
                execution_hints[name] = dec.outputs

        # Urgency tier
        urg_cfg = cfg.get("urgency_thresholds", {}) or {}
        high_thr = float(urg_cfg.get("high_abs_score", 2.5))
        crit_thr = float(urg_cfg.get("critical_abs_score", 3.5))

        if abs_score >= crit_thr:
            urgency = "CRITICAL"
        elif abs_score >= high_thr:
            urgency = "HIGH"
        elif abs_score >= min_abs:
            urgency = "NORMAL"
        else:
            urgency = "LOW"

        allowed = (direction != 0) and (abs_score >= min_abs) and (active_count >= min_active)
        reason = "ok" if allowed else "alpha_below_threshold_or_inactive"

        return AlphaStackDecision(
            allowed=allowed,
            direction=direction,
            alpha_score=alpha_score,
            confidence=confidence,
            urgency_tier=urgency,
            module_results=results,
            execution_hints=execution_hints,
            reason=reason,
        )
