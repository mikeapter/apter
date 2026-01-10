from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml


# -----------------------------
# helpers
# -----------------------------
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


# -----------------------------
# public return signature
# -----------------------------
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
    STEP 17 — Execution safe mode can tighten:
      - max_trades_multiplier < 1.0  => fewer trades/day allowed
      - cooldown_multiplier  > 1.0   => longer cooldown between trades

    Constructor is compatible with older code:
      TradeThrottle("Config/trade_throttle.yaml")
    """

    def __init__(self, config_path: Union[str, Path], state_path: Optional[Union[str, Path]] = None) -> None:
        self.config_path = Path(config_path)
        if state_path is None:
            # default state next to config
            self.state_path = self.config_path.with_name("trade_throttle_state.json")
        else:
            self.state_path = Path(state_path)

        self._cfg: Dict[str, Any] = {}
        self._day_key: str = ""  # YYYY-MM-DD (UTC by default)

        # state
        self._trade_counts: Dict[str, int] = {}              # regime -> count today
        self._last_trade_ts_by_regime: Dict[str, float] = {} # regime -> epoch seconds

        self._load_cfg()
        self._load_state()

    # -----------------------------
    # config/state IO
    # -----------------------------
    def _load_cfg(self) -> None:
        data = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError("trade_throttle.yaml must be a dict")

        # normalize
        data.setdefault("version", 1)
        data.setdefault("timezone", "UTC")
        data.setdefault("urgency", {})
        data.setdefault("regimes", {})

        # urgency defaults
        urg = data.get("urgency", {}) or {}
        urg.setdefault("tiers", ["LOW", "NORMAL", "HIGH"])
        urg.setdefault("cooldown_multipliers", {"LOW": 1.5, "NORMAL": 1.0, "HIGH": 0.5})
        urg.setdefault("min_effective_cooldown_seconds", 0)

        self._cfg = data

    def _load_state(self) -> None:
        if not self.state_path.exists():
            self._persist_state()
            return
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8") or "{}")
        except Exception:
            raw = {}

        if not isinstance(raw, dict):
            raw = {}

        self._day_key = str(raw.get("day_key") or "")
        self._trade_counts = dict(raw.get("trade_counts") or {})
        self._last_trade_ts_by_regime = dict(raw.get("last_trade_ts_by_regime") or {})

        # ensure types
        self._trade_counts = {str(k).upper(): _coerce_int(v, 0) for k, v in self._trade_counts.items()}
        self._last_trade_ts_by_regime = {
            str(k).upper(): float(v) for k, v in self._last_trade_ts_by_regime.items() if v is not None
        }

        # ensure today key exists (so old state doesn't poison)
        self._ensure_day(self._now())

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

    # -----------------------------
    # time/day handling
    # -----------------------------
    def _now(self) -> datetime:
        # Keep it simple: store state by UTC day.
        # If you later need America/New_York, we can add tz conversion cleanly.
        return _now_utc()

    def _day_key_for(self, dt: datetime) -> str:
        dtu = dt.astimezone(timezone.utc)
        return dtu.strftime("%Y-%m-%d")

    def _ensure_day(self, dt: datetime) -> None:
        key = self._day_key_for(dt)
        if key != self._day_key:
            # reset daily counters when day changes
            self._day_key = key
            self._trade_counts = {}
            self._persist_state()

    # -----------------------------
    # regime/urgency config
    # -----------------------------
    def _get_regime_cfg(self, regime: str) -> Dict[str, Any]:
        reg = _safe_upper(regime, "DEFAULT")
        regimes = self._cfg.get("regimes", {}) or {}
        cfg = regimes.get(reg, None)

        # fallback: DEFAULT if present, else empty
        if cfg is None:
            cfg = regimes.get("DEFAULT", {}) or {}
        if not isinstance(cfg, dict):
            cfg = {}
        return cfg

    def _cooldown_multiplier(self, urgency: str) -> float:
        u = _safe_upper(urgency, "NORMAL")
        urg = self._cfg.get("urgency", {}) or {}
        mults = urg.get("cooldown_multipliers", {}) or {}
        try:
            m = float(mults.get(u, mults.get("NORMAL", 1.0)))
        except Exception:
            m = 1.0
        # clamp to reasonable bounds
        if m < 0.1:
            m = 0.1
        if m > 10.0:
            m = 10.0
        return m

    # -----------------------------
    # public API
    # -----------------------------
    def can_trade(
        self,
        *,
        regime: str,
        now: Optional[datetime] = None,
        urgency: Optional[str] = None,
        # STEP 17 additions (safe mode can tighten)
        max_trades_multiplier: float = 1.0,   # < 1.0 => fewer trades/day
        cooldown_multiplier: float = 1.0,     # > 1.0 => longer cooldown
    ) -> ThrottleDecision:
        """
        Returns a ThrottleDecision with allowed/reason plus diagnostics.

        Backward compatible: callers that don't pass multipliers get defaults (1.0).
        """
        reg = _safe_upper(regime, "DEFAULT")
        tier = _safe_upper(urgency, "NORMAL")

        now_dt = now or self._now()
        self._ensure_day(now_dt)

        cfg = self._get_regime_cfg(reg)
        max_trades = _coerce_int(cfg.get("max_trades_per_day", 0), 0)
        cooldown = _coerce_int(cfg.get("min_seconds_between_trades", 0), 0)

        # ---- STEP 17: tighten daily frequency
        try:
            mtm = float(max_trades_multiplier)
        except Exception:
            mtm = 1.0
        if mtm < 0.0:
            mtm = 0.0
        if mtm > 1.0:
            mtm = 1.0

        eff_max_trades = max_trades
        if max_trades > 0:
            eff_max_trades = max(0, int(max_trades * mtm))
            # avoid accidental "no trades ever" unless mtm == 0.0
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

        # ---- cooldown check
        last_ts = self._last_trade_ts_by_regime.get(reg)
        seconds_since = None
        seconds_until = 0

        # existing urgency scaling
        urg_mult = self._cooldown_multiplier(tier)

        # STEP 17: safe-mode cooldown tightening
        try:
            cdm = float(cooldown_multiplier)
        except Exception:
            cdm = 1.0
        if cdm < 1.0:
            cdm = 1.0
        if cdm > 25.0:
            cdm = 25.0

        min_eff = _coerce_int((self._cfg.get("urgency", {}) or {}).get("min_effective_cooldown_seconds", 0), 0)
        eff_cd = int(round(cooldown * float(urg_mult) * float(cdm)))
        if eff_cd < min_eff:
            eff_cd = min_eff

        if last_ts is not None and eff_cd > 0:
            seconds_since = int(now_dt.timestamp() - float(last_ts))
            if seconds_since < eff_cd:
                seconds_until = max(0, eff_cd - seconds_since)
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
                    seconds_until_allowed=seconds_until,
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
            seconds_since_last_trade=seconds_since,
            seconds_until_allowed=seconds_until,
        )

    def record_trade(
        self,
        *,
        regime: str,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        ts: Optional[float] = None,
    ) -> None:
        """
        Call this after a successful SUBMITTED/FILLED decision.
        """
        reg = _safe_upper(regime, "DEFAULT")
        now_dt = self._now()
        self._ensure_day(now_dt)

        t = float(ts) if ts is not None else float(now_dt.timestamp())
        self._trade_counts[reg] = _coerce_int(self._trade_counts.get(reg, 0), 0) + 1
        self._last_trade_ts_by_regime[reg] = t
        self._persist_state()

    def stats(self) -> Dict[str, Any]:
        """
        Lightweight observability.
        """
        return {
            "day_key": self._day_key,
            "trade_counts": dict(self._trade_counts),
            "last_trade_ts_by_regime": dict(self._last_trade_ts_by_regime),
        }
