from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _round_to_step(x: float, step: float) -> float:
    if step <= 0:
        return x
    return round(x / step) * step


@dataclass(frozen=True)
class SizeInputs:
    equity_usd: float
    price: float
    stop_distance_usd: Optional[float]  # $ risk per share/contract to stop
    regime: str
    strategy_id: str
    confidence: Optional[float] = None  # 0..1


@dataclass(frozen=True)
class SizeResult:
    qty: float
    notional_usd: float
    risk_usd: float

    regime: str
    strategy_id: str

    base_risk_pct: float
    regime_mult: float
    confidence_mult: float
    strategy_mult: float

    blocked: bool
    reason: str


class PositionSizer:
    """
    Risk-based sizing with regime + confidence multipliers and hard clamps.

    This is engineering logic, not investment advice.
    """

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._cfg: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Position sizing config not found: {self.config_path}")
        with self.config_path.open("r", encoding="utf-8") as f:
            self._cfg = yaml.safe_load(f) or {}

    def _get_strategy_overrides(self, strategy_id: str) -> Tuple[Optional[float], float]:
        strategies = self._cfg.get("strategies", {}) or {}
        s = strategies.get(strategy_id, {}) or {}
        risk_pct = s.get("risk_per_trade_pct", None)
        strat_mult = float(s.get("strategy_mult", 1.0))
        return (risk_pct, strat_mult)

    def _confidence_multiplier(self, conf: Optional[float]) -> float:
        c_cfg = self._cfg.get("confidence", {}) or {}
        if not bool(c_cfg.get("enabled", True)):
            return 1.0

        if conf is None:
            return 1.0  # neutral if missing

        conf = _clamp(float(conf), 0.0, 1.0)

        min_conf = float(c_cfg.get("min_conf", 0.2))
        max_conf = float(c_cfg.get("max_conf", 0.8))
        floor_mult = float(c_cfg.get("floor_mult", 0.5))
        ceil_mult = float(c_cfg.get("ceil_mult", 1.25))

        if max_conf <= min_conf:
            return 1.0

        conf_clip = _clamp(conf, min_conf, max_conf)
        t = (conf_clip - min_conf) / (max_conf - min_conf)  # 0..1
        return floor_mult + t * (ceil_mult - floor_mult)

    def size(self, inp: SizeInputs) -> SizeResult:
        base = self._cfg.get("base", {}) or {}
        clamps = self._cfg.get("clamps", {}) or {}
        reg_mults = self._cfg.get("regime_multipliers", {}) or {}

        regime = (inp.regime or "UNKNOWN").strip().upper()
        strategy_id = (inp.strategy_id or "").strip().upper()

        if inp.equity_usd <= 0:
            return SizeResult(
                qty=0, notional_usd=0, risk_usd=0,
                regime=regime, strategy_id=strategy_id,
                base_risk_pct=0, regime_mult=0, confidence_mult=0, strategy_mult=0,
                blocked=True, reason="BLOCK: equity_usd must be > 0",
            )

        if inp.price <= 0:
            return SizeResult(
                qty=0, notional_usd=0, risk_usd=0,
                regime=regime, strategy_id=strategy_id,
                base_risk_pct=0, regime_mult=0, confidence_mult=0, strategy_mult=0,
                blocked=True, reason="BLOCK: price must be > 0",
            )

        # ---- base risk pct + optional strategy override ----
        default_risk_pct = float(base.get("risk_per_trade_pct", 0.0025))
        override_risk_pct, strategy_mult = self._get_strategy_overrides(strategy_id)
        risk_pct = float(override_risk_pct) if override_risk_pct is not None else default_risk_pct

        # ---- regime multiplier ----
        regime_mult = float(reg_mults.get(regime, reg_mults.get("UNKNOWN", 0.0)))
        if regime_mult <= 0.0:
            return SizeResult(
                qty=0, notional_usd=0, risk_usd=0,
                regime=regime, strategy_id=strategy_id,
                base_risk_pct=risk_pct, regime_mult=regime_mult,
                confidence_mult=0.0, strategy_mult=float(strategy_mult),
                blocked=True, reason="BLOCK: regime multiplier <= 0",
            )

        # ---- confidence multiplier ----
        conf_mult = self._confidence_multiplier(inp.confidence)

        # ---- stop distance ----
        stop_distance = inp.stop_distance_usd
        if stop_distance is None:
            min_stop_pct = float(base.get("min_stop_distance_pct", 0.001))
            stop_distance = inp.price * max(min_stop_pct, 0.0)

        stop_distance = float(stop_distance)
        if stop_distance <= 0:
            return SizeResult(
                qty=0, notional_usd=0, risk_usd=0,
                regime=regime, strategy_id=strategy_id,
                base_risk_pct=risk_pct, regime_mult=regime_mult,
                confidence_mult=conf_mult, strategy_mult=float(strategy_mult),
                blocked=True, reason="BLOCK: stop_distance_usd must be > 0",
            )

        # ---- risk budget ----
        risk_usd = inp.equity_usd * risk_pct
        risk_usd *= regime_mult
        risk_usd *= conf_mult
        risk_usd *= float(strategy_mult)

        # hard cap risk
        max_risk_usd = float(clamps.get("max_risk_usd", risk_usd))
        risk_usd = min(risk_usd, max_risk_usd)

        # ---- raw qty ----
        qty = risk_usd / stop_distance

        # ---- notional clamps ----
        notional = qty * inp.price
        min_notional = float(clamps.get("min_notional_usd", 0.0))
        max_notional = float(clamps.get("max_notional_usd", float("inf")))

        if max_notional > 0:
            notional = _clamp(notional, min_notional, max_notional)
            qty = notional / inp.price

        # ---- qty clamps ----
        min_qty = float(clamps.get("min_qty", 0.0))
        max_qty = float(clamps.get("max_qty", float("inf")))
        qty = _clamp(qty, min_qty, max_qty)

        # ---- rounding ----
        step = float(base.get("qty_step", 1))
        qty = _round_to_step(qty, step)
        qty = max(0.0, qty)

        notional = qty * inp.price
        realized_risk = qty * stop_distance

        blocked = qty <= 0.0
        reason = "OK" if not blocked else "BLOCK: qty computed as 0"

        return SizeResult(
            qty=qty,
            notional_usd=notional,
            risk_usd=realized_risk,
            regime=regime,
            strategy_id=strategy_id,
            base_risk_pct=risk_pct,
            regime_mult=regime_mult,
            confidence_mult=conf_mult,
            strategy_mult=float(strategy_mult),
            blocked=blocked,
            reason=reason,
        )
