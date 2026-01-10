from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


def _safe_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _safe_bool(x: Any, default: bool = False) -> bool:
    try:
        if x is None:
            return default
        if isinstance(x, bool):
            return x
        s = str(x).strip().lower()
        return s in ("1", "true", "yes", "y", "on")
    except Exception:
        return default


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _spread_bps(quote: Dict[str, Any]) -> Optional[float]:
    b = _safe_float(quote.get("bid"))
    a = _safe_float(quote.get("ask"))
    if b is None or a is None or b <= 0 or a <= 0:
        return None
    mid = (b + a) / 2.0
    if mid <= 0:
        return None
    return (a - b) / mid * 10000.0


@dataclass(frozen=True)
class SafeModeDecision:
    active: bool
    level: str
    score: int
    reasons: List[str]

    size_multiplier: float
    cooldown_multiplier: float
    max_trades_multiplier: float

    disable_passive: bool
    force_ioc: bool
    force_direct: bool
    cancel_resting: bool
    avoid_dark_pools: bool
    block_new_entries: bool
    require_exit_flag_for_orders: bool

    until_ts: Optional[float] = None  # informational


class ExecutionSafeModeMonitor:
    """
    STEP 17 — Execution Safe Mode
    - Triggers: spread widen / depth collapse / vol shock / event windows / latency & rejects / halts
    - Disables: passive posting (limit-making), dark pools, algos (if desired), resting orders
    - Tightens: size, cooldown, max trades, routing/venue and TIF (IOC)
    - Higher levels: block new entries, exits-only mode

    IMPORTANT CHANGE:
      - force_safe_mode_level bypasses hysteresis and immediately sets level.

    STEP 21 ADDITIONS:
      - Watchdog/degradation can force safe mode via state file fields:
          forced_level, forced_reason, forced_ts
      - Persisting state preserves forced_* keys.
    """

    def __init__(
        self,
        *,
        config_path: Union[str, Path],
        state_path: Union[str, Path],
        events_path: Optional[Union[str, Path]] = None,
        logger: Any = None,
    ) -> None:
        self.config_path = Path(config_path)
        self.state_path = Path(state_path)
        self.events_path = Path(events_path) if events_path is not None else None
        self.log = logger

        self.cfg = self._load_config(self.config_path)

        # persistent state
        self._level: str = "NORMAL"
        self._since_ts: float = time.time()
        self._last_level_change_ts: float = self._since_ts

        # hysteresis helper
        self._stable_since_ts: Optional[float] = None

        self._load_state()

    # ---------------- config/state ----------------
    def _load_config(self, path: Path) -> Dict[str, Any]:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError("execution_safe_mode.yaml must be a dict")
        data.setdefault("version", 1)
        data.setdefault("thresholds", {})
        data.setdefault("weights", {})
        data.setdefault("actions", {})
        data.setdefault("hysteresis", {})
        data.setdefault("score_to_level", {})
        return data

    def _read_state_raw(self) -> Dict[str, Any]:
        try:
            if self.state_path.exists():
                raw = json.loads(self.state_path.read_text(encoding="utf-8") or "{}")
                if isinstance(raw, dict):
                    return raw
        except Exception:
            pass
        return {}

    def _persist_state(self) -> None:
        """
        STEP 21: Preserve watchdog override keys (forced_level/forced_reason/forced_ts)
        instead of wiping them out.
        """
        existing = self._read_state_raw()

        payload: Dict[str, Any] = {
            "level": self._level,
            "since_ts": float(self._since_ts),
            "last_level_change_ts": float(self._last_level_change_ts),
        }

        # preserve external override fields if present
        for k in ("forced_level", "forced_reason", "forced_ts"):
            if k in existing:
                payload[k] = existing.get(k)

        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.state_path)

    def _load_state(self) -> None:
        if not self.state_path.exists():
            self._persist_state()
            return
        raw = self._read_state_raw()
        self._level = str(raw.get("level") or "NORMAL").upper()
        self._since_ts = float(raw.get("since_ts") or time.time())
        self._last_level_change_ts = float(raw.get("last_level_change_ts") or self._since_ts)

    def _emit_event(self, event: Dict[str, Any]) -> None:
        if self.events_path is None:
            return
        try:
            self.events_path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(event, sort_keys=True)
            with self.events_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    # ---------------- public API ----------------
    def current_level(self) -> str:
        return self._level

    def pre_trade(
        self,
        *,
        symbol: str,
        side: str,
        qty: int,
        quote: Dict[str, Any],
        meta: Dict[str, Any],
        now_ts: Optional[float] = None,
    ) -> SafeModeDecision:
        now = float(now_ts or time.time())
        meta = meta or {}

        # ----------------------------------------------------
        # STEP 21: STATE-FILE OVERRIDE (watchdog/degradation)
        # If meta did not provide an override, read forced_level from state file
        # and inject it into meta so the existing FORCE OVERRIDE logic triggers.
        # ----------------------------------------------------
        if not str(meta.get("force_safe_mode_level") or "").strip():
            st = self._read_state_raw()
            forced_state = str(st.get("forced_level") or "").strip().upper()
            if forced_state:
                meta["force_safe_mode_level"] = forced_state
                if st.get("forced_reason"):
                    meta["_forced_safe_mode_reason"] = str(st.get("forced_reason"))

        # ----------------------------------------------------
        # FORCE OVERRIDE (IMPORTANT CHANGE)
        # - bypass hysteresis and immediately set level
        # ----------------------------------------------------
        forced = str(meta.get("force_safe_mode_level") or "").strip().upper()
        if forced in ("NORMAL", "PRE_ALERT", "ALERT", "HIGH_ALERT", "CRITICAL"):
            prev = self._level
            self._level = forced
            self._since_ts = now
            self._last_level_change_ts = now
            self._stable_since_ts = None
            self._persist_state()

            reasons = [f"forced_level={forced}"]
            if meta.get("_forced_safe_mode_reason"):
                reasons.insert(0, f"forced_reason={meta.get('_forced_safe_mode_reason')}")

            self._emit_event(
                {
                    "ts": now,
                    "type": "SAFE_MODE_LEVEL_CHANGE",
                    "symbol": str(symbol).upper(),
                    "side": str(side).upper(),
                    "prev_level": prev,
                    "new_level": forced,
                    "score": 999,
                    "reasons": reasons,
                }
            )

            d = self._decision_for_level(level=self._level, score=999, reasons=reasons)
            if self.log is not None:
                try:
                    self.log.info(
                        "ExecutionSafeMode forced override",
                        extra={"symbol": str(symbol).upper(), "side": str(side).upper(), "level": d.level},
                    )
                except Exception:
                    pass
            return d

        # Compute level normally
        computed_level, score, reasons = self._compute_level(quote=quote, meta=meta)

        # Apply hysteresis (promote immediately, downgrade only after stable window)
        new_level = self._apply_hysteresis(computed_level=computed_level, now=now)

        if new_level != self._level:
            prev = self._level
            self._level = new_level
            self._since_ts = now
            self._last_level_change_ts = now
            self._stable_since_ts = None
            self._persist_state()
            self._emit_event(
                {
                    "ts": now,
                    "type": "SAFE_MODE_LEVEL_CHANGE",
                    "symbol": str(symbol).upper(),
                    "side": str(side).upper(),
                    "prev_level": prev,
                    "new_level": new_level,
                    "score": int(score),
                    "reasons": reasons,
                }
            )

        d = self._decision_for_level(level=self._level, score=score, reasons=reasons)

        if self.log is not None:
            try:
                self.log.info(
                    "ExecutionSafeMode pre-trade",
                    extra={
                        "symbol": str(symbol).upper(),
                        "side": str(side).upper(),
                        "level": d.level,
                        "score": d.score,
                        "reasons": d.reasons,
                        "size_multiplier": d.size_multiplier,
                        "cooldown_multiplier": d.cooldown_multiplier,
                        "max_trades_multiplier": d.max_trades_multiplier,
                        "disable_passive": d.disable_passive,
                        "force_ioc": d.force_ioc,
                        "force_direct": d.force_direct,
                        "cancel_resting": d.cancel_resting,
                        "avoid_dark_pools": d.avoid_dark_pools,
                        "block_new_entries": d.block_new_entries,
                    },
                )
            except Exception:
                pass

        return d

    # ---------------- internals ----------------
    def _compute_level(self, *, quote: Dict[str, Any], meta: Dict[str, Any]) -> tuple[str, int, List[str]]:
        thr = self.cfg.get("thresholds", {}) or {}
        weights = self.cfg.get("weights", {}) or {}

        sbps = _safe_float(meta.get("spread_bps"))
        if sbps is None:
            sbps = _spread_bps(quote)

        depth_ratio = _safe_float(meta.get("depth_ratio"))  # 1.0 normal, 0.3 depth collapse
        vol_z = _safe_float(meta.get("vol_z"))
        latency_ms = _safe_float(meta.get("latency_ms"))
        reject_rate = _safe_float(meta.get("reject_rate"))

        is_event_window = _safe_bool(meta.get("is_event_window"), False)
        is_halted = _safe_bool(meta.get("halted"), False) or _safe_bool(meta.get("circuit_breaker"), False)

        reasons: List[str] = []
        score = 0

        # Hard fail: halts/circuit breakers -> CRITICAL immediately
        if is_halted:
            reasons.append("halted_or_circuit_breaker")
            return "CRITICAL", 999, reasons

        # Latency outage -> CRITICAL
        lat_thr = (thr.get("latency_ms", {}) or {})
        if latency_ms is not None:
            outage = _safe_float(lat_thr.get("outage"), 1000.0) or 1000.0
            alert = _safe_float(lat_thr.get("alert"), 150.0) or 150.0
            if latency_ms >= outage:
                reasons.append(f"latency_outage_ms={latency_ms:.0f}")
                return "CRITICAL", 999, reasons
            if latency_ms >= alert:
                score += 1
                reasons.append(f"latency_alert_ms={latency_ms:.0f}")

        # Spread score
        sthr = (thr.get("spread_bps", {}) or {})
        if sbps is not None:
            pre = _safe_float(sthr.get("pre_alert"), 8.0) or 8.0
            al = _safe_float(sthr.get("alert"), 15.0) or 15.0
            hi = _safe_float(sthr.get("high_alert"), 25.0) or 25.0
            if sbps >= hi:
                score += 3
                reasons.append(f"spread_high_bps={sbps:.1f}")
            elif sbps >= al:
                score += 2
                reasons.append(f"spread_alert_bps={sbps:.1f}")
            elif sbps >= pre:
                score += 1
                reasons.append(f"spread_pre_bps={sbps:.1f}")

        # Depth collapse score
        dthr = (thr.get("depth_ratio", {}) or {})
        if depth_ratio is not None:
            pre = _safe_float(dthr.get("pre_alert"), 0.60) or 0.60
            al = _safe_float(dthr.get("alert"), 0.40) or 0.40
            hi = _safe_float(dthr.get("high_alert"), 0.25) or 0.25
            if depth_ratio <= hi:
                score += 3
                reasons.append(f"depth_collapse_high={depth_ratio:.2f}")
            elif depth_ratio <= al:
                score += 2
                reasons.append(f"depth_collapse_alert={depth_ratio:.2f}")
            elif depth_ratio <= pre:
                score += 1
                reasons.append(f"depth_collapse_pre={depth_ratio:.2f}")

        # Liquidity vacuum combo boost (wide spread + low depth)
        if sbps is not None and depth_ratio is not None:
            al = _safe_float((thr.get("spread_bps", {}) or {}).get("alert"), 15.0) or 15.0
            dal = _safe_float((thr.get("depth_ratio", {}) or {}).get("alert"), 0.40) or 0.40
            if sbps >= al and depth_ratio <= dal:
                score += 2
                reasons.append("liquidity_vacuum_combo")

        # Vol shock score
        vthr = (thr.get("vol_z", {}) or {})
        if vol_z is not None:
            pre = _safe_float(vthr.get("pre_alert"), 2.0) or 2.0
            al = _safe_float(vthr.get("alert"), 3.0) or 3.0
            hi = _safe_float(vthr.get("high_alert"), 4.0) or 4.0
            if vol_z >= hi:
                score += 3
                reasons.append(f"vol_high_z={vol_z:.2f}")
            elif vol_z >= al:
                score += 2
                reasons.append(f"vol_alert_z={vol_z:.2f}")
            elif vol_z >= pre:
                score += 1
                reasons.append(f"vol_pre_z={vol_z:.2f}")

        # Reject rate score (venue/broker instability)
        rthr = (thr.get("reject_rate", {}) or {})
        if reject_rate is not None:
            al = _safe_float(rthr.get("alert"), 0.15) or 0.15
            hi = _safe_float(rthr.get("high_alert"), 0.30) or 0.30
            if reject_rate >= hi:
                score += 2
                reasons.append(f"reject_rate_high={reject_rate:.2f}")
            elif reject_rate >= al:
                score += 1
                reasons.append(f"reject_rate_alert={reject_rate:.2f}")

        # Event window adds risk points
        if is_event_window:
            pts = int(_safe_float(weights.get("event_risk_points"), 1.0) or 1.0)
            score += max(0, pts)
            reasons.append("event_window")

        level = self._score_to_level(score)
        return level, int(score), reasons

    def _score_to_level(self, score: int) -> str:
        m = self.cfg.get("score_to_level", {}) or {}
        pre = int(m.get("pre_alert_min", 1))
        al = int(m.get("alert_min", 3))
        hi = int(m.get("high_alert_min", 6))
        cr = int(m.get("critical_min", 9))

        if score >= cr:
            return "CRITICAL"
        if score >= hi:
            return "HIGH_ALERT"
        if score >= al:
            return "ALERT"
        if score >= pre:
            return "PRE_ALERT"
        return "NORMAL"

    def _severity(self, level: str) -> int:
        l = str(level).upper()
        return {"NORMAL": 0, "PRE_ALERT": 1, "ALERT": 2, "HIGH_ALERT": 3, "CRITICAL": 4}.get(l, 0)

    def _apply_hysteresis(self, *, computed_level: str, now: float) -> str:
        hyster = self.cfg.get("hysteresis", {}) or {}
        min_secs = int(hyster.get("min_seconds_in_level", 30))
        exit_stable = int(hyster.get("exit_stable_seconds", 90))

        cur = self._level
        cur_sev = self._severity(cur)
        new_sev = self._severity(computed_level)

        # Immediate promote
        if new_sev > cur_sev:
            return computed_level

        # Same level: reset stable timer
        if new_sev == cur_sev:
            self._stable_since_ts = None
            return cur

        # Downgrade path: require minimum time in level + stable window
        time_in_level = now - float(self._since_ts)
        if time_in_level < float(min_secs):
            return cur

        if self._stable_since_ts is None:
            self._stable_since_ts = now
            return cur

        if (now - self._stable_since_ts) < float(exit_stable):
            return cur

        return computed_level

    def _decision_for_level(self, *, level: str, score: int, reasons: List[str]) -> SafeModeDecision:
        actions = (self.cfg.get("actions", {}) or {}).get(level, {}) or {}

        size_mult = float(_clamp(_safe_float(actions.get("size_multiplier"), 1.0) or 1.0, 0.0, 1.0))
        cd_mult = float(_clamp(_safe_float(actions.get("cooldown_multiplier"), 1.0) or 1.0, 1.0, 25.0))
        max_mult = float(_clamp(_safe_float(actions.get("max_trades_multiplier"), 1.0) or 1.0, 0.0, 1.0))

        disable_passive = _safe_bool(actions.get("disable_passive"), False)
        force_ioc = _safe_bool(actions.get("force_ioc"), False)
        force_direct = _safe_bool(actions.get("force_direct"), False)
        cancel_resting = _safe_bool(actions.get("cancel_resting"), False)
        avoid_dark = _safe_bool(actions.get("avoid_dark_pools"), False)
        block_entries = _safe_bool(actions.get("block_new_entries"), False)
        require_exit = _safe_bool(actions.get("require_exit_flag_for_orders"), False)

        active = (self._severity(level) > 0)

        return SafeModeDecision(
            active=active,
            level=str(level).upper(),
            score=int(score),
            reasons=list(reasons),
            size_multiplier=size_mult,
            cooldown_multiplier=cd_mult,
            max_trades_multiplier=max_mult,
            disable_passive=disable_passive,
            force_ioc=force_ioc,
            force_direct=force_direct,
            cancel_resting=cancel_resting,
            avoid_dark_pools=avoid_dark,
            block_new_entries=block_entries,
            require_exit_flag_for_orders=require_exit,
            until_ts=None,
        )


# Backwards-compatible aliases
ExecutionSafeModeDecision = SafeModeDecision
ExecutionSafeModeModule = ExecutionSafeModeMonitor
