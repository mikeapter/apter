from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _upper(x: Any, default: str = "") -> str:
    if x is None:
        return default
    return str(x).upper().strip()


def _mid(bid: Optional[float], ask: Optional[float]) -> Optional[float]:
    if bid is None or ask is None:
        return None
    return (float(bid) + float(ask)) / 2.0


def _side_sign(side: str) -> int:
    s = _upper(side, "BUY")
    return +1 if s in ("BUY", "B", "LONG") else -1


@dataclass
class AdverseSelectionDecision:
    allow_passive: bool
    force_aggressive_only: bool
    force_ioc: bool
    block_new_entries: bool
    score: float
    action: str  # CONTINUE / AGGRESSIVE_ONLY / PAUSE_PASSIVE / BLOCK
    reason: str
    until_ts: Optional[float] = None
    random_tick_offset: int = 0


@dataclass
class AdverseSelectionResult:
    detected: bool
    score: float
    action: str
    reason: str
    fill_speed_s: float
    post_fill_adverse_move_bps: float
    fast_fill_rate_pct: float
    adverse_rate_pct: float
    latency_flag_score: float


class AdverseSelectionMonitor:
    """
    STEP 16 — Adverse selection detection + mitigation

    Uses Strategy concepts:
      - Fast fill on limit order (e.g. < 0.5s) = suspicious
      - Post-fill price move against you within ~5s
      - Stale quote / latency flag

    Maintains a rolling window of recent fills to compute:
      - fast_fill_rate_pct
      - adverse_rate_pct

    Emits actions:
      - CONTINUE
      - AGGRESSIVE_ONLY (no passive posting; prefer IOC/controlled marketable limits)
      - PAUSE_PASSIVE (cooldown N minutes)
      - BLOCK (optional: if you want to hard-block new entries during severe toxicity)
    """

    def __init__(
        self,
        config_path: Union[str, Path],
        state_path: Union[str, Path],
        events_path: Union[str, Path],
    ):
        self.config_path = Path(config_path)
        self.state_path = Path(state_path)
        self.events_path = Path(events_path)
        self.cfg = self._load_yaml(self.config_path)
        self._state = self._load_state()

    # ---------------- config/state ----------------

    def _load_yaml(self, p: Path) -> Dict[str, Any]:
        if not p.exists():
            raise FileNotFoundError(f"AdverseSelection config missing: {p}")
        # lightweight yaml parse without dependency (repo already uses yaml elsewhere,
        # but keeping this file standalone-friendly)
        import yaml  # type: ignore
        with open(p, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "passive_paused_until_ts": 0.0,
            "aggressive_only_until_ts": 0.0,
            "block_entries_until_ts": 0.0,
            "last_score": 0.0,
            "last_action": "CONTINUE",
            "last_reason": "",
            "recent": [],  # rolling list of fill observations
        }

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")

    def _append_event(self, event: Dict[str, Any]) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    def _now(self) -> float:
        return time.time()

    # ---------------- timers / modes ----------------

    def passive_paused(self, now: Optional[float] = None) -> bool:
        t = self._now() if now is None else float(now)
        return t < float(self._state.get("passive_paused_until_ts", 0.0))

    def aggressive_only(self, now: Optional[float] = None) -> bool:
        t = self._now() if now is None else float(now)
        # passive pause implies aggressive-only (safer behavior)
        if self.passive_paused(t):
            return True
        return t < float(self._state.get("aggressive_only_until_ts", 0.0))

    def block_entries(self, now: Optional[float] = None) -> bool:
        t = self._now() if now is None else float(now)
        return t < float(self._state.get("block_entries_until_ts", 0.0))

    # ---------------- scoring helpers ----------------

    def _prune_recent(self) -> None:
        max_n = _safe_int(self.cfg.get("rolling_window_fills", 50), 50)
        recent = list(self._state.get("recent", []))
        if len(recent) > max_n:
            recent = recent[-max_n:]
        self._state["recent"] = recent

    def _rates(self) -> Dict[str, float]:
        self._prune_recent()
        recent = list(self._state.get("recent", []))
        if not recent:
            return {"fast_fill_rate_pct": 0.0, "adverse_rate_pct": 0.0}

        fast_thr = _safe_float(self.cfg.get("fast_fill_seconds", 0.5), 0.5)
        adv_thr = _safe_float(self.cfg.get("adverse_move_threshold_bps", 5.0), 5.0)

        fast = 0
        adverse = 0
        for r in recent:
            fs = _safe_float(r.get("fill_speed_s", 999.0), 999.0)
            move_bps = _safe_float(r.get("post_fill_adverse_move_bps", 0.0), 0.0)
            if fs < fast_thr:
                fast += 1
            # NOTE: move_bps is direction-adjusted (negative = against you)
            if move_bps < -adv_thr:
                adverse += 1

        n = max(1, len(recent))
        return {
            "fast_fill_rate_pct": 100.0 * fast / n,
            "adverse_rate_pct": 100.0 * adverse / n,
        }

    def _latency_flag_score(self, latency_ms: Optional[float]) -> float:
        if latency_ms is None:
            return 0.0
        thr = _safe_float(self.cfg.get("latency_ms_threshold", 50.0), 50.0)
        lat = float(latency_ms)
        # scale: 0 at 0ms, 100 at >= threshold*2
        return _clamp((lat / max(1e-9, (thr * 2.0))) * 100.0, 0.0, 100.0)

    def _compute_score(
        self,
        *,
        fast_fill_rate_pct: float,
        adverse_rate_pct: float,
        latency_flag_score: float,
        p_adverse_selection: Optional[float] = None,
        toxicity: Optional[float] = None,
    ) -> float:
        # Strategy weighted sum:
        # 0.3 fast fills + 0.4 post-fill adverse + 0.3 latency flag
        score = (
            0.30 * float(fast_fill_rate_pct)
            + 0.40 * float(adverse_rate_pct)
            + 0.30 * float(latency_flag_score)
        )

        # IPS-style probability gate: if P(AdverseSelection) > 0.55 => treat as elevated.
        if p_adverse_selection is not None:
            p_thr = _safe_float(self.cfg.get("p_adverse_selection_threshold", 0.55), 0.55)
            if float(p_adverse_selection) > p_thr:
                score += _safe_float(self.cfg.get("p_adverse_selection_score_add", 15.0), 15.0)

        # Optional toxicity gate: if toxicity above threshold, boost score.
        if toxicity is not None:
            tox_thr = _safe_float(self.cfg.get("toxicity_threshold", 0.70), 0.70)
            if float(toxicity) >= tox_thr:
                score += _safe_float(self.cfg.get("toxicity_score_add", 20.0), 20.0)

        return _clamp(score, 0.0, 100.0)

    # ---------------- public API ----------------

    def pre_trade(self, symbol: str, side: str, quote: Dict[str, Any], meta: Optional[Dict[str, Any]] = None) -> AdverseSelectionDecision:
        """
        Called BEFORE placing an order.
        Uses state + (optional) live microstructure inputs from meta.
        """
        meta = meta or {}
        now = self._now()

        # If entries are blocked (optional severe mode)
        if self.block_entries(now):
            until = float(self._state.get("block_entries_until_ts", 0.0))
            return AdverseSelectionDecision(
                allow_passive=False,
                force_aggressive_only=True,
                force_ioc=True,
                block_new_entries=True,
                score=float(self._state.get("last_score", 0.0)),
                action="BLOCK",
                reason=str(self._state.get("last_reason", "BLOCK_ENTRIES_ACTIVE")),
                until_ts=until,
                random_tick_offset=0,
            )

        # If passive is paused (cooldown)
        if self.passive_paused(now):
            until = float(self._state.get("passive_paused_until_ts", 0.0))
            return AdverseSelectionDecision(
                allow_passive=False,
                force_aggressive_only=True,
                force_ioc=True,
                block_new_entries=False,
                score=float(self._state.get("last_score", 0.0)),
                action="PAUSE_PASSIVE",
                reason=str(self._state.get("last_reason", "PASSIVE_PAUSED_ACTIVE")),
                until_ts=until,
                random_tick_offset=0,
            )

        # If aggressive-only is active (but passive pause is not)
        if self.aggressive_only(now):
            until = float(self._state.get("aggressive_only_until_ts", 0.0))
            return AdverseSelectionDecision(
                allow_passive=False,
                force_aggressive_only=True,
                force_ioc=bool(self.cfg.get("aggressive_only_force_ioc", True)),
                block_new_entries=False,
                score=float(self._state.get("last_score", 0.0)),
                action="AGGRESSIVE_ONLY",
                reason=str(self._state.get("last_reason", "AGGRESSIVE_ONLY_ACTIVE")),
                until_ts=until,
                random_tick_offset=0,
            )

        # Freshness/latency defenses (stale quote / latency arbitrage victim risk)
        latency_ms = meta.get("latency_ms")
        quote_age_ms = meta.get("quote_age_ms")
        lat_thr = _safe_float(self.cfg.get("latency_ms_threshold", 50.0), 50.0)
        quote_age_thr = _safe_float(self.cfg.get("quote_age_ms_threshold", 250.0), 250.0)

        if latency_ms is not None and float(latency_ms) > lat_thr:
            # Safe execution mode: pull passive quotes, IOC-only.
            return AdverseSelectionDecision(
                allow_passive=False,
                force_aggressive_only=True,
                force_ioc=True,
                block_new_entries=False,
                score=80.0,
                action="AGGRESSIVE_ONLY",
                reason=f"LATENCY_HIGH latency_ms={float(latency_ms):.1f} > {lat_thr:.1f}",
                until_ts=None,
                random_tick_offset=0,
            )

        if quote_age_ms is not None and float(quote_age_ms) > quote_age_thr:
            return AdverseSelectionDecision(
                allow_passive=False,
                force_aggressive_only=True,
                force_ioc=True,
                block_new_entries=False,
                score=75.0,
                action="AGGRESSIVE_ONLY",
                reason=f"STALE_QUOTE quote_age_ms={float(quote_age_ms):.1f} > {quote_age_thr:.1f}",
                until_ts=None,
                random_tick_offset=0,
            )

        # Optional IPS signals
        p_adv = meta.get("p_adverse_selection")
        toxicity = meta.get("toxicity")

        # Convert optional probability/toxicity into a pre-trade score bump.
        rates = self._rates()
        latency_score = self._latency_flag_score(latency_ms if latency_ms is not None else None)
        score = self._compute_score(
            fast_fill_rate_pct=rates["fast_fill_rate_pct"],
            adverse_rate_pct=rates["adverse_rate_pct"],
            latency_flag_score=latency_score,
            p_adverse_selection=float(p_adv) if p_adv is not None else None,
            toxicity=float(toxicity) if toxicity is not None else None,
        )

        # Decide action by score
        warn_thr = _safe_float(self.cfg.get("warn_threshold", 35.0), 35.0)
        aggr_thr = _safe_float(self.cfg.get("aggressive_only_threshold", 50.0), 50.0)
        pause_thr = _safe_float(self.cfg.get("pause_passive_threshold", 70.0), 70.0)

        action = "CONTINUE"
        allow_passive = True
        force_aggr = False
        force_ioc = False
        reason = "score_ok"

        if score >= pause_thr:
            action = "PAUSE_PASSIVE"
            allow_passive = False
            force_aggr = True
            force_ioc = True
            reason = f"score={score:.1f} >= pause_thr({pause_thr:.1f})"
        elif score >= aggr_thr:
            action = "AGGRESSIVE_ONLY"
            allow_passive = False
            force_aggr = True
            force_ioc = bool(self.cfg.get("aggressive_only_force_ioc", True))
            reason = f"score={score:.1f} >= aggr_thr({aggr_thr:.1f})"
        elif score >= warn_thr:
            action = "CONTINUE"
            allow_passive = True
            force_aggr = False
            force_ioc = False
            reason = f"score={score:.1f} >= warn_thr({warn_thr:.1f})"

        # Random tick offset (avoid “obvious” levels) — only if enabled AND we’re posting passively.
        tick_offset = 0
        if allow_passive and bool(self.cfg.get("random_tick_offset_enabled", True)):
            mn = _safe_int(self.cfg.get("random_tick_offset_min", 1), 1)
            mx = _safe_int(self.cfg.get("random_tick_offset_max", 3), 3)
            if mx >= mn and mn > 0:
                tick_offset = random.randint(mn, mx)

        return AdverseSelectionDecision(
            allow_passive=allow_passive,
            force_aggressive_only=force_aggr,
            force_ioc=force_ioc,
            block_new_entries=False,
            score=float(score),
            action=action,
            reason=reason,
            until_ts=None,
            random_tick_offset=tick_offset,
        )

    def record_fill(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        submit_ts: float,
        fill_ts: float,
        fill_price: float,
        post_fill_mid: Optional[float],
        latency_ms: Optional[float] = None,
        p_adverse_selection: Optional[float] = None,
        toxicity: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> AdverseSelectionResult:
        """
        Called AFTER a fill.
        Computes:
          - fill_speed_s
          - post_fill_adverse_move_bps (direction-adjusted; negative = against you)
          - rolling rates
          - score and potential mitigations
        """
        now = self._now()
        side_u = _upper(side, "BUY")
        sign = _side_sign(side_u)

        fill_speed_s = max(0.0, float(fill_ts) - float(submit_ts))

        post_mid = None if post_fill_mid is None else float(post_fill_mid)
        fill_px = float(fill_price)

        # Direction-adjusted move: negative means price moved against you.
        post_fill_adverse_move_bps = 0.0
        if post_mid is not None and fill_px > 0:
            post_fill_adverse_move_bps = sign * ((post_mid - fill_px) / fill_px) * 10000.0

        # Add observation
        obs = {
            "ts": now,
            "symbol": str(symbol).upper().strip(),
            "side": side_u,
            "order_type": str(order_type).upper().strip(),
            "fill_speed_s": float(fill_speed_s),
            "post_fill_adverse_move_bps": float(post_fill_adverse_move_bps),
            "latency_ms": float(latency_ms) if latency_ms is not None else None,
        }
        recent = list(self._state.get("recent", []))
        recent.append(obs)
        self._state["recent"] = recent
        self._prune_recent()

        rates = self._rates()
        latency_score = self._latency_flag_score(latency_ms)

        score = self._compute_score(
            fast_fill_rate_pct=rates["fast_fill_rate_pct"],
            adverse_rate_pct=rates["adverse_rate_pct"],
            latency_flag_score=latency_score,
            p_adverse_selection=float(p_adverse_selection) if p_adverse_selection is not None else None,
            toxicity=float(toxicity) if toxicity is not None else None,
        )

        warn_thr = _safe_float(self.cfg.get("warn_threshold", 35.0), 35.0)
        aggr_thr = _safe_float(self.cfg.get("aggressive_only_threshold", 50.0), 50.0)
        pause_thr = _safe_float(self.cfg.get("pause_passive_threshold", 70.0), 70.0)

        action = "CONTINUE"
        reason = "score_ok"
        detected = False

        adv_thr = _safe_float(self.cfg.get("adverse_move_threshold_bps", 5.0), 5.0)
        fast_thr = _safe_float(self.cfg.get("fast_fill_seconds", 0.5), 0.5)

        # "Detected" if we see classic patterns
        if fill_speed_s < fast_thr and post_fill_adverse_move_bps < -adv_thr:
            detected = True

        # Trigger mitigations
        if score >= pause_thr:
            detected = True
            pause_minutes = _safe_float(self.cfg.get("pause_passive_minutes", 5.0), 5.0)
            until = now + pause_minutes * 60.0
            self._state["passive_paused_until_ts"] = float(until)
            # aggressive-only also active (safe mode behavior)
            self._state["aggressive_only_until_ts"] = float(until)
            action = "PAUSE_PASSIVE"
            reason = f"score={score:.1f} >= pause_thr({pause_thr:.1f}) => pause_passive {pause_minutes:.1f}m"
        elif score >= aggr_thr:
            detected = True
            aggr_minutes = _safe_float(self.cfg.get("aggressive_only_minutes", 3.0), 3.0)
            until = now + aggr_minutes * 60.0
            self._state["aggressive_only_until_ts"] = float(until)
            action = "AGGRESSIVE_ONLY"
            reason = f"score={score:.1f} >= aggr_thr({aggr_thr:.1f}) => aggressive_only {aggr_minutes:.1f}m"
        elif score >= warn_thr:
            action = "CONTINUE"
            reason = f"score={score:.1f} >= warn_thr({warn_thr:.1f}) => caution"

        # Persist last decision
        self._state["last_score"] = float(score)
        self._state["last_action"] = str(action)
        self._state["last_reason"] = str(reason)

        # Append event log
        event = {
            "ts": now,
            "symbol": str(symbol).upper().strip(),
            "side": side_u,
            "order_type": str(order_type).upper().strip(),
            "submit_ts": float(submit_ts),
            "fill_ts": float(fill_ts),
            "fill_speed_s": float(fill_speed_s),
            "fill_price": float(fill_px),
            "post_fill_mid": float(post_mid) if post_mid is not None else None,
            "post_fill_adverse_move_bps": float(post_fill_adverse_move_bps),
            "fast_fill_rate_pct": float(rates["fast_fill_rate_pct"]),
            "adverse_rate_pct": float(rates["adverse_rate_pct"]),
            "latency_flag_score": float(latency_score),
            "score": float(score),
            "detected": bool(detected),
            "action": str(action),
            "reason": str(reason),
            "extra": extra or {},
        }
        self._append_event(event)
        self._save_state()

        return AdverseSelectionResult(
            detected=bool(detected),
            score=float(score),
            action=str(action),
            reason=str(reason),
            fill_speed_s=float(fill_speed_s),
            post_fill_adverse_move_bps=float(post_fill_adverse_move_bps),
            fast_fill_rate_pct=float(rates["fast_fill_rate_pct"]),
            adverse_rate_pct=float(rates["adverse_rate_pct"]),
            latency_flag_score=float(latency_score),
        )


# Backwards-compatible alias
AdverseSelectionModule = AdverseSelectionMonitor
