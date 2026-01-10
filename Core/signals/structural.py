from __future__ import annotations

from typing import Dict, Any

from .base import AlphaContext, SignalModule


class TrendPersistenceSignal(SignalModule):
    name = "trend_persistence"
    kind = "structural"
    priority = "HIGHEST"

    def compute(self, ctx: AlphaContext, cfg: Dict[str, Any]):
        thr = (cfg.get("thresholds", {}) or {})
        strong_abs = float(thr.get("strong_abs", 2.5))
        weak_abs = float(thr.get("weak_abs", 1.0))

        ps = self._to_float(ctx.f("persistence_score", None), None)

        if ps is None:
            gap = self._to_float(ctx.f("gap_pct", None), None)
            base = self._to_float(ctx.f("gap_base_pct", None), 0.02) or 0.02
            if gap is None:
                return self._inactive("missing:persistence_score|gap_pct")
            ps = (gap / base)

        direction = self._sign(ps)
        abs_ps = abs(ps)

        if abs_ps < weak_abs:
            return self._mk(
                active=False,
                direction=0,
                score=0.0,
                confidence=min(0.30, abs_ps / max(weak_abs, 1e-9)),
                urgency=0.0,
                reason=f"weak_trend(abs={abs_ps:.2f} < {weak_abs:.2f})",
                outputs={"persistence_score": ps, "trend_direction": 0, "state": "WEAK"},
            )

        state = "STRONG" if abs_ps >= strong_abs else "NEUTRAL"
        conf = min(1.0, abs_ps / max(strong_abs, 1e-9))
        urg = min(1.0, 0.25 + 0.75 * conf)

        return self._mk(
            active=True,
            direction=direction,
            score=float(ps),
            confidence=conf,
            urgency=urg,
            reason="ok",
            outputs={"persistence_score": ps, "trend_direction": direction, "state": state},
        )


class VolatilityExpansionSignal(SignalModule):
    name = "volatility_expansion"
    kind = "structural"
    priority = "HIGHEST"

    def compute(self, ctx: AlphaContext, cfg: Dict[str, Any]):
        thr = (cfg.get("thresholds", {}) or {})
        exp_ratio_thr = float(thr.get("expansion_ratio", 1.5))
        skew_up = float(thr.get("skew_up", 1.2))
        skew_dn = float(thr.get("skew_down", 0.8))

        exp_ratio = self._to_float(ctx.f("expansion_ratio", None), None)
        vol_skew = self._to_float(ctx.f("vol_skew", None), None)

        if exp_ratio is None:
            rv_short = self._to_float(ctx.f("rv_short", None), None)
            rv_med = self._to_float(ctx.f("rv_medium", None), None)
            if rv_short is not None and rv_med and rv_med > 0:
                exp_ratio = rv_short / rv_med

        if exp_ratio is None:
            return self._inactive("missing:expansion_ratio|rv_short+rv_medium")

        state = "stable"
        active = False

        if exp_ratio > exp_ratio_thr:
            state = "expanding"
            active = True
        elif exp_ratio < (1.0 / max(exp_ratio_thr, 1e-9)):
            state = "compressing"
            active = True

        asym = "neutral"
        if vol_skew is not None:
            if vol_skew > skew_up:
                asym = "upside"
            elif vol_skew < skew_dn:
                asym = "downside"

        mom = self._to_float(ctx.f("momentum", None), 0.0) or 0.0
        direction = self._sign(mom) if state == "expanding" else 0

        raw = (float(exp_ratio) - 1.0)
        score = raw * (direction if direction != 0 else 1.0)
        conf = min(1.0, abs(raw) / max(exp_ratio_thr - 1.0, 1e-9))
        urg = min(1.0, 0.20 + 0.70 * conf)

        return self._mk(
            active=active,
            direction=direction,
            score=score if active else 0.0,
            confidence=conf if active else 0.0,
            urgency=urg if active else 0.0,
            reason="ok" if active else "stable",
            outputs={"expansion_ratio": exp_ratio, "vol_skew": vol_skew, "asymmetry": asym, "expansion_state": state},
        )


class LiquiditySeekingSignal(SignalModule):
    name = "liquidity_seeking"
    kind = "structural"
    priority = "HIGHEST"

    def compute(self, ctx: AlphaContext, cfg: Dict[str, Any]):
        dist = self._to_float(ctx.f("liquidity_zone_distance_pct", None), None)
        approaching = bool(ctx.f("approaching_liquidity_zone", False))
        target = self._to_float(ctx.f("target_liquidity_zone_price", None), None)
        px = self._to_float(ctx.q("last", ctx.f("price", None)), None)

        thr = cfg.get("thresholds", {}) or {}
        max_dist = float(thr.get("max_distance_pct", 0.001))

        if dist is None or px is None or target is None:
            return self._inactive("missing:liquidity_zone_distance_pct|price|target_liquidity_zone_price")

        active = abs(dist) <= max_dist and approaching
        if not active:
            return self._mk(
                active=False,
                direction=0,
                score=0.0,
                confidence=0.0,
                urgency=0.0,
                reason="not_near_liquidity_zone",
                outputs={"liquidity_seeking": False, "target_price": target, "distance_pct": dist},
            )

        direction = self._sign(float(target) - float(px))
        conf = min(1.0, (max_dist - abs(float(dist))) / max(max_dist, 1e-9))
        urg = min(1.0, 0.35 + 0.65 * conf)

        return self._mk(
            active=True,
            direction=direction,
            score=direction * (1.0 + 2.0 * conf),
            confidence=conf,
            urgency=urg,
            reason="ok",
            outputs={"liquidity_seeking": True, "target_price": target, "distance_pct": dist},
        )


class DealerGammaSignal(SignalModule):
    name = "dealer_gamma"
    kind = "structural"
    priority = "HIGHEST"

    def compute(self, ctx: AlphaContext, cfg: Dict[str, Any]):
        net_gamma = self._to_float(ctx.f("net_gamma", None), None)
        spot = self._to_float(ctx.f("spot", None), None)
        flip = self._to_float(ctx.f("gamma_flip_level", None), None)

        if net_gamma is None or spot is None or flip is None:
            return self._inactive("missing:net_gamma|spot|gamma_flip_level")

        regime = "negative_gamma" if net_gamma < 0 else ("positive_gamma_above" if spot > flip else "positive_gamma_below")
        mult = {
            "positive_gamma_above": 0.7,
            "positive_gamma_below": 1.3,
            "negative_gamma": 1.8,
        }.get(regime, 1.0)

        return self._mk(
            active=True,
            direction=0,
            score=0.0,
            confidence=1.0,
            urgency=0.60 if regime == "negative_gamma" else 0.20,
            reason="ok",
            outputs={"gamma_regime": regime, "volatility_expectation_multiplier": float(mult)},
        )
