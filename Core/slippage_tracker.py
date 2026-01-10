from __future__ import annotations

import json
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


def _percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    v = sorted(values)
    if len(v) == 1:
        return v[0]
    k = (len(v) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(v) - 1)
    if f == c:
        return v[f]
    d0 = v[f] * (c - k)
    d1 = v[c] * (k - f)
    return d0 + d1


@dataclass
class SlippageResult:
    realized_bps: float
    realized_usd: float
    hourly_usd: float
    daily_usd: float
    paused: bool
    severity: str  # OK / WARN / SEVERE
    reason: str


class SlippageTracker:
    """
    STEP 15: slippage tracking + hard limits (kill-switch)

    Tracks:
      - per-trade slippage (bps and $)
      - hourly and daily slippage budgets
      - rolling stats (median and p90 bps)

    Hard behaviors:
      - if severe single-trade slippage breach => PAUSE TRADING
      - if daily slippage budget breached => PAUSE TRADING
    """

    def __init__(
        self,
        state_path: Union[str, Path],
        events_path: Union[str, Path],
        *,
        max_acceptable_slippage_bps: float = 5.0,
        severe_multiplier: float = 2.0,
        warn_multiplier: float = 1.5,
        hourly_slippage_limit_usd: float = 500.0,
        daily_slippage_limit_usd: float = 2000.0,
        equity_slippage_limit_pct: float = 0.001,  # 0.1% of equity
    ):
        self.state_path = Path(state_path)
        self.events_path = Path(events_path)

        self.max_acceptable_slippage_bps = float(max_acceptable_slippage_bps)
        self.severe_multiplier = float(severe_multiplier)
        self.warn_multiplier = float(warn_multiplier)

        self.hourly_slippage_limit_usd = float(hourly_slippage_limit_usd)
        self.daily_slippage_limit_usd = float(daily_slippage_limit_usd)
        self.equity_slippage_limit_pct = float(equity_slippage_limit_pct)

        self._state = self._load_state()

    # ---------------- state ----------------

    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "paused": False,
            "pause_reason": "",
            "daily_usd": 0.0,
            "hourly_usd": 0.0,
            "daily_start_ts": time.time(),
            "hourly_start_ts": time.time(),
            "recent_bps": [],  # rolling list for median/p90
        }

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")

    def _append_event(self, event: Dict[str, Any]) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    # ---------------- public API ----------------

    def is_paused(self) -> bool:
        return bool(self._state.get("paused", False))

    def pause(self, reason: str) -> None:
        self._state["paused"] = True
        self._state["pause_reason"] = str(reason)
        self._save_state()

    def resume(self) -> None:
        self._state["paused"] = False
        self._state["pause_reason"] = ""
        self._save_state()

    def reset_budgets(self) -> None:
        now = time.time()
        self._state["daily_usd"] = 0.0
        self._state["hourly_usd"] = 0.0
        self._state["daily_start_ts"] = now
        self._state["hourly_start_ts"] = now
        self._save_state()

    def maybe_roll_windows(self) -> None:
        now = time.time()
        # hourly window
        if now - float(self._state.get("hourly_start_ts", now)) >= 3600.0:
            self._state["hourly_usd"] = 0.0
            self._state["hourly_start_ts"] = now
        # daily window
        if now - float(self._state.get("daily_start_ts", now)) >= 86400.0:
            self._state["daily_usd"] = 0.0
            self._state["daily_start_ts"] = now
        self._save_state()

    def record_fill(
        self,
        *,
        symbol: str,
        side: str,
        qty: int,
        expected_price: float,
        fill_price: float,
        account_equity: Optional[float] = None,
        ts: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> SlippageResult:
        """
        Records a fill, updates budgets, and may pause trading.
        Slippage sign is direction-adjusted:
          BUY: fill - expected
          SELL: expected - fill
        """
        self.maybe_roll_windows()
        now = time.time() if ts is None else float(ts)

        qty_i = max(0, _safe_int(qty, 0))
        exp = float(expected_price)
        fill = float(fill_price)

        side_u = str(side).upper().strip()
        direction = +1 if side_u in ("BUY", "B", "LONG") else -1

        # direction-adjusted
        slip = (fill - exp) if direction == +1 else (exp - fill)
        slip_bps = 0.0 if exp <= 0 else (slip / exp) * 10000.0
        slip_usd = slip * float(qty_i)

        # Update rolling stats
        recent = list(self._state.get("recent_bps", []))
        recent.append(float(slip_bps))
        max_n = 500
        if len(recent) > max_n:
            recent = recent[-max_n:]
        self._state["recent_bps"] = recent

        # Update budgets (use absolute $ impact for budgets)
        abs_usd = abs(float(slip_usd))
        self._state["hourly_usd"] = float(self._state.get("hourly_usd", 0.0)) + abs_usd
        self._state["daily_usd"] = float(self._state.get("daily_usd", 0.0)) + abs_usd

        # Equity-based daily cap
        equity_cap_usd = None
        if account_equity is not None:
            equity_cap_usd = float(account_equity) * float(self.equity_slippage_limit_pct)

        # Severity checks
        severity = "OK"
        reason = ""

        warn_bps = self.max_acceptable_slippage_bps * self.warn_multiplier
        severe_bps = self.max_acceptable_slippage_bps * self.severe_multiplier

        if slip_bps >= severe_bps:
            severity = "SEVERE"
            reason = f"single_trade_slippage_bps={slip_bps:.2f} >= severe({severe_bps:.2f})"
            self.pause(reason)
        elif slip_bps >= warn_bps:
            severity = "WARN"
            reason = f"single_trade_slippage_bps={slip_bps:.2f} >= warn({warn_bps:.2f})"

        # Budget breach checks
        daily_limit = self.daily_slippage_limit_usd
        if equity_cap_usd is not None:
            daily_limit = min(daily_limit, equity_cap_usd)

        if float(self._state["daily_usd"]) >= float(daily_limit):
            severity = "SEVERE"
            reason = f"daily_slippage_usd={self._state['daily_usd']:.2f} >= limit({daily_limit:.2f})"
            self.pause(reason)

        if float(self._state["hourly_usd"]) >= float(self.hourly_slippage_limit_usd):
            if severity != "SEVERE":
                severity = "WARN"
                reason = f"hourly_slippage_usd={self._state['hourly_usd']:.2f} >= limit({self.hourly_slippage_limit_usd:.2f})"

        # Persist event
        event = {
            "ts": now,
            "symbol": symbol,
            "side": side_u,
            "qty": qty_i,
            "expected_price": exp,
            "fill_price": fill,
            "slippage": slip,
            "slippage_bps": slip_bps,
            "slippage_usd": slip_usd,
            "abs_slippage_usd": abs_usd,
            "hourly_usd": self._state["hourly_usd"],
            "daily_usd": self._state["daily_usd"],
            "paused": self.is_paused(),
            "severity": severity,
            "reason": reason,
            "extra": extra or {},
        }
        self._append_event(event)
        self._save_state()

        return SlippageResult(
            realized_bps=float(slip_bps),
            realized_usd=float(slip_usd),
            hourly_usd=float(self._state["hourly_usd"]),
            daily_usd=float(self._state["daily_usd"]),
            paused=self.is_paused(),
            severity=severity,
            reason=reason,
        )

    def stats(self) -> Dict[str, Any]:
        recent = list(self._state.get("recent_bps", []))
        median = _percentile(recent, 50.0)
        p90 = _percentile(recent, 90.0)
        return {
            "paused": self.is_paused(),
            "pause_reason": self._state.get("pause_reason", ""),
            "hourly_usd": float(self._state.get("hourly_usd", 0.0)),
            "daily_usd": float(self._state.get("daily_usd", 0.0)),
            "median_bps": median,
            "p90_bps": p90,
            "n": len(recent),
        }


# Backwards-compatible alias
SlippageDecision = SlippageResult
