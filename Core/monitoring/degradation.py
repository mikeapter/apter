from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .tca_engine import TCAEngine, TCAConfig


def _now_ts() -> float:
    return time.time()


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


@dataclass(frozen=True)
class DegradationThresholds:
    window_trades: int = 50
    max_avg_total_cost_bps: float = 8.0
    max_p90_is_bps: float = 15.0
    max_avg_latency_ms: float = 250.0
    warn_forced_safe_mode_level: str = "ALERT"
    critical_forced_safe_mode_level: str = "CRITICAL"


@dataclass(frozen=True)
class DegradationAction:
    level: str  # "OK" | "WARN" | "CRITICAL"
    reason: str
    details: Dict[str, Any]


class DegradationMonitor:
    """
    STEP 21 — Degradation triggers + automated responses.

    Uses recent TCA stats (rolling window) to decide:
      - OK: no action
      - WARN: force safe-mode (ALERT)
      - CRITICAL: force safe-mode (CRITICAL) + pause via slippage state
    """

    def __init__(
        self,
        *,
        trade_log_path: Path,
        execution_safe_mode_state_path: Path,
        slippage_state_path: Optional[Path] = None,
        thresholds: Optional[DegradationThresholds] = None,
    ) -> None:
        self.trade_log_path = Path(trade_log_path)
        self.safe_mode_state_path = Path(execution_safe_mode_state_path)
        self.slippage_state_path = Path(slippage_state_path) if slippage_state_path is not None else None
        self.th = thresholds or DegradationThresholds()
        self.tca = TCAEngine(trade_log_path=self.trade_log_path, cfg=TCAConfig())

    def evaluate(self) -> DegradationAction:
        df = self.tca.load_events()
        tm = self.tca.compute_trade_metrics(df)

        if tm.empty:
            return DegradationAction(level="OK", reason="no_trades", details={})

        recent = tm.dropna(subset=["total_cost_bps"]).tail(int(self.th.window_trades)).copy()
        if recent.empty:
            return DegradationAction(level="OK", reason="no_cost_data", details={})

        avg_cost = float(recent["total_cost_bps"].mean())
        p90_is = float(recent["impl_shortfall_bps"].quantile(0.90))
        avg_lat = float(recent["latency_ms"].dropna().mean()) if "latency_ms" in recent.columns else 0.0

        reasons: List[str] = []
        if avg_cost > self.th.max_avg_total_cost_bps:
            reasons.append(f"avg_total_cost_bps={avg_cost:.2f}>{self.th.max_avg_total_cost_bps:.2f}")
        if p90_is > self.th.max_p90_is_bps:
            reasons.append(f"p90_is_bps={p90_is:.2f}>{self.th.max_p90_is_bps:.2f}")
        if avg_lat and avg_lat > self.th.max_avg_latency_ms:
            reasons.append(f"avg_latency_ms={avg_lat:.1f}>{self.th.max_avg_latency_ms:.1f}")

        if not reasons:
            return DegradationAction(
                level="OK",
                reason="within_thresholds",
                details={"avg_total_cost_bps": avg_cost, "p90_is_bps": p90_is, "avg_latency_ms": avg_lat, "n": int(len(recent))},
            )

        level = "WARN"
        if len(reasons) >= 2:
            level = "CRITICAL"

        return DegradationAction(
            level=level,
            reason=";".join(reasons),
            details={"avg_total_cost_bps": avg_cost, "p90_is_bps": p90_is, "avg_latency_ms": avg_lat, "n": int(len(recent))},
        )

    def apply(self, action: DegradationAction) -> None:
        now = _now_ts()

        # --- force safe-mode via state file (ExecutionSafeModeModule will honor forced_level) ---
        safe_state = _read_json(self.safe_mode_state_path, default={})
        if not isinstance(safe_state, dict):
            safe_state = {}

        if action.level == "OK":
            if safe_state.get("forced_level"):
                safe_state["forced_level"] = ""
                safe_state["forced_reason"] = ""
                safe_state["forced_ts"] = now
                _write_json(self.safe_mode_state_path, safe_state)

            # If we paused due to degradation earlier, unpause when OK again
            if self.slippage_state_path is not None:
                sstate = _read_json(self.slippage_state_path, default={})
                if isinstance(sstate, dict) and sstate.get("paused") is True and str(sstate.get("pause_reason", "")).startswith("DEGRADATION_"):
                    sstate["paused"] = False
                    sstate["pause_reason"] = ""
                    _write_json(self.slippage_state_path, sstate)
            return

        forced = self.th.warn_forced_safe_mode_level if action.level == "WARN" else self.th.critical_forced_safe_mode_level
        safe_state["forced_level"] = forced
        safe_state["forced_reason"] = f"TCA_DEGRADATION:{action.reason}"
        safe_state["forced_ts"] = now
        _write_json(self.safe_mode_state_path, safe_state)

        # CRITICAL => pause (kill-switch)
        if action.level == "CRITICAL" and self.slippage_state_path is not None:
            sstate = _read_json(self.slippage_state_path, default={})
            if not isinstance(sstate, dict):
                sstate = {}
            sstate["paused"] = True
            sstate["pause_reason"] = f"DEGRADATION_CRITICAL:{action.reason}"
            _write_json(self.slippage_state_path, sstate)
