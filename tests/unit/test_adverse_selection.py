from __future__ import annotations

import time
from pathlib import Path

from Core.adverse_selection import AdverseSelectionMonitor


def test_adverse_selection_triggers_pause_passive(tmp_path: Path):
    # Use real config from Config/ but isolate state/events in tmp_path
    here = Path(__file__).resolve().parents[2]  # BotTrader/
    cfg = here / "Config" / "adverse_selection.yaml"

    state = tmp_path / "adverse_state.json"
    events = tmp_path / "adverse_events.jsonl"

    mon = AdverseSelectionMonitor(config_path=cfg, state_path=state, events_path=events)

    # Baseline: no history => should allow passive
    d0 = mon.pre_trade(symbol="SPY", side="BUY", quote={"bid": 99.99, "ask": 100.01, "mid": 100.0}, meta={})
    assert d0.allow_passive is True

    # Record a suspicious fill: fast + adverse move against us
    submit_ts = time.time()
    fill_ts = submit_ts + 0.20  # fast fill
    fill_price = 100.00
    post_mid = 99.92  # 8 bps against for a BUY

    r = mon.record_fill(
        symbol="SPY",
        side="BUY",
        order_type="LIMIT",
        submit_ts=submit_ts,
        fill_ts=fill_ts,
        fill_price=fill_price,
        post_fill_mid=post_mid,
        latency_ms=40.0,
        extra={"test": True},
    )

    assert r.detected is True

    # Immediately after: should no longer allow passive (aggressive-only or pause-passive)
    d1 = mon.pre_trade(symbol="SPY", side="BUY", quote={"bid": 99.99, "ask": 100.01, "mid": 100.0}, meta={})
    assert d1.allow_passive is False
    assert d1.force_aggressive_only is True
    assert d1.action in ("AGGRESSIVE_ONLY", "PAUSE_PASSIVE")


def test_latency_high_forces_aggressive_only(tmp_path: Path):
    here = Path(__file__).resolve().parents[2]
    cfg = here / "Config" / "adverse_selection.yaml"

    state = tmp_path / "adverse_state.json"
    events = tmp_path / "adverse_events.jsonl"

    mon = AdverseSelectionMonitor(config_path=cfg, state_path=state, events_path=events)

    d = mon.pre_trade(
        symbol="SPY",
        side="SELL",
        quote={"bid": 99.99, "ask": 100.01, "mid": 100.0},
        meta={"latency_ms": 200.0},
    )
    assert d.allow_passive is False
    assert d.force_aggressive_only is True
    assert d.force_ioc is True
