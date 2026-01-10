from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import time
import yaml
from pathlib import Path

Mode = str  # "OK" | "WARN" | "OUTAGE"

@dataclass
class SlaBand:
    warn: int
    outage: int

@dataclass
class LatencySla:
    quote_age_ms: SlaBand
    heartbeat_gap_ms: SlaBand
    order_ack_ms: SlaBand
    breaches_to_enter_warn: int
    breaches_to_enter_outage: int
    ok_samples_to_recover: int
    failover_enabled: bool
    failover_outage_grace_ms: int

def now_ms() -> int:
    return int(time.time() * 1000)

def load_latency_sla(path: str = "config/latency_sla.yaml") -> LatencySla:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    cfg = data["latency_sla"]

    return LatencySla(
        quote_age_ms=SlaBand(**cfg["quote_age_ms"]),
        heartbeat_gap_ms=SlaBand(**cfg["heartbeat_gap_ms"]),
        order_ack_ms=SlaBand(**cfg["order_ack_ms"]),
        breaches_to_enter_warn=int(cfg.get("breaches_to_enter_warn", 2)),
        breaches_to_enter_outage=int(cfg.get("breaches_to_enter_outage", 2)),
        ok_samples_to_recover=int(cfg.get("ok_samples_to_recover", 5)),
        failover_enabled=bool(cfg.get("failover", {}).get("enabled", True)),
        failover_outage_grace_ms=int(cfg.get("failover", {}).get("outage_grace_ms", 3000)),
    )

@dataclass
class Event:
    level: str   # "INFO" | "WARN" | "OUTAGE"
    code: str
    msg: str

@dataclass
class Decision:
    mode: Mode
    can_open_new_risk: bool
    allow_only_reduce_risk: bool
    allow_market_orders: bool
    request_failover: bool
    events: List[Event]

class LatencyMonitor:
    """
    Tracks:
      - per-feed heartbeats
      - per-symbol quote freshness
      - order send->ack latency
    Produces:
      - mode (OK/WARN/OUTAGE)
      - what trading is allowed
      - failover request flag
    """
    def __init__(self, sla: LatencySla):
        self.sla = sla

        self.last_heartbeat_ms: Dict[str, int] = {}
        self.last_quote_data_ts_ms: Dict[str, int] = {}   # symbol -> data_ts
        self.last_quote_recv_ts_ms: Dict[str, int] = {}   # symbol -> received_ts
        self.last_order_ack_ms: Optional[int] = None

        self._mode: Mode = "OK"
        self._warn_breaches = 0
        self._outage_breaches = 0
        self._ok_samples = 0

        self._outage_since_ms: Optional[int] = None

    # --------- updates ---------
    def update_heartbeat(self, feed: str, heartbeat_ts_ms: int) -> None:
        self.last_heartbeat_ms[feed] = int(heartbeat_ts_ms)

    def update_quote(self, symbol: str, data_ts_ms: int, received_ts_ms: int) -> None:
        self.last_quote_data_ts_ms[symbol] = int(data_ts_ms)
        self.last_quote_recv_ts_ms[symbol] = int(received_ts_ms)

    def update_order_ack_latency(self, sent_ts_ms: int, ack_ts_ms: int) -> None:
        self.last_order_ack_ms = int(ack_ts_ms) - int(sent_ts_ms)

    # --------- evaluation ---------
    def evaluate(self, now_ts_ms: Optional[int] = None) -> Decision:
        now_ts_ms = int(now_ts_ms) if now_ts_ms is not None else now_ms()
        events: List[Event] = []

        worst_level = "OK"  # OK < WARN < OUTAGE

        def bump(level: str, code: str, msg: str):
            nonlocal worst_level
            events.append(Event(level=level, code=code, msg=msg))
            if level == "OUTAGE":
                worst_level = "OUTAGE"
            elif level == "WARN" and worst_level != "OUTAGE":
                worst_level = "WARN"

        # 1) Feed heartbeat checks
        for feed, hb in self.last_heartbeat_ms.items():
            gap = now_ts_ms - hb
            if gap >= self.sla.heartbeat_gap_ms.outage:
                bump("OUTAGE", "FEED_HEARTBEAT_STALE", f"feed={feed} gap_ms={gap}")
            elif gap >= self.sla.heartbeat_gap_ms.warn:
                bump("WARN", "FEED_HEARTBEAT_LAG", f"feed={feed} gap_ms={gap}")

        # 2) Quote staleness checks (use received_ts to be safe in live)
        for symbol, recv_ts in self.last_quote_recv_ts_ms.items():
            age = now_ts_ms - recv_ts
            if age >= self.sla.quote_age_ms.outage:
                bump("OUTAGE", "QUOTE_STALE", f"symbol={symbol} age_ms={age}")
            elif age >= self.sla.quote_age_ms.warn:
                bump("WARN", "QUOTE_AGING", f"symbol={symbol} age_ms={age}")

        # 3) Order ack SLA (if we have one)
        if self.last_order_ack_ms is not None:
            lat = self.last_order_ack_ms
            if lat >= self.sla.order_ack_ms.outage:
                bump("OUTAGE", "ORDER_ACK_SLA", f"sent_to_ack_ms={lat}")
            elif lat >= self.sla.order_ack_ms.warn:
                bump("WARN", "ORDER_ACK_SLA", f"sent_to_ack_ms={lat}")

        # --------- mode machine (with hysteresis) ---------
        if worst_level == "OUTAGE":
            self._outage_breaches += 1
            self._warn_breaches = 0
            self._ok_samples = 0
        elif worst_level == "WARN":
            self._warn_breaches += 1
            self._outage_breaches = 0
            self._ok_samples = 0
        else:
            self._ok_samples += 1
            self._warn_breaches = 0
            self._outage_breaches = 0

        prev_mode = self._mode

        if self._outage_breaches >= self.sla.breaches_to_enter_outage:
            self._mode = "OUTAGE"
        elif self._warn_breaches >= self.sla.breaches_to_enter_warn and self._mode != "OUTAGE":
            self._mode = "WARN"
        elif self._ok_samples >= self.sla.ok_samples_to_recover:
            self._mode = "OK"

        if self._mode == "OUTAGE":
            if self._outage_since_ms is None:
                self._outage_since_ms = now_ts_ms
        else:
            self._outage_since_ms = None

        if prev_mode != self._mode:
            events.append(Event("INFO", "MODE_SWITCH", f"{prev_mode} -> {self._mode}"))

        # --------- stale quote response logic ---------
        if self._mode == "OK":
            can_open_new_risk = True
            allow_only_reduce_risk = False
            allow_market_orders = True
        elif self._mode == "WARN":
            # tightened: no market orders; prefer passive limits; smaller size in your strategy layer
            can_open_new_risk = True
            allow_only_reduce_risk = False
            allow_market_orders = False
        else:  # OUTAGE
            # block new risk; only reduce/flatten/cancel
            can_open_new_risk = False
            allow_only_reduce_risk = True
            allow_market_orders = False

        # --------- failover request ---------
        request_failover = False
        if self.sla.failover_enabled and self._mode == "OUTAGE" and self._outage_since_ms is not None:
            if (now_ts_ms - self._outage_since_ms) >= self.sla.failover_outage_grace_ms:
                request_failover = True

        return Decision(
            mode=self._mode,
            can_open_new_risk=can_open_new_risk,
            allow_only_reduce_risk=allow_only_reduce_risk,
            allow_market_orders=allow_market_orders,
            request_failover=request_failover,
            events=events,
        )
