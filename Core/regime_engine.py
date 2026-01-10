# Core/regime_engine.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple, Any
import time

try:
    import yaml  # pip install pyyaml
except Exception as e:  # pragma: no cover
    yaml = None


class RegimeLabel(str, Enum):
    DIRECTIONAL_EXPANSION = "DIRECTIONAL_EXPANSION"
    DIRECTIONAL_COMPRESSION = "DIRECTIONAL_COMPRESSION"
    VOLATILITY_EXPANSION = "VOLATILITY_EXPANSION"
    VOLATILITY_COMPRESSION = "VOLATILITY_COMPRESSION"
    LIQUIDITY_VACUUM = "LIQUIDITY_VACUUM"
    EVENT_DOMINATED = "EVENT_DOMINATED"


@dataclass
class RegimeFeatures:
    # --- Vol ---
    rv_iv_z: Optional[float] = None

    # --- Trend ---
    trend_alignment: Optional[int] = None   # e.g., -5..+5
    trend_persistence: Optional[float] = None

    # --- Range ---
    range_expansion_ratio: Optional[float] = None
    range_percentile: Optional[float] = None

    # --- Liquidity ---
    spread_bps: Optional[float] = None
    depth_usd: Optional[float] = None

    # --- Events / shock ---
    event_risk_flag: bool = False
    shock_flag: bool = False

    # --- Cross asset (optional) ---
    cross_asset_risk_flag: bool = False


@dataclass
class RegimeOutput:
    label: RegimeLabel
    confidence: float  # 0..100
    transition_zone: bool
    candidate_label: Optional[RegimeLabel]
    scores: Dict[RegimeLabel, float] = field(default_factory=dict)
    votes: Dict[str, Optional[RegimeLabel]] = field(default_factory=dict)
    controls: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=lambda: time.time())


@dataclass
class _State:
    current: RegimeLabel = RegimeLabel.VOLATILITY_COMPRESSION
    since_ts: float = field(default_factory=lambda: time.time())
    candidate: Optional[RegimeLabel] = None
    candidate_streak: int = 0
    switch_count_window: int = 0
    last_switch_ts: float = field(default_factory=lambda: time.time())


def load_rce_config(path: str) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML not installed. Run: pip install pyyaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class RegimeEngine:
    """
    RCE = master state machine (hard gate).
    - Mutually exclusive regimes
    - Confirmation + hysteresis + minimum duration to prevent flapping
    - Confidence score (0..100)
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.state = _State()

    @classmethod
    def from_yaml(cls, path: str) -> "RegimeEngine":
        return cls(load_rce_config(path))

    def update(self, feats: RegimeFeatures, now_ts: Optional[float] = None) -> RegimeOutput:
        now = now_ts if now_ts is not None else time.time()

        votes = self._compute_votes(feats)
        scores = self._aggregate_scores(votes, feats)

        # Ensure every regime has a score key (even if 0)
        for r in RegimeLabel:
            scores.setdefault(r, 0.0)

        candidate = max(scores, key=scores.get)
        current = self.state.current

        confidence = self._confidence_score(votes=votes, feats=feats, now=now, chosen=candidate)
        transition_zone = False

        eng = self.cfg["engine"]
        confirm_periods = int(eng["confirm_periods"])
        min_duration_seconds = float(eng["min_duration_seconds"])
        enter_conf = float(eng["enter_confidence"])
        hysteresis_delta = float(eng["hysteresis_delta"])

        # Hysteresis: candidate must beat current by delta (if current != candidate)
        margin_ok = True
        if candidate != current:
            margin_ok = (scores[candidate] - scores[current]) >= hysteresis_delta

        # Minimum duration: can't switch too fast after last switch
        min_duration_ok = (now - self.state.since_ts) >= min_duration_seconds

        # Transition handling
        if candidate == current:
            # reset candidate tracking
            self.state.candidate = None
            self.state.candidate_streak = 0
        else:
            transition_zone = True
            can_start = (confidence >= enter_conf) and margin_ok
            if not can_start:
                # not enough evidence: reset streak
                self.state.candidate = candidate
                self.state.candidate_streak = 0
            else:
                if self.state.candidate != candidate:
                    self.state.candidate = candidate
                    self.state.candidate_streak = 1
                else:
                    self.state.candidate_streak += 1

                # Confirmed switch?
                if self.state.candidate_streak >= confirm_periods and min_duration_ok:
                    self._switch_to(candidate, now)
                    current = self.state.current
                    transition_zone = False  # switch completed

        controls = self._controls_for(current, confidence, transition_zone)

        return RegimeOutput(
            label=current,
            confidence=confidence,
            transition_zone=transition_zone,
            candidate_label=self.state.candidate if transition_zone else None,
            scores=scores,
            votes=votes,
            controls=controls,
            ts=now,
        )

    # ----------------------------
    # Votes
    # ----------------------------
    def _compute_votes(self, f: RegimeFeatures) -> Dict[str, Optional[RegimeLabel]]:
        th = self.cfg["thresholds"]
        out: Dict[str, Optional[RegimeLabel]] = {}

        # 1) RV vs IV divergence
        z = f.rv_iv_z
        if z is None:
            out["rv_iv_divergence"] = None
        else:
            if z >= float(th["rv_iv_z"]["high"]):
                out["rv_iv_divergence"] = RegimeLabel.VOLATILITY_EXPANSION
            elif z <= float(th["rv_iv_z"]["low"]):
                out["rv_iv_divergence"] = RegimeLabel.VOLATILITY_COMPRESSION
            else:
                out["rv_iv_divergence"] = None

        # 2) Trend persistence
        align = f.trend_alignment
        persist = f.trend_persistence
        if align is None or persist is None:
            out["trend_persistence"] = None
        else:
            t = th["trend"]
            if align >= int(t["alignment_expansion"]) and persist > float(t["persistence_expansion"]):
                out["trend_persistence"] = RegimeLabel.DIRECTIONAL_EXPANSION
            elif align >= int(t["alignment_compression"]) and persist > float(t["persistence_compression"]):
                out["trend_persistence"] = RegimeLabel.DIRECTIONAL_COMPRESSION
            else:
                out["trend_persistence"] = None

        # 3) Range expansion / compression
        rr = f.range_expansion_ratio
        rp = f.range_percentile
        if rr is None and rp is None:
            out["range_expansion"] = None
        else:
            rth = th["range"]
            expanding = (rr is not None and rr >= float(rth["expansion_ratio_hi"])) or \
                        (rp is not None and rp >= float(rth["range_pct_hi"]))
            compressing = (rr is not None and rr <= float(rth["compression_ratio_lo"])) or \
                          (rp is not None and rp <= float(rth["range_pct_lo"]))

            # If direction is ambiguous, treat expansion/compression as volatility regimes
            ambiguous = False
            if f.trend_alignment is not None:
                ambiguous = abs(int(f.trend_alignment)) <= int(th["trend"]["alignment_ambiguous_max_abs"])

            if expanding:
                out["range_expansion"] = RegimeLabel.VOLATILITY_EXPANSION if ambiguous else RegimeLabel.DIRECTIONAL_EXPANSION
            elif compressing:
                out["range_expansion"] = RegimeLabel.VOLATILITY_COMPRESSION if ambiguous else RegimeLabel.DIRECTIONAL_COMPRESSION
            else:
                out["range_expansion"] = None

        # 4) Liquidity
        spread = f.spread_bps
        depth = f.depth_usd
        if spread is None and depth is None:
            out["liquidity"] = None
        else:
            lth = th["liquidity"]
            spread_bad = (spread is not None and spread > float(lth["spread_bps_max"]))
            depth_bad = (depth is not None and depth < float(lth["depth_usd_min"]))
            out["liquidity"] = RegimeLabel.LIQUIDITY_VACUUM if (spread_bad or depth_bad) else None

        # 5) Event
        out["event"] = RegimeLabel.EVENT_DOMINATED if (f.event_risk_flag or f.shock_flag) else None

        # 6) Cross asset (optional)
        out["cross_asset"] = RegimeLabel.EVENT_DOMINATED if f.cross_asset_risk_flag else None

        return out

    def _aggregate_scores(self, votes: Dict[str, Optional[RegimeLabel]], feats: RegimeFeatures) -> Dict[RegimeLabel, float]:
        # Weighted vote count + small strength shaping when available
        w = self.cfg["votes"]["weights"]
        scores: Dict[RegimeLabel, float] = {}

        def add(reg: RegimeLabel, amount: float):
            scores[reg] = scores.get(reg, 0.0) + amount

        for k, reg in votes.items():
            if reg is None:
                continue
            base = float(w.get(k, 1.0))
            # Strength hints (optional)
            strength = 1.0
            if k == "rv_iv_divergence" and feats.rv_iv_z is not None:
                strength = min(2.0, max(0.5, abs(feats.rv_iv_z) / 2.0))
            if k == "liquidity":
                strength = 1.5
            if k == "event":
                strength = 1.5
            add(reg, base * strength)

        return scores

    # ----------------------------
    # Confidence
    # ----------------------------
    def _confidence_score(self, votes: Dict[str, Optional[RegimeLabel]], feats: RegimeFeatures, now: float, chosen: RegimeLabel) -> float:
        # Agreement %
        active_votes = [v for v in votes.values() if v is not None]
        if not active_votes:
            agreement = 0.0
        else:
            agreement = 100.0 * (sum(1 for v in active_votes if v == chosen) / len(active_votes))

        # Duration factor (new regime = low confidence)
        secs_in_regime = now - self.state.since_ts
        # Convert seconds into “period-ish” buckets; you can refine later
        periods = secs_in_regime / 60.0  # 1 period ~= 1 minute (placeholder)
        if periods < 10:
            duration_factor = 50.0
        elif periods < 30:
            duration_factor = 75.0
        else:
            duration_factor = 100.0

        # Signal clarity: how far beyond thresholds are we?
        clarity = self._signal_clarity(feats)

        # Stability factor: penalize frequent switching
        # (simple version: decay with switch_count_window)
        stability = max(0.0, 100.0 - 10.0 * float(self.state.switch_count_window))

        # Weighted blend (Strategy recipe)
        conf = (
            agreement * 0.40 +
            duration_factor * 0.25 +
            clarity * 0.20 +
            stability * 0.15
        )
        return float(max(0.0, min(100.0, conf)))

    def _signal_clarity(self, f: RegimeFeatures) -> float:
        th = self.cfg["thresholds"]
        distances = []

        # rv_iv_z clarity
        if f.rv_iv_z is not None:
            hi = float(th["rv_iv_z"]["high"])
            lo = float(th["rv_iv_z"]["low"])
            if f.rv_iv_z >= hi:
                distances.append((f.rv_iv_z - hi) / max(hi, 1e-9))
            elif f.rv_iv_z <= lo:
                distances.append((lo - f.rv_iv_z) / max(abs(lo), 1e-9))

        # trend clarity
        if f.trend_alignment is not None and f.trend_persistence is not None:
            t = th["trend"]
            a = float(f.trend_alignment)
            p = float(f.trend_persistence)
            distances.append(max(0.0, (a - float(t["alignment_compression"])) / max(float(t["alignment_compression"]), 1e-9)))
            distances.append(max(0.0, (p - float(t["persistence_compression"])) / max(float(t["persistence_compression"]), 1e-9)))

        # range clarity
        if f.range_expansion_ratio is not None:
            rth = th["range"]
            rr = float(f.range_expansion_ratio)
            distances.append(max(0.0, (rr - float(rth["expansion_ratio_hi"])) / max(float(rth["expansion_ratio_hi"]), 1e-9)))
            distances.append(max(0.0, (float(rth["compression_ratio_lo"]) - rr) / max(float(rth["compression_ratio_lo"]), 1e-9)))

        if not distances:
            return 50.0  # neutral
        avg = sum(distances) / len(distances)
        return float(max(0.0, min(100.0, avg * 100.0)))

    # ----------------------------
    # Controls (what downstream uses)
    # ----------------------------
    def _controls_for(self, regime: RegimeLabel, confidence: float, transition_zone: bool) -> Dict[str, Any]:
        ctrl = self.cfg["controls"]
        mask = ctrl["strategy_mask"].get(regime.value, {})

        exec_mode = ctrl.get("execution_mode", {})
        mode = exec_mode.get(regime.value, exec_mode.get("default", "NORMAL"))

        # Simple strength gating example:
        # - low confidence => downscale everything
        if confidence < 50:
            mask = {k: float(v) * 0.5 for k, v in mask.items()}

        return {
            "strategy_mask": mask,              # Gate 39
            "execution_mode": mode,             # passive/aggressive posture hint
            "transition_zone": transition_zone  # Gate 42 usage
        }

    def _switch_to(self, new_regime: RegimeLabel, now: float) -> None:
        self.state.current = new_regime
        self.state.since_ts = now
        self.state.last_switch_ts = now
        self.state.switch_count_window += 1
        self.state.candidate = None
        self.state.candidate_streak = 0
