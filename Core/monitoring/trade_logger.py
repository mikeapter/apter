from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional


def _now_ts() -> float:
    return time.time()


def _safe_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


@dataclass
class TradeEvent:
    """
    Canonical trade/order event record for monitoring + TCA.

    event_type examples:
      - ORDER_SUBMITTED
      - ORDER_FILLED
      - ORDER_REJECTED
      - ORDER_CANCELED
      - ORDER_BLOCKED
      - ERROR
    """
    ts: float
    event_type: str
    symbol: str
    side: str
    qty: int
    strategy: str
    regime: str = "UNKNOWN"

    # IDs / routing
    order_id: Optional[str] = None
    broker: Optional[str] = None
    venue: Optional[str] = None
    order_type: Optional[str] = None

    # Prices
    arrival_price: Optional[float] = None  # decision-time mid/last
    fill_price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None

    # Costs
    commission_usd: Optional[float] = None
    fees_usd: Optional[float] = None

    # Timing
    decision_ts: Optional[float] = None
    submit_ts: Optional[float] = None
    fill_ts: Optional[float] = None
    latency_ms: Optional[float] = None

    # Outcomes
    status: Optional[str] = None
    reason: Optional[str] = None

    # Extra payload
    meta: Optional[Dict[str, Any]] = None


class TradeLogger:
    """
    Append-only JSONL trade log.
    Default path: <repo_root>/Data/Logs/trades.jsonl
    """

    def __init__(self, *, repo_root: Path, path: Optional[Path] = None) -> None:
        self.repo_root = Path(repo_root)
        self.path = Path(path) if path is not None else (self.repo_root / "Data" / "Logs" / "trades.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: TradeEvent) -> None:
        rec = asdict(event)
        # Safety: avoid writing huge nested dicts
        if isinstance(rec.get("meta"), dict):
            try:
                if len(json.dumps(rec["meta"])) > 50_000:
                    rec["meta"] = {"_truncated": True}
            except Exception:
                rec["meta"] = {"_truncated": True}
        line = json.dumps(rec, separators=(",", ":"), ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def log_from_result(
        self,
        *,
        symbol: str,
        side: str,
        qty: int,
        strategy: str,
        meta: Dict[str, Any],
        result: Dict[str, Any],
        broker: Optional[str] = None,
        venue: Optional[str] = None,
        order_type: Optional[str] = None,
        event_type: Optional[str] = None,
        started_ts: Optional[float] = None,
    ) -> None:
        now = _now_ts()

        q = meta.get("quote", {}) if isinstance(meta, dict) else {}
        bid = _safe_float(q.get("bid"), None)
        ask = _safe_float(q.get("ask"), None)

        arrival = _safe_float(meta.get("arrival_price"), None)
        if arrival is None:
            arrival = _safe_float(q.get("mid"), None)
        if arrival is None:
            arrival = _safe_float(q.get("last"), None)

        fill_px = _safe_float(result.get("fill_price"), None)
        if fill_px is None and isinstance(result.get("price"), (int, float)):
            fill_px = _safe_float(result.get("price"), None)

        status = str(result.get("status", "")).upper()

        if event_type is None:
            if status in ("FILLED", "FILL", "EXECUTED"):
                et = "ORDER_FILLED"
            elif status in ("BLOCKED", "REJECTED", "DENIED"):
                et = "ORDER_BLOCKED"
            elif status in ("CANCELED", "CANCELLED"):
                et = "ORDER_CANCELED"
            elif status in ("PAPER", "SUBMITTED", "SENT", "ACCEPTED", "LIVE_SUBMITTED"):
                et = "ORDER_SUBMITTED"
            elif status in ("ERROR",):
                et = "ERROR"
            else:
                et = "ORDER_SUBMITTED"
        else:
            et = event_type

        latency_ms = None
        if started_ts is not None:
            try:
                latency_ms = (now - float(started_ts)) * 1000.0
            except Exception:
                latency_ms = None

        ev = TradeEvent(
            ts=now,
            event_type=et,
            symbol=str(symbol).upper(),
            side=str(side).upper(),
            qty=_safe_int(qty, 0),
            strategy=str(strategy).upper(),
            regime=str(meta.get("regime", meta.get("regime_label", "UNKNOWN"))).upper(),
            order_id=str(result.get("id") or result.get("order_id") or "") or None,
            broker=broker,
            venue=venue or (meta.get("venue") if isinstance(meta, dict) else None),
            order_type=order_type or (meta.get("order_type") if isinstance(meta, dict) else None),
            arrival_price=arrival,
            fill_price=fill_px,
            bid=bid,
            ask=ask,
            commission_usd=_safe_float(result.get("commission_usd"), None),
            fees_usd=_safe_float(result.get("fees_usd"), None),
            decision_ts=_safe_float(meta.get("decision_ts"), None),
            submit_ts=_safe_float(meta.get("submit_ts"), None),
            fill_ts=_safe_float(meta.get("fill_ts"), None),
            latency_ms=latency_ms,
            status=status or None,
            reason=str(result.get("reason") or meta.get("reason") or "") or None,
            meta=meta,
        )
        self.log(ev)
