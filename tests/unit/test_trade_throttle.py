from __future__ import annotations

from datetime import datetime
from pathlib import Path

from Core.trade_throttle import TradeThrottle


def test_daily_limit_and_cooldown(tmp_path: Path):
    cfg = tmp_path / "trade_throttle.yaml"
    state = tmp_path / "trade_throttle_state.json"
    cfg.write_text(
        f"""
version: 1
timezone: "America/New_York"
day_reset_hhmm: "09:30"
state_file: "{state.name}"
urgency:
  allow_urgency_override_max_trades_per_day: false
  min_effective_cooldown_seconds: 0
  cooldown_multiplier_by_tier:
    default: 1.0
    HIGH: 0.5
    CRITICAL: 0.0
regimes:
  default:
    max_trades_per_day: 0
    min_seconds_between_trades: 3600
  DIRECTIONAL_EXPANSION:
    max_trades_per_day: 2
    min_seconds_between_trades: 120
""",
        encoding="utf-8",
    )

    m = TradeThrottle(config_path=cfg)

    t0 = datetime(2025, 12, 19, 10, 0, 0)
    dec = m.can_trade(regime="DIRECTIONAL_EXPANSION", now=t0)
    assert dec.allowed is True

    m.record_trade(regime="DIRECTIONAL_EXPANSION", symbol="SPY", strategy="TEST", now=t0)

    t1 = datetime(2025, 12, 19, 10, 1, 0)
    dec = m.can_trade(regime="DIRECTIONAL_EXPANSION", now=t1)
    assert dec.allowed is False
    assert dec.reason == "cooldown_active"

    dec = m.can_trade(regime="DIRECTIONAL_EXPANSION", urgency="HIGH", now=t1)
    assert dec.allowed is True

    m.record_trade(regime="DIRECTIONAL_EXPANSION", symbol="SPY", strategy="TEST", now=t1)

    t2 = datetime(2025, 12, 19, 11, 0, 0)
    dec = m.can_trade(regime="DIRECTIONAL_EXPANSION", now=t2)
    assert dec.allowed is False
    assert dec.reason == "daily_frequency_limit_reached"

    m2 = TradeThrottle(config_path=cfg)
    dec2 = m2.can_trade(regime="DIRECTIONAL_EXPANSION", now=t2)
    assert dec2.allowed is False
    assert dec2.reason == "daily_frequency_limit_reached"


def test_day_rollover_at_market_open(tmp_path: Path):
    cfg = tmp_path / "trade_throttle.yaml"
    state = tmp_path / "trade_throttle_state.json"
    cfg.write_text(
        f"""
version: 1
timezone: "America/New_York"
day_reset_hhmm: "09:30"
state_file: "{state.name}"
regimes:
  default:
    max_trades_per_day: 1
    min_seconds_between_trades: 0
""",
        encoding="utf-8",
    )

    m = TradeThrottle(config_path=cfg)

    t_pre = datetime(2025, 12, 19, 8, 0, 0)
    assert m.can_trade(regime="ANY", now=t_pre).allowed is True
    m.record_trade(regime="ANY", now=t_pre)

    t_pre2 = datetime(2025, 12, 19, 9, 0, 0)
    assert m.can_trade(regime="ANY", now=t_pre2).allowed is False

    t_post = datetime(2025, 12, 19, 10, 0, 0)
    assert m.can_trade(regime="ANY", now=t_post).allowed is True
