from pathlib import Path

import pytest

from Core.stops import StopModule, StopInputs


def test_regime_multiplier_widens(tmp_path: Path):
    cfg = tmp_path / "stops.yaml"
    cfg.write_text(
        """
version: 1
base:
  method: PCT
  stop_pct: 0.01
  min_stop_pct: 0.001
  max_stop_pct: 0.05
regime_multipliers:
  RISK_ON: 1.00
  RISK_OFF: 1.50
  OUTAGE: 0.00
  UNKNOWN: 1.10
liquidity:
  enabled: false
confidence:
  enabled: false
max_loss:
  enabled: false
""",
        encoding="utf-8",
    )

    m = StopModule(cfg)

    r_on = m.compute(StopInputs(
        symbol="AAPL",
        side="BUY",
        entry_price=100.0,
        regime="RISK_ON",
        strategy_id="OPENING_CONTINUATION",
    ))
    r_off = m.compute(StopInputs(
        symbol="AAPL",
        side="BUY",
        entry_price=100.0,
        regime="RISK_OFF",
        strategy_id="OPENING_CONTINUATION",
    ))

    assert r_on.blocked is False
    assert r_off.blocked is False
    assert r_off.stop_distance_usd > r_on.stop_distance_usd


def test_outage_blocks(tmp_path: Path):
    cfg = tmp_path / "stops.yaml"
    cfg.write_text(
        """
version: 1
base:
  method: PCT
  stop_pct: 0.01
  min_stop_pct: 0.001
  max_stop_pct: 0.05
regime_multipliers:
  OUTAGE: 0.00
  UNKNOWN: 1.0
liquidity:
  enabled: false
confidence:
  enabled: false
max_loss:
  enabled: false
""",
        encoding="utf-8",
    )

    m = StopModule(cfg)
    res = m.compute(StopInputs(
        symbol="SPY",
        side="BUY",
        entry_price=100.0,
        regime="OUTAGE",
        strategy_id="X",
    ))

    assert res.blocked is True
    assert "regime" in res.reason.lower()


def test_liquidity_widens_and_buffers(tmp_path: Path):
    cfg = tmp_path / "stops.yaml"
    cfg.write_text(
        """
version: 1
base:
  method: PCT
  stop_pct: 0.01
  min_stop_pct: 0.001
  max_stop_pct: 0.05
regime_multipliers:
  UNKNOWN: 1.0
liquidity:
  enabled: true
  widen_threshold_pct: 0.0010
  widen_slope: 1.0
  max_widen_mult: 2.0
  block_if_spread_too_wide: false
  max_spread_pct: 0.05
  min_buffer_bps: 2.0
  buffer_bps_per_spread_bps: 1.0
  max_buffer_bps: 20.0
confidence:
  enabled: false
max_loss:
  enabled: false
""",
        encoding="utf-8",
    )

    m = StopModule(cfg)

    tight = m.compute(StopInputs(
        symbol="TSLA",
        side="BUY",
        entry_price=100.0,
        regime="UNKNOWN",
        strategy_id="X",
        bid=99.99,
        ask=100.01,  # ~2 bps
    ))
    wide = m.compute(StopInputs(
        symbol="TSLA",
        side="BUY",
        entry_price=100.0,
        regime="UNKNOWN",
        strategy_id="X",
        bid=99.50,
        ask=100.50,  # ~100 bps
    ))

    assert tight.blocked is False
    assert wide.blocked is False
    assert wide.stop_distance_usd > tight.stop_distance_usd
    assert wide.buffer_usd >= tight.buffer_usd


def test_max_loss_caps_qty(tmp_path: Path):
    cfg = tmp_path / "stops.yaml"
    cfg.write_text(
        """
version: 1
base:
  method: PCT
  stop_pct: 0.02
  min_stop_pct: 0.001
  max_stop_pct: 0.05
regime_multipliers:
  UNKNOWN: 1.0
liquidity:
  enabled: false
confidence:
  enabled: false
max_loss:
  enabled: true
  risk_per_trade_pct: 0.001  # 0.10%
  max_risk_usd: 50
  regime_multipliers:
    UNKNOWN: 1.0
""",
        encoding="utf-8",
    )

    m = StopModule(cfg)

    res = m.compute(StopInputs(
        symbol="SPY",
        side="BUY",
        entry_price=100.0,
        regime="UNKNOWN",
        strategy_id="X",
        equity_usd=100000.0,
        qty=999,
    ))

    assert res.blocked is False
    assert res.max_loss_usd == 50
    assert res.qty_capped_to is not None
    assert res.qty_capped_to < 999
