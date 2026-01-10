from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _safe_upper(x: Optional[str], default: str) -> str:
    s = (x or default).strip().upper()
    return s if s else default


def _spread_pct(bid: float, ask: float) -> float:
    mid = (bid + ask) / 2.0
    if mid <= 0:
        return 1.0
    return (ask - bid) / mid


@dataclass(frozen=True)
class StopInputs:
    symbol: str
    side: str                 # "BUY"/"SELL" or "buy"/"sell"
    entry_price: float
    regime: str
    strategy_id: str
    confidence: Optional[float] = None  # 0..1

    # optional market microstructure
    bid: Optional[float] = None
    ask: Optional[float] = None

    # optional volatility input (if you have it)
    atr: Optional[float] = None

    # optional for max-loss enforcement
    equity_usd: Optional[float] = None
    qty: Optional[int] = None


@dataclass(frozen=True)
class StopResult:
    stop_price: float
    stop_distance_usd: float

    # diagnostics
    method: str
    base_distance_usd: float
    regime_mult: float
    liquidity_mult: float
    buffer_usd: float
    spread_pct: Optional[float]

    # max loss enforcement outputs
    max_loss_usd: Optional[float]
    max_qty_for_loss: Optional[int]
    qty_capped_to: Optional[int]

    blocked: bool
    reason: str


class StopModule:
    """
    STEP 11 — Stops module
    - Base stop definition (PCT or ATR)
    - Regime-based stop multipliers
    - Liquidity-based widening + buffer (spread-aware)
    - Max loss per trade enforcement (caps qty if provided)

    Engineering logic only.
    """

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._cfg: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Stops config not found: {self.config_path}")
        with self.config_path.open("r", encoding="utf-8") as f:
            self._cfg = yaml.safe_load(f) or {}
        if not isinstance(self._cfg, dict):
            raise ValueError("Stops YAML must be a mapping at top-level")

    # ---------------------------
    # Confidence multiplier (same shape as sizing)
    # ---------------------------
    def _confidence_mult(self, conf: Optional[float]) -> float:
        c = self._cfg.get("confidence", {}) or {}
        if not bool(c.get("enabled", True)):
            return 1.0
        if conf is None:
            return 1.0

        conf = _clamp(float(conf), 0.0, 1.0)
        min_conf = float(c.get("min_conf", 0.20))
        max_conf = float(c.get("max_conf", 0.80))
        floor_mult = float(c.get("floor_mult", 0.80))
        ceil_mult = float(c.get("ceil_mult", 1.10))

        if max_conf <= min_conf:
            return 1.0

        conf_clip = _clamp(conf, min_conf, max_conf)
        t = (conf_clip - min_conf) / (max_conf - min_conf)  # 0..1
        return floor_mult + t * (ceil_mult - floor_mult)

    # ---------------------------
    # Max-loss budget (optional enforcement)
    # ---------------------------
    def max_loss_budget_usd(
        self,
        *,
        equity_usd: float,
        regime: str,
        strategy_id: str,
        confidence: Optional[float],
    ) -> Optional[float]:
        mx = self._cfg.get("max_loss", {}) or {}
        if not bool(mx.get("enabled", True)):
            return None

        if equity_usd <= 0:
            return None

        # risk pct default + optional strategy override
        default_risk_pct = float(mx.get("risk_per_trade_pct", 0.0025))
        strat = (mx.get("strategies", {}) or {}).get(strategy_id, {}) or {}
        risk_pct = float(strat.get("risk_per_trade_pct", default_risk_pct))

        # regime multiplier (for max-loss budget)
        reg_mults = mx.get("regime_multipliers", {}) or {}
        reg = _safe_upper(regime, "UNKNOWN")
        regime_mult = float(reg_mults.get(reg, reg_mults.get("UNKNOWN", 1.0)))

        # confidence multiplier
        conf_mult = self._confidence_mult(confidence)

        budget = equity_usd * risk_pct * regime_mult * conf_mult

        # hard cap
        cap = mx.get("max_risk_usd", None)
        if cap is not None:
            budget = min(budget, float(cap))

        # if regime_mult is 0 => budget is 0 => block upstream
        return max(0.0, float(budget))

    def cap_qty_for_max_loss(
        self,
        *,
        qty: int,
        stop_distance_usd: float,
        equity_usd: float,
        regime: str,
        strategy_id: str,
        confidence: Optional[float],
    ) -> Tuple[int, Optional[float]]:
        budget = self.max_loss_budget_usd(
            equity_usd=equity_usd,
            regime=regime,
            strategy_id=strategy_id,
            confidence=confidence,
        )
        if budget is None:
            return qty, None
        if stop_distance_usd <= 0:
            return 0, budget

        max_qty = int(budget // stop_distance_usd)
        if max_qty < 0:
            max_qty = 0
        return int(min(qty, max_qty)), budget

    # ---------------------------
    # Main stop computation
    # ---------------------------
    def compute(self, inp: StopInputs) -> StopResult:
        base = self._cfg.get("base", {}) or {}
        liq = self._cfg.get("liquidity", {}) or {}
        reg_mults = self._cfg.get("regime_multipliers", {}) or {}

        sym = (inp.symbol or "").upper()
        side = (inp.side or "").strip().upper()
        if side not in {"BUY", "SELL"}:
            # allow "buy"/"sell"
            if side.lower() == "buy":
                side = "BUY"
            elif side.lower() == "sell":
                side = "SELL"
            else:
                return StopResult(
                    stop_price=0.0,
                    stop_distance_usd=0.0,
                    method="UNKNOWN",
                    base_distance_usd=0.0,
                    regime_mult=0.0,
                    liquidity_mult=0.0,
                    buffer_usd=0.0,
                    spread_pct=None,
                    max_loss_usd=None,
                    max_qty_for_loss=None,
                    qty_capped_to=None,
                    blocked=True,
                    reason=f"BLOCK: invalid side '{inp.side}' for {sym}",
                )

        if inp.entry_price <= 0:
            return StopResult(
                stop_price=0.0,
                stop_distance_usd=0.0,
                method="UNKNOWN",
                base_distance_usd=0.0,
                regime_mult=0.0,
                liquidity_mult=0.0,
                buffer_usd=0.0,
                spread_pct=None,
                max_loss_usd=None,
                max_qty_for_loss=None,
                qty_capped_to=None,
                blocked=True,
                reason=f"BLOCK: entry_price must be > 0 for {sym}",
            )

        method = _safe_upper(str(base.get("method", "PCT")), "PCT")

        stop_pct = float(base.get("stop_pct", 0.005))
        atr_mult = float(base.get("atr_multiple", 1.5))

        # base distance
        if method == "ATR":
            if inp.atr is not None and float(inp.atr) > 0:
                base_dist = float(inp.atr) * atr_mult
            else:
                # fallback
                base_dist = inp.entry_price * stop_pct
        else:
            # PCT default
            base_dist = inp.entry_price * stop_pct
            method = "PCT"

        # clamp base distance by min/max pct
        min_stop_pct = float(base.get("min_stop_pct", 0.001))
        max_stop_pct = float(base.get("max_stop_pct", 0.050))

        min_dist = inp.entry_price * max(0.0, min_stop_pct)
        max_dist = inp.entry_price * max(0.0, max_stop_pct)
        if max_dist > 0:
            base_dist = _clamp(base_dist, min_dist, max_dist)

        # regime multiplier for stop width
        reg = _safe_upper(inp.regime, "UNKNOWN")
        regime_mult = float(reg_mults.get(reg, reg_mults.get("UNKNOWN", 1.0)))
        if regime_mult <= 0:
            return StopResult(
                stop_price=0.0,
                stop_distance_usd=0.0,
                method=method,
                base_distance_usd=float(base_dist),
                regime_mult=regime_mult,
                liquidity_mult=0.0,
                buffer_usd=0.0,
                spread_pct=None,
                max_loss_usd=None,
                max_qty_for_loss=None,
                qty_capped_to=None,
                blocked=True,
                reason=f"BLOCK: regime stop multiplier <= 0 for regime={reg}",
            )

        dist = float(base_dist) * regime_mult

        # liquidity widening + buffer
        liquidity_mult = 1.0
        buffer_usd = 0.0
        sp_pct: Optional[float] = None

        if bool(liq.get("enabled", True)) and inp.bid is not None and inp.ask is not None:
            bid = float(inp.bid)
            ask = float(inp.ask)
            sp_pct = _spread_pct(bid, ask)

            max_spread_pct = float(liq.get("max_spread_pct", 0.02))
            if bool(liq.get("block_if_spread_too_wide", False)) and sp_pct > max_spread_pct:
                return StopResult(
                    stop_price=0.0,
                    stop_distance_usd=0.0,
                    method=method,
                    base_distance_usd=float(base_dist),
                    regime_mult=regime_mult,
                    liquidity_mult=0.0,
                    buffer_usd=0.0,
                    spread_pct=sp_pct,
                    max_loss_usd=None,
                    max_qty_for_loss=None,
                    qty_capped_to=None,
                    blocked=True,
                    reason=f"BLOCK: spread {sp_pct:.3%} > max_spread_pct {max_spread_pct:.3%}",
                )

            widen_threshold_pct = float(liq.get("widen_threshold_pct", 0.0015))
            slope = float(liq.get("widen_slope", 0.75))
            max_widen = float(liq.get("max_widen_mult", 1.75))

            if widen_threshold_pct > 0 and sp_pct > widen_threshold_pct:
                excess = (sp_pct - widen_threshold_pct) / widen_threshold_pct
                liquidity_mult = 1.0 + slope * excess
                liquidity_mult = _clamp(liquidity_mult, 1.0, max_widen)
                dist *= liquidity_mult

            # add a buffer in bps (spread-aware)
            spread_bps = sp_pct * 10000.0
            min_buffer_bps = float(liq.get("min_buffer_bps", 2.0))
            per_spread_bps = float(liq.get("buffer_bps_per_spread_bps", 0.50))
            max_buffer_bps = float(liq.get("max_buffer_bps", 12.0))

            buffer_bps = max(min_buffer_bps, spread_bps * per_spread_bps)
            buffer_bps = min(buffer_bps, max_buffer_bps)

            buffer_usd = inp.entry_price * (buffer_bps / 10000.0)
            dist += buffer_usd

        # final sanity
        dist = float(dist)
        if dist <= 0:
            return StopResult(
                stop_price=0.0,
                stop_distance_usd=0.0,
                method=method,
                base_distance_usd=float(base_dist),
                regime_mult=regime_mult,
                liquidity_mult=float(liquidity_mult),
                buffer_usd=float(buffer_usd),
                spread_pct=sp_pct,
                max_loss_usd=None,
                max_qty_for_loss=None,
                qty_capped_to=None,
                blocked=True,
                reason="BLOCK: computed stop distance <= 0",
            )

        stop_price = inp.entry_price - dist if side == "BUY" else inp.entry_price + dist

        # max-loss enforcement outputs
        qty_capped_to: Optional[int] = None
        max_loss_usd: Optional[float] = None
        max_qty_for_loss: Optional[int] = None

        if inp.equity_usd is not None and float(inp.equity_usd) > 0:
            max_loss_usd = self.max_loss_budget_usd(
                equity_usd=float(inp.equity_usd),
                regime=inp.regime,
                strategy_id=_safe_upper(inp.strategy_id, "UNKNOWN"),
                confidence=inp.confidence,
            )

            if max_loss_usd is not None:
                max_qty_for_loss = int(max_loss_usd // dist) if dist > 0 else 0
                if max_qty_for_loss < 0:
                    max_qty_for_loss = 0

                if inp.qty is not None:
                    qty_capped_to = int(min(int(inp.qty), max_qty_for_loss))

        return StopResult(
            stop_price=float(stop_price),
            stop_distance_usd=float(dist),
            method=method,
            base_distance_usd=float(base_dist),
            regime_mult=float(regime_mult),
            liquidity_mult=float(liquidity_mult),
            buffer_usd=float(buffer_usd),
            spread_pct=sp_pct,
            max_loss_usd=max_loss_usd,
            max_qty_for_loss=max_qty_for_loss,
            qty_capped_to=qty_capped_to,
            blocked=False,
            reason="OK",
        )
