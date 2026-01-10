from pathlib import Path

import pytest

from Core.position_sizing import PositionSizer, SizeInputs


def test_outage_blocks(tmp_path: Path):
    cfg = tmp_path / "position_sizing.yaml"
    cfg.write_text(
        """
version: 1
base: {risk_per_trade_pct: 0.01, min_stop_distance_pct: 0.01, qty_step: 1}
regime_multipliers: {OUTAGE: 0.0, RISK_ON: 1.0, UNKNOWN: 0.0}
confidence: {enabled: true, min_conf: 0.2, max_conf: 0.8, floor_mult: 0.5, ceil_mult: 1.25}
clamps: {min_qty: 1, max_qty: 9999, min_notional_usd: 0, max_notional_usd: 1e9, max_risk_usd: 1e9}
""",
        encoding="utf-8",
    )

    sizer = PositionSizer(cfg)
    res = sizer.size(SizeInputs(
        equity_usd=100000,
        price=100,
        stop_distance_usd=2,
        regime="OUTAGE",
        strategy_id="OPENING_CONTINUATION",
        confidence=0.9
    ))
    assert res.blocked is True
    assert res.qty == 0


def test_risk_off_reduces_size(tmp_path: Path):
    cfg = tmp_path / "position_sizing.yaml"
    cfg.write_text(
        """
version: 1
base: {risk_per_trade_pct: 0.01, min_stop_distance_pct: 0.01, qty_step: 1}
regime_multipliers: {RISK_ON: 1.0, RISK_OFF: 0.5, UNKNOWN: 0.0}
confidence: {enabled: false}
clamps: {min_qty: 1, max_qty: 999999, min_notional_usd: 0, max_notional_usd: 1e9, max_risk_usd: 1e9}
""",
        encoding="utf-8",
    )

    sizer = PositionSizer(cfg)

    on = sizer.size(SizeInputs(
        equity_usd=100000, price=100, stop_distance_usd=2,
        regime="RISK_ON", strategy_id="X", confidence=None
    ))
    off = sizer.size(SizeInputs(
        equity_usd=100000, price=100, stop_distance_usd=2,
        regime="RISK_OFF", strategy_id="X", confidence=None
    ))

    assert off.qty <= on.qty
    assert off.qty == pytest.approx(on.qty * 0.5, rel=0.05)
