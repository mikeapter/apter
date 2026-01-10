from __future__ import annotations

import os
import time
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

try:
    import yaml
except Exception as e:  # pragma: no cover
    raise RuntimeError("Missing dependency: pyyaml. Install with: pip install pyyaml") from e

log = logging.getLogger("data_sources")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _now() -> float:
    return time.time()


def _bps_diff(a: float, b: float) -> float:
    if a == 0:
        return float("inf")
    return abs(a - b) / abs(a) * 10_000.0


@dataclass
class QuoteL1:
    symbol: str
    bid: float
    ask: float
    ts: float  # epoch seconds


@dataclass
class FeedHealth:
    ok: bool
    reason: str
    active_vendor: str
    last_update_ts: float
    last_heartbeat_ts: float
    latency_ms: float
    missed_heartbeats: int


class VendorAdapter:
    """Interface for vendor adapters. Implement what you need as you go."""
    name: str

    def heartbeat(self) -> bool:
        return True

    def get_l1(self, symbol: str) -> QuoteL1:
        raise NotImplementedError


class StubAdapter(VendorAdapter):
    """A deterministic adapter for tests and early wiring (no external calls)."""

    def __init__(self, name: str, *, price: float = 100.0, stale_seconds: float = 0.0, fail: bool = False):
        self.name = name
        self._price = float(price)
        self._stale_seconds = float(stale_seconds)
        self._fail = bool(fail)

    def heartbeat(self) -> bool:
        return not self._fail

    def get_l1(self, symbol: str) -> QuoteL1:
        if self._fail:
            raise RuntimeError(f"{self.name} forced failure")
        ts = _now() - self._stale_seconds
        return QuoteL1(symbol=symbol, bid=self._price - 0.01, ask=self._price + 0.01, ts=ts)


class FailoverFeed:
    """
    Wraps primary + secondary vendor for one feed.
    - Fails over on exceptions, missed heartbeats, stale data, or latency outage.
    - Optional failback (disabled by default).
    """

    def __init__(self, feed_name: str, primary: VendorAdapter, secondary: VendorAdapter, policy: Dict[str, Any]):
        self.feed_name = feed_name
        self.primary = primary
        self.secondary = secondary
        self.policy = policy

        self.active = primary
        self._missed_heartbeats = 0
        self._last_update_ts = 0.0
        self._last_heartbeat_ts = 0.0
        self._latency_ms = 0.0
        self._last_failover_ts = 0.0

    def _policy(self, key: str, default: Any) -> Any:
        return self.policy.get(key, default)

    def _switch_to(self, adapter: VendorAdapter, reason: str) -> None:
        if self.active.name == adapter.name:
            return
        self.active = adapter
        self._last_failover_ts = _now()
        log.warning("FAILOVER feed=%s -> %s reason=%s", self.feed_name, adapter.name, reason)

    def _check_heartbeat(self) -> None:
        ok = self.active.heartbeat()
        self._last_heartbeat_ts = _now()
        if ok:
            self._missed_heartbeats = 0
            return

        self._missed_heartbeats += 1
        if self._missed_heartbeats >= int(self._policy("max_missed_heartbeats", 3)):
            # try switching
            target = self.secondary if self.active.name == self.primary.name else self.primary
            self._switch_to(target, f"missed_heartbeats={self._missed_heartbeats}")

    def _enforce_stale(self, quote_ts: float) -> None:
        stale_s = _now() - quote_ts
        if stale_s > float(self._policy("max_stale_seconds", 2)):
            target = self.secondary if self.active.name == self.primary.name else self.primary
            self._switch_to(target, f"stale_data={stale_s:.3f}s")

    def _enforce_latency(self, elapsed_ms: float) -> None:
        self._latency_ms = float(elapsed_ms)
        if self._latency_ms > float(self._policy("latency_outage_ms", 1000)):
            target = self.secondary if self.active.name == self.primary.name else self.primary
            self._switch_to(target, f"latency_outage_ms={self._latency_ms:.1f}")

    def health(self) -> FeedHealth:
        ok = True
        reason = "ok"
        # heartbeat check updates counters
        self._check_heartbeat()

        # if too many misses, health is not ok
        if self._missed_heartbeats >= int(self._policy("max_missed_heartbeats", 3)):
            ok = False
            reason = f"missed_heartbeats={self._missed_heartbeats}"

        # if no updates at all
        if self._last_update_ts == 0.0:
            ok = False
            reason = "no_updates_yet"

        return FeedHealth(
            ok=ok,
            reason=reason,
            active_vendor=self.active.name,
            last_update_ts=self._last_update_ts,
            last_heartbeat_ts=self._last_heartbeat_ts,
            latency_ms=self._latency_ms,
            missed_heartbeats=self._missed_heartbeats,
        )

    def get_l1(self, symbol: str) -> QuoteL1:
        self._check_heartbeat()
        start = _now()
        try:
            q = self.active.get_l1(symbol)
        except Exception as e:
            # immediate failover and retry once
            target = self.secondary if self.active.name == self.primary.name else self.primary
            self._switch_to(target, f"exception={type(e).__name__}")
            q = self.active.get_l1(symbol)

        elapsed_ms = (_now() - start) * 1000.0
        self._enforce_latency(elapsed_ms)
        self._enforce_stale(q.ts)

        self._last_update_ts = _now()
        return q


class DataRedundancyManager:
    """
    Owns all feeds (L1/L2/trades/OHLCV/options/corp_actions).
    MVP here wires L1 + health + reconciliation hooks. Extend feed methods later.
    """

    def __init__(self, config_path: str = "config/data_sources.yaml"):
        self.config_path = config_path
        self.cfg = self._load_cfg(config_path)

        self.policy = self.cfg.get("policy", {})
        self.recon = self.cfg.get("reconciliation", {})
        self.feeds_cfg = self.cfg.get("feeds", {})
        self.vendors_cfg = self.cfg.get("vendors", {})

        # Build adapters (MVP: http vendors are just placeholders; use stubs until you wire real SDKs)
        self.adapters: Dict[str, VendorAdapter] = {}
        for name, vcfg in self.vendors_cfg.items():
            kind = vcfg.get("kind", "stub")
            if kind == "stub":
                self.adapters[name] = StubAdapter(name=name)
            else:
                # Keep safe until you intentionally wire live APIs
                self.adapters[name] = StubAdapter(name=name)

        # Build feed wrappers
        self.l1 = self._build_failover_feed("l1")

    def _load_cfg(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _build_failover_feed(self, feed_name: str) -> FailoverFeed:
        fcfg = self.feeds_cfg.get(feed_name, {})
        primary_name = fcfg.get("primary")
        secondary_name = fcfg.get("secondary")

        if not primary_name or not secondary_name:
            raise ValueError(f"Feed '{feed_name}' missing primary/secondary in {self.config_path}")

        primary = self.adapters[primary_name]
        secondary = self.adapters[secondary_name]
        return FailoverFeed(feed_name, primary, secondary, self.policy)

    def can_trade(self) -> Tuple[bool, str]:
        """Hard gate: if required feeds unhealthy => cannot trade."""
        required_l1 = bool(self.feeds_cfg.get("l1", {}).get("required", True))
        if required_l1:
            h = self.l1.health()
            if not h.ok:
                return False, f"data:l1:{h.reason} vendor={h.active_vendor}"
        return True, "data:ok"

    def get_l1(self, symbol: str) -> QuoteL1:
        return self.l1.get_l1(symbol)

    def reconcile_l1(self, symbol: str) -> Dict[str, Any]:
        """Compare primary vs secondary (even if one is active)."""
        p = self.l1.primary.get_l1(symbol)
        s = self.l1.secondary.get_l1(symbol)

        p_mid = (p.bid + p.ask) / 2.0
        s_mid = (s.bid + s.ask) / 2.0
        diff_bps = _bps_diff(p_mid, s_mid)

        max_bps = float(self.recon.get("l1_max_price_diff_bps", 10))
        ok = diff_bps <= max_bps

        out = {
            "symbol": symbol,
            "primary": self.l1.primary.name,
            "secondary": self.l1.secondary.name,
            "primary_mid": p_mid,
            "secondary_mid": s_mid,
            "diff_bps": diff_bps,
            "ok": ok,
        }

        if self.recon.get("log_discrepancies", True) and not ok:
            log.warning("RECON L1 mismatch %s", json.dumps(out, default=str))

        return out
