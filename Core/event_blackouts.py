from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from zoneinfo import ZoneInfo

VERSION = "STEP18_EVENT_BLACKOUTS_FIX_V8_IGNORE_SESSION_AND_VACUUMS"


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


def _spread_bps(quote: Dict[str, Any]) -> Optional[float]:
    b = _safe_float(quote.get("bid"))
    a = _safe_float(quote.get("ask"))
    if b is None or a is None or b <= 0 or a <= 0:
        return None
    mid = _safe_float(quote.get("mid"))
    if mid is None:
        mid = (b + a) / 2.0
    if mid <= 0:
        return None
    return (a - b) / mid * 10000.0


def _parse_hhmm(s: str) -> Tuple[int, int]:
    s = str(s).strip()
    if ":" not in s:
        raise ValueError(f"Bad time string: {s}")
    hh, mm = s.split(":")
    return int(hh), int(mm)


def _dt_et_from_string(dt_str: str, tz: ZoneInfo) -> datetime:
    dt_str = str(dt_str).strip()
    d = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    return d.replace(tzinfo=tz)


@dataclass(frozen=True)
class EventBlackoutDecision:
    allowed: bool
    action: str
    reason: str
    tags: List[str]
    cancel_resting: bool = False
    force_safe_mode_level: Optional[str] = None
    active_until_ts: Optional[float] = None


class EventBlackoutGate:
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
        tz_name = str(self.cfg.get("timezone", "America/New_York"))
        self.tz = ZoneInfo(tz_name)

        self._shock_active_until_ts: Optional[float] = None
        self._shock_last_reason: str = ""
        self._load_state()

    def _load_config(self, path: Path) -> Dict[str, Any]:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError("event_blackouts.yaml must be a dict")
        data.setdefault("version", 1)
        data.setdefault("open_close_avoidance", {})
        data.setdefault("intraday_vacuums", {})
        data.setdefault("macro_events", {})
        data.setdefault("earnings", {})
        data.setdefault("shock_detection", {})
        return data

    def _persist_state(self) -> None:
        payload = {
            "version": 1,
            "shock_active_until_ts": self._shock_active_until_ts,
            "shock_last_reason": self._shock_last_reason,
            "saved_ts": time.time(),
            "module_version": VERSION,
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            self._shock_active_until_ts = payload.get("shock_active_until_ts")
            self._shock_last_reason = str(payload.get("shock_last_reason") or "")
        except Exception:
            self._shock_active_until_ts = None
            self._shock_last_reason = ""

    def _session_open_close_et(self, now_et: datetime) -> Tuple[datetime, datetime]:
        o = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        c = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        return o, c

    def _is_weekend(self, now_et: datetime) -> bool:
        return now_et.weekday() >= 5

    def _env_truthy(self, *names: str) -> bool:
        for n in names:
            if _safe_bool(os.getenv(n), False):
                return True
        return False

    def pre_trade(
        self,
        *,
        symbol: str,
        side: str,
        qty: int,
        strategy: str,
        quote: Dict[str, Any],
        meta: Optional[Dict[str, Any]] = None,
        now_ts: Optional[float] = None,
    ) -> EventBlackoutDecision:
        meta = dict(meta or {})
        now_ts = float(now_ts) if now_ts is not None else time.time()
        now_et = datetime.fromtimestamp(now_ts, tz=self.tz)

        # TEST OVERRIDES
        ignore_weekends = _safe_bool(meta.get("ignore_weekends"), False) or self._env_truthy(
            "EVENT_BLACKOUTS_IGNORE_WEEKENDS",
            "EVENT_BLACKOUT_IGNORE_WEEKENDS",
        )
        ignore_session = _safe_bool(meta.get("ignore_session"), False) or self._env_truthy(
            "EVENT_BLACKOUTS_IGNORE_SESSION",
            "EVENT_BLACKOUT_IGNORE_SESSION",
        )
        ignore_vacuums = _safe_bool(meta.get("ignore_vacuums"), False) or self._env_truthy(
            "EVENT_BLACKOUTS_IGNORE_VACUUMS",
            "EVENT_BLACKOUT_IGNORE_VACUUMS",
        )

        # 0) Weekend gate
        if (not ignore_weekends) and self._is_weekend(now_et):
            return EventBlackoutDecision(
                allowed=False,
                action="BLOCK_ALL",
                reason="MARKET_CLOSED:WEEKEND",
                tags=["MARKET_CLOSED"],
            )

        session_open, session_close = self._session_open_close_et(now_et)

        # 1) Session-hours gate
        if (not ignore_session) and (now_et < session_open or now_et > session_close):
            return EventBlackoutDecision(
                allowed=False,
                action="BLOCK_ALL",
                reason="MARKET_CLOSED:OUTSIDE_SESSION",
                tags=["MARKET_CLOSED"],
            )

        # 2) Open/close liquidity vacuum windows (IPS) — can be ignored for testing
        if not ignore_vacuums:
            oca = self.cfg.get("open_close_avoidance", {}) or {}
            after_open_min = int(oca.get("avoid_minutes_after_open", 0) or 0)
            before_close_min = int(oca.get("avoid_minutes_before_close", 0) or 0)
            exits_allowed = _safe_bool(oca.get("exits_allowed", True), True)

            if after_open_min > 0:
                window_end = session_open + timedelta(minutes=after_open_min)
                if now_et <= window_end:
                    action = "REDUCE_ONLY" if exits_allowed else "BLOCK_ALL"
                    return EventBlackoutDecision(
                        allowed=False,
                        action=action,
                        reason=f"SESSION_OPEN_VACUUM:<=+{after_open_min}m",
                        tags=["OPEN_VACUUM"],
                        cancel_resting=True,
                        force_safe_mode_level="ALERT",
                    )

            if before_close_min > 0:
                window_start = session_close - timedelta(minutes=before_close_min)
                if now_et >= window_start:
                    action = "REDUCE_ONLY" if exits_allowed else "BLOCK_ALL"
                    return EventBlackoutDecision(
                        allowed=False,
                        action=action,
                        reason=f"SESSION_CLOSE_VACUUM:>={before_close_min}m_to_close",
                        tags=["CLOSE_VACUUM"],
                        cancel_resting=True,
                        force_safe_mode_level="ALERT",
                    )

        # 3) Shock detection with persistence
        sd = self.cfg.get("shock_detection", {}) or {}
        if _safe_bool(sd.get("enabled", False), False):
            if self._shock_active_until_ts is not None and now_ts <= float(self._shock_active_until_ts):
                return EventBlackoutDecision(
                    allowed=False,
                    action=str(sd.get("action") or "REDUCE_ONLY").upper(),
                    reason=f"SHOCK_ACTIVE:{self._shock_last_reason or 'ACTIVE'}",
                    tags=["SHOCK"],
                    cancel_resting=_safe_bool(sd.get("cancel_resting_orders", True), True),
                    force_safe_mode_level=str(sd.get("force_safe_mode_level") or "HIGH_ALERT").upper(),
                    active_until_ts=float(self._shock_active_until_ts),
                )

            trig = _safe_float(sd.get("spread_bps_trigger"), 30.0) or 30.0
            rel = _safe_float(sd.get("spread_bps_release"), 15.0) or 15.0
            spread = _spread_bps(quote)

            if spread is not None and spread >= trig:
                blackout_minutes = int(sd.get("blackout_minutes", 10) or 10)
                self._shock_active_until_ts = now_ts + blackout_minutes * 60.0
                self._shock_last_reason = f"SPREAD_BPS:{spread:.1f}"
                self._persist_state()
                return EventBlackoutDecision(
                    allowed=False,
                    action=str(sd.get("action") or "REDUCE_ONLY").upper(),
                    reason=f"SHOCK_SPREAD:{spread:.1f}bps",
                    tags=["SHOCK", "SPREAD"],
                    cancel_resting=_safe_bool(sd.get("cancel_resting_orders", True), True),
                    force_safe_mode_level=str(sd.get("force_safe_mode_level") or "HIGH_ALERT").upper(),
                    active_until_ts=float(self._shock_active_until_ts),
                )

            if spread is not None and spread <= rel:
                self._shock_active_until_ts = None
                self._shock_last_reason = ""
                self._persist_state()

        return EventBlackoutDecision(
            allowed=True,
            action="ALLOW",
            reason="OK",
            tags=[],
        )
