from __future__ import annotations

try:
    from zoneinfo import ZoneInfo  # py3.9+
except Exception:
    ZoneInfo = None  # type: ignore

from typing import Dict, Any

from .base import AlphaContext, SignalModule


class MeanReversionSignal(SignalModule):
    name = "mean_reversion"
    kind = "statistical"
    priority = "MEDIUM"

    def compute(self, ctx: AlphaContext, cfg: Dict[str, Any]):
        activation = cfg.get("activation", {}) or {}
        allowed_regimes = [str(x).upper() for x in activation.get("regimes_allow", ["DIRECTIONAL_COMPRESSION", "VOLATILITY_COMPRESSION"])]

        if str(ctx.regime_label or "UNKNOWN").upper() not in allowed_regimes:
            return self._inactive(f"regime_block({ctx.regime_label})")

        if bool(ctx.m("structural_trend_override", False)):
            return self._inactive("blocked_by_structural_trend")

        z = self._to_float(ctx.f("z_score_vwap", None), None)
        boll = self._to_float(ctx.f("bollinger_position", None), None)
        if z is None and boll is None:
            return self._inactive("missing:z_score_vwap|bollinger_position")

        sr = self._to_float(ctx.f("reversion_success_rate", None), None)
        sr_min = float(activation.get("min_success_rate", 0.55))
        if sr is not None and sr < sr_min:
            return self._inactive(f"low_success_rate({sr:.2f} < {sr_min:.2f})")

        direction = 0
        if z is not None:
            if z > 2.5:
                direction = -1
            elif z < -2.5:
                direction = 1
        if direction == 0 and boll is not None:
            if boll > 0.95:
                direction = -1
            elif boll < 0.05:
                direction = 1

        if direction == 0:
            return self._mk(
                active=False,
                direction=0,
                score=0.0,
                confidence=0.0,
                urgency=0.0,
                reason="no_deviation",
                outputs={"reversion_signal": 0, "z_score_vwap": z, "bollinger_position": boll, "success_rate": sr},
            )

        conf = 0.60 if sr is None else max(0.0, min(1.0, sr / 0.50))
        urg = min(1.0, 0.25 + 0.65 * conf)
        mag = abs(z) if z is not None else 2.5
        score = direction * min(4.0, mag / 2.5)

        return self._mk(
            active=True,
            direction=direction,
            score=score,
            confidence=conf,
            urgency=urg,
            reason="ok",
            outputs={"reversion_signal": direction, "z_score_vwap": z, "bollinger_position": boll, "success_rate": sr},
        )


class LeadLagSignal(SignalModule):
    name = "lead_lag"
    kind = "statistical"
    priority = "MEDIUM"

    def compute(self, ctx: AlphaContext, cfg: Dict[str, Any]):
        act = cfg.get("activation", {}) or {}
        lead_strength_min = float(act.get("min_lead_strength", 0.7))
        leader_move_thr = float(act.get("leader_move_threshold", 0.01))

        leader_move = self._to_float(ctx.f("leader_move", None), None)
        lead_strength = self._to_float(ctx.f("lead_strength", None), None)
        beta = self._to_float(ctx.f("beta", None), 1.0) or 1.0
        optimal_lag = self._to_float(ctx.f("optimal_lag", None), None)

        if leader_move is None or lead_strength is None:
            return self._inactive("missing:leader_move|lead_strength")

        if abs(leader_move) < leader_move_thr:
            return self._inactive(f"leader_move_below_threshold({leader_move:.3f})")

        if abs(lead_strength) < lead_strength_min:
            return self._inactive(f"weak_lead_strength({lead_strength:.2f})")

        expected = float(leader_move) * float(beta) * float(lead_strength)
        direction = self._sign(expected)

        conf = min(1.0, abs(float(lead_strength)))
        urg = min(1.0, 0.30 + 0.60 * conf)
        score = direction * min(3.0, abs(expected) / max(leader_move_thr, 1e-9))

        return self._mk(
            active=True,
            direction=direction,
            score=score,
            confidence=conf,
            urgency=urg,
            reason="ok",
            outputs={
                "expected_lagger_move": expected,
                "leader_move": leader_move,
                "lead_strength": lead_strength,
                "beta": beta,
                "optimal_lag": optimal_lag,
            },
        )


class IntradaySeasonalitySignal(SignalModule):
    name = "intraday_seasonality"
    kind = "statistical"
    priority = "MEDIUM"

    def compute(self, ctx: AlphaContext, cfg: Dict[str, Any]):
        now = ctx.now
        if ZoneInfo is not None:
            try:
                now = now.astimezone(ZoneInfo("America/New_York"))
            except Exception:
                pass

        hhmm = now.hour * 60 + now.minute

        def in_range(sh: int, sm: int, eh: int, em: int) -> bool:
            s = sh * 60 + sm
            e = eh * 60 + em
            return s <= hhmm < e

        bias = "neutral"
        size_mult = 1.0

        if in_range(9, 30, 10, 0):
            bias = "breakout"
            size_mult = 1.0
        elif in_range(12, 0, 13, 0):
            bias = "mean_reversion"
            size_mult = 0.6
        elif in_range(15, 0, 16, 0):
            bias = "trend"
            size_mult = 1.2

        edge = self._to_float(ctx.f("seasonality_edge", None), None)
        min_edge = float((cfg.get("thresholds", {}) or {}).get("min_edge", 0.15))

        active = (bias != "neutral") and (edge is None or edge >= min_edge)

        if not active:
            return self._mk(
                active=False,
                direction=0,
                score=0.0,
                confidence=0.0,
                urgency=0.0,
                reason="neutral_or_low_edge",
                outputs={"time_of_day_bias": bias, "size_multiplier": size_mult, "seasonality_edge": edge},
            )

        conf = 0.50 if edge is None else min(1.0, float(edge) / max(min_edge, 1e-9))
        return self._mk(
            active=True,
            direction=0,
            score=0.0,
            confidence=conf,
            urgency=0.20,
            reason="ok",
            outputs={"time_of_day_bias": bias, "size_multiplier": size_mult, "seasonality_edge": edge},
        )
