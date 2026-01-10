from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml


def _safe_upper(x: Any, default: str = "") -> str:
    if x is None:
        return default
    try:
        s = str(x).strip()
        return s.upper() if s else default
    except Exception:
        return default


def _coerce_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        return int(float(x))
    except Exception:
        return default


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ThrottleDecision:
    allowed: bool
    reason: str

    regime: str
    urgency_tier: str

    max_trades_per_day: int
    trades_today: int

    cooldown_seconds: int
    effective_cooldown_seconds: int

    seconds_since_last_trade: Optional[int]
    seconds_until_allowed: int


class TradeThrottle:
    """
    STEP 12 — Trade frequency throttle + cooldowns
    STEP 17 — Safe Mode tightening:
      - max_trades_multiplier < 1.0  => fewer trades/day allowed
      - cooldown_multiplier  > 1.0  => longer cooldown between trades
    """

    def __init__(self, config_path: Union[str, Path], state_path: Optional[Union[str, Path]] = None) -> None:
        self.config_path = Path(config_path)
        self.state_path = Path(state_path) if state_path else self.config_path.with_name("trade_throttle_state.json")
        self._state_path_provided = state_path is not None

        self._cfg: Dict[str, Any] = {}
        self._day_key: str = ""  # UTC YYYY-MM-DD

        # daily state
        self._trade_counts: Dict[str, int] = {}              # REGIME -> count today
        self._last_trade_ts_by_regime: Dict[str, float] = {} # REGIME -> epoch sec

        self._load_cfg()
        self._load_state()

    # ---------------- config/state IO ----------------
    def _load_cfg(self) -> None:
        data = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError("trade_throttle.yaml must be a dict")

        data.setdefault("version", 1)
        data.setdefault("urgency", {})
        data.setdefault("regimes", {})

        urg = data.get("urgency", {}) or {}
        urg.setdefault("cooldown_multipliers", {"LOW": 1.5, "NORMAL": 1.0, "HIGH": 0.5})
        urg.setdefault("min_effective_cooldown_seconds", 0)

        self._cfg = data

        # If the YAML config specifies a state file, prefer it (relative paths are relative to the config folder).
        if not self._state_path_provided:
            sf = self._cfg.get('state_file') or self._cfg.get('state_path')
            if sf:
                p = Path(str(sf))
                if not p.is_absolute():
                    p = self.config_path.parent / p
                self.state_path = p


    def _persist_state(self) -> None:
        payload = {
            "day_key": self._day_key,
            "trade_counts": self._trade_counts,
            "last_trade_ts_by_regime": self._last_trade_ts_by_regime,
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.state_path)

    def _load_state(self) -> None:
        if not self.state_path.exists():
            self._day_key = self._day_key_for(_now_utc())
            self._persist_state()
            return

        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8") or "{}")
        except Exception:
            raw = {}

        if not isinstance(raw, dict):
            raw = {}

        self._day_key = str(raw.get("day_key") or "")
        self._trade_counts = {str(k).upper(): _coerce_int(v, 0) for k, v in dict(raw.get("trade_counts") or {}).items()}
        self._last_trade_ts_by_regime = {
            str(k).upper(): float(v) for k, v in dict(raw.get("last_trade_ts_by_regime") or {}).items() if v is not None
        }


    # ---------------- time/day ----------------
    def _day_key_for(self, dt: datetime) -> str:
        """Compute the 'trading day' key.

        Uses config:
          - timezone (e.g., America/New_York)
          - day_reset_hhmm (e.g., 09:30)

        The day rolls over at day_reset_hhmm *in the configured timezone*.
        If dt is naive, it is interpreted as being in the configured timezone.
        """
        tz_name = self._cfg.get('timezone') or 'UTC'
        try:
            tz = ZoneInfo(str(tz_name))
        except Exception:
            tz = timezone.utc

        if dt.tzinfo is None:
            local_dt = dt.replace(tzinfo=tz)
        else:
            local_dt = dt.astimezone(tz)

        reset_hhmm = str(self._cfg.get('day_reset_hhmm') or '00:00')
        try:
            hh, mm = reset_hhmm.split(':', 1)
            reset_hour = int(hh)
            reset_min = int(mm)
        except Exception:
            reset_hour, reset_min = 0, 0

        reset_dt = local_dt.replace(hour=reset_hour, minute=reset_min, second=0, microsecond=0)
        day = local_dt.date()
        if local_dt < reset_dt:
            # still part of previous trading day
            from datetime import timedelta
            day = day - timedelta(days=1)
        return day.strftime('%Y-%m-%d')

    def _ensure_day(self, dt: datetime) -> None:
        key = self._day_key_for(dt)
        if key != self._day_key:
            self._day_key = key
            self._trade_counts = {}
            self._persist_state()

    # ---------------- config helpers ----------------
    def _get_regime_cfg(self, regime: str) -> Dict[str, Any]:
        reg = _safe_upper(regime, 'DEFAULT')
        regimes = self._cfg.get('regimes', {}) or {}
        if not isinstance(regimes, dict):
            return {}
        # Accept both upper and lower keys (tests use 'default')
        cfg = regimes.get(reg)
        if cfg is None:
            cfg = regimes.get(reg.lower())
        if cfg is None:
            cfg = regimes.get('DEFAULT')
        if cfg is None:
            cfg = regimes.get('default')
        if cfg is None:
            cfg = {}
        return cfg if isinstance(cfg, dict) else {}

    def _cooldown_multiplier(self, urgency: str) -> float:
        u = _safe_upper(urgency, "NORMAL")
        mults = (self._cfg.get("urgency", {}) or {}).get("cooldown_multipliers", {}) or {}
        try:
            m = float(mults.get(u, mults.get("NORMAL", 1.0)))
        except Exception:
            m = 1.0
        # clamp
        return max(0.1, min(10.0, m))

    # ---------------- public API ----------------
    def can_trade(
        self,
        *,
        regime: str,
        now: Optional[datetime] = None,
        urgency: Optional[str] = None,
        # STEP 17 additions:
        max_trades_multiplier: float = 1.0,
        cooldown_multiplier: float = 1.0,
    ) -> ThrottleDecision:
        reg = _safe_upper(regime, "DEFAULT")
        tier = _safe_upper(urgency, "NORMAL")

        now_dt = now or _now_utc()
        self._ensure_day(now_dt)

        cfg = self._get_regime_cfg(reg)
        max_trades = _coerce_int(cfg.get("max_trades_per_day", 0), 0)
        cooldown = _coerce_int(cfg.get("min_seconds_between_trades", 0), 0)

        # ---- STEP 17: tighten daily frequency
        try:
            mtm = float(max_trades_multiplier)
        except Exception:
            mtm = 1.0
        mtm = max(0.0, min(1.0, mtm))

        eff_max_trades = max_trades
        if max_trades > 0:
            eff_max_trades = max(0, int(max_trades * mtm))
            if mtm > 0.0 and eff_max_trades == 0:
                eff_max_trades = 1

        trades_today = _coerce_int(self._trade_counts.get(reg, 0), 0)
        if eff_max_trades > 0 and trades_today >= eff_max_trades:
            return ThrottleDecision(
                allowed=False,
                reason="daily_frequency_limit_reached",
                regime=reg,
                urgency_tier=tier,
                max_trades_per_day=eff_max_trades,
                trades_today=trades_today,
                cooldown_seconds=cooldown,
                effective_cooldown_seconds=cooldown,
                seconds_since_last_trade=None,
                seconds_until_allowed=0,
            )

        # ---- STEP 17: tighten cooldown
        try:
            cdm = float(cooldown_multiplier)
        except Exception:
            cdm = 1.0
        cdm = max(1.0, min(25.0, cdm))

        urg_mult = self._cooldown_multiplier(tier)
        min_eff = _coerce_int((self._cfg.get("urgency", {}) or {}).get("min_effective_cooldown_seconds", 0), 0)
        eff_cd = int(round(cooldown * float(urg_mult) * float(cdm)))
        if eff_cd < min_eff:
            eff_cd = min_eff

        last_ts = self._last_trade_ts_by_regime.get(reg)
        if last_ts is not None and eff_cd > 0:
            seconds_since = int(now_dt.timestamp() - float(last_ts))
            if seconds_since < eff_cd:
                return ThrottleDecision(
                    allowed=False,
                    reason="cooldown_active",
                    regime=reg,
                    urgency_tier=tier,
                    max_trades_per_day=eff_max_trades,
                    trades_today=trades_today,
                    cooldown_seconds=cooldown,
                    effective_cooldown_seconds=eff_cd,
                    seconds_since_last_trade=seconds_since,
                    seconds_until_allowed=max(0, eff_cd - seconds_since),
                )

        return ThrottleDecision(
            allowed=True,
            reason="ok",
            regime=reg,
            urgency_tier=tier,
            max_trades_per_day=eff_max_trades,
            trades_today=trades_today,
            cooldown_seconds=cooldown,
            effective_cooldown_seconds=eff_cd,
            seconds_since_last_trade=None if last_ts is None else int(now_dt.timestamp() - float(last_ts)),
            seconds_until_allowed=0,
        )

    def record_trade(self, regime: str, symbol: Optional[str] = None, strategy: Optional[str] = None, ts: Optional[float] = None, now: Any = None) -> None:
        # Backwards-compatible: tests may pass `now=datetime(...)` instead of `ts=...`
        if ts is None and now is not None:
            try:
                # datetime-like
                ts = float(now.timestamp())  # type: ignore[attr-defined]
            except Exception:
                try:
                    ts = float(now)
                except Exception:
                    ts = None
        reg = _safe_upper(regime, "DEFAULT")
        # Use the provided time for daily rollover accounting when available
        if now is not None and hasattr(now, 'tzinfo'):
            try:
                now_dt = now  # datetime-like
            except Exception:
                now_dt = _now_utc()
        elif ts is not None:
            try:
                now_dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
            except Exception:
                now_dt = _now_utc()
        else:
            now_dt = _now_utc()
        self._ensure_day(now_dt)

        t = float(ts) if ts is not None else float(now_dt.timestamp())
        self._trade_counts[reg] = _coerce_int(self._trade_counts.get(reg, 0), 0) + 1
        self._last_trade_ts_by_regime[reg] = t
        self._persist_state()

    def stats(self) -> Dict[str, Any]:
        return {
            "day_key": self._day_key,
            "trade_counts": dict(self._trade_counts),
            "last_trade_ts_by_regime": dict(self._last_trade_ts_by_regime),
        }
