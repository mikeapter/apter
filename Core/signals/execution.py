from __future__ import annotations

from typing import Dict, Any

from .base import AlphaContext, SignalModule


class QueuePositionSignal(SignalModule):
    name = "queue_position"
    kind = "execution"
    priority = "CRITICAL"

    def compute(self, ctx: AlphaContext, cfg: Dict[str, Any]):
        fp = self._to_float(ctx.f("fill_probability", None), None)
        eft = self._to_float(ctx.f("expected_fill_time_s", None), None)
        if fp is None or eft is None:
            return self._inactive("missing:fill_probability|expected_fill_time_s")

        max_wait = float((cfg.get("thresholds", {}) or {}).get("max_wait_time_s", 3.0))
        urgency = ctx.m("signal_urgency", None)

        if isinstance(urgency, (int, float)):
            urg_f = float(urgency)
        elif isinstance(urgency, str):
            t = urgency.strip().upper()
            urg_f = {"LOW": 0.1, "NORMAL": 0.4, "HIGH": 0.7, "CRITICAL": 0.9}.get(t, 0.4)
        else:
            urg_f = 0.4

        if fp < 0.3 or eft > max_wait:
            action = "aggressive"
        elif fp > 0.7:
            action = "passive"
        else:
            action = "repricing" if urg_f >= 0.6 else "passive"

        conf = min(1.0, 0.5 + 0.5 * abs(fp - 0.5) * 2.0)
        return self._mk(
            active=True,
            direction=0,
            score=0.0,
            confidence=conf,
            urgency=min(1.0, urg_f),
            reason="ok",
            outputs={"order_action": action, "fill_probability": fp, "expected_fill_time_s": eft},
        )


class SpreadCaptureSignal(SignalModule):
    name = "spread_capture"
    kind = "execution"
    priority = "CRITICAL"

    def compute(self, ctx: AlphaContext, cfg: Dict[str, Any]):
        spread_bps = self._to_float(ctx.q("spread_bps", ctx.f("spread_bps", None)), None)
        if spread_bps is None:
            return self._inactive("missing:spread_bps")

        thr = float((cfg.get("thresholds", {}) or {}).get("min_profitable_spread_bps", 8.0))
        active = float(spread_bps) >= thr

        return self._mk(
            active=active,
            direction=0,
            score=0.0,
            confidence=min(1.0, float(spread_bps) / max(thr, 1e-9)) if active else 0.0,
            urgency=0.10 if active else 0.0,
            reason="ok" if active else "spread_too_tight",
            outputs={"spread_capture_active": bool(active), "spread_bps": spread_bps},
        )


class SlippageMinSignal(SignalModule):
    name = "slippage_min"
    kind = "execution"
    priority = "CRITICAL"

    def compute(self, ctx: AlphaContext, cfg: Dict[str, Any]):
        order_size = self._to_float(ctx.m("order_size", None), None)
        avg_vol_per_min = self._to_float(ctx.f("avg_volume_per_minute", None), None)
        volatility = self._to_float(ctx.f("volatility", None), None)

        if order_size is None or avg_vol_per_min is None or volatility is None:
            return self._inactive("missing:order_size|avg_volume_per_minute|volatility")

        vol_thr = float((cfg.get("thresholds", {}) or {}).get("low_volatility_threshold", 0.01))
        if float(order_size) > float(avg_vol_per_min) * 0.1:
            method = "twap" if float(volatility) < vol_thr else "vwap"
        else:
            method = "market"

        return self._mk(
            active=True,
            direction=0,
            score=0.0,
            confidence=0.70,
            urgency=0.20,
            reason="ok",
            outputs={"execution_method": method, "order_size": order_size},
        )


class AdverseSelectionSignal(SignalModule):
    name = "adverse_selection"
    kind = "execution"
    priority = "CRITICAL"

    def compute(self, ctx: AlphaContext, cfg: Dict[str, Any]):
        adverse_score = self._to_float(ctx.f("adverse_selection_score", None), None)

        thr = cfg.get("thresholds", {}) or {}
        score_thr = float(thr.get("score_threshold", 70.0))

        if adverse_score is not None:
            detected = float(adverse_score) > score_thr
            return self._mk(
                active=True,
                direction=0,
                score=0.0,
                confidence=1.0,
                urgency=0.70 if detected else 0.20,
                reason="ok",
                outputs={"adverse_selection_detected": bool(detected), "adverse_selection_score": adverse_score},
            )

        latency_ms = self._to_float(ctx.f("latency_ms", None), None)
        stale = bool(ctx.f("stale_quote_flag", False))

        latency_thr = float(thr.get("latency_ms_threshold", 50.0))
        detected = bool(stale) or (latency_ms is not None and float(latency_ms) > latency_thr)

        return self._mk(
            active=True,
            direction=0,
            score=0.0,
            confidence=0.8,
            urgency=0.75 if detected else 0.10,
            reason="ok",
            outputs={"adverse_selection_detected": bool(detected), "latency_ms": latency_ms, "stale_quote": stale},
        )
