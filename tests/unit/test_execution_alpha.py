from __future__ import annotations

import os
from pathlib import Path

from Core.execution_alpha import ExecutionAlpha
from Core.slippage_tracker import SlippageTracker


def _cfg_path() -> str:
    here = Path(__file__).resolve().parents[2]  # BotTrader/
    return str(here / "Config" / "execution_alpha.yaml")


def test_direct_small_order():
    ea = ExecutionAlpha(_cfg_path())
    quote = {"bid": 99.99, "ask": 100.01, "last": 100.0, "mid": 100.0}
    plan = ea.build_plan("SPY", "BUY", 50, quote, meta={"avg_minute_volume": 20000, "volatility": 0.01})
    assert plan.method == "DIRECT"
    assert plan.order_type in ("MARKETABLE_LIMIT", "LIMIT")
    assert plan.qty == 50


def test_large_order_selects_algo():
    ea = ExecutionAlpha(_cfg_path())
    quote = {"bid": 99.90, "ask": 100.10, "last": 100.0, "mid": 100.0}
    plan = ea.build_plan("SPY", "BUY", 5000, quote, meta={"avg_minute_volume": 20000, "volatility": 0.02})
    assert plan.method in ("TWAP", "POV", "VWAP", "ICEBERG")
    assert plan.qty == 5000
    if plan.method in ("TWAP", "POV", "VWAP", "ICEBERG"):
        # should have children for these methods
        assert len(plan.children) > 0


def test_wide_spread_goes_passive_limit():
    ea = ExecutionAlpha(_cfg_path())
    # Very wide spread relative to mid
    quote = {"bid": 99.0, "ask": 101.0, "last": 100.0, "mid": 100.0}
    plan = ea.build_plan("SPY", "BUY", 100, quote, meta={"avg_minute_volume": 20000, "volatility": 0.01})
    assert plan.order_type == "LIMIT"


def test_slippage_kill_switch_severe_trade(tmp_path: Path):
    state = tmp_path / "slip_state.json"
    events = tmp_path / "slip_events.jsonl"

    st = SlippageTracker(
        state_path=state,
        events_path=events,
        max_acceptable_slippage_bps=5.0,
        severe_multiplier=2.0,
        warn_multiplier=1.5,
        hourly_slippage_limit_usd=999999.0,
        daily_slippage_limit_usd=999999.0,
        equity_slippage_limit_pct=0.999,
    )

    # BUY: if fill is much higher than expected, slippage is positive (bad)
    res = st.record_fill(
        symbol="SPY",
        side="BUY",
        qty=100,
        expected_price=100.0,
        fill_price=100.2,  # +20 bps
        account_equity=100000.0,
    )
    assert res.paused is True
    assert st.is_paused() is True
