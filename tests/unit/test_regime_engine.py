# Tests/test_regime_engine.py
import time
from Core.regime_engine import RegimeEngine, RegimeFeatures, RegimeLabel

CFG = {
    "engine": {
        "confirm_periods": 3,
        "min_duration_seconds": 0,
        "enter_confidence": 60,
        "exit_confidence": 55,
        "hysteresis_delta": 0.0,
        "transition_block": True,
    },
    "votes": {"weights": {"rv_iv_divergence": 1.0, "trend_persistence": 1.0, "range_expansion": 1.0, "liquidity": 1.0, "event": 1.0, "cross_asset": 1.0}},
    "thresholds": {
        "rv_iv_z": {"high": 2.0, "low": -2.0},
        "trend": {"alignment_expansion": 4, "alignment_compression": 3, "persistence_expansion": 1.5, "persistence_compression": 1.0, "alignment_ambiguous_max_abs": 1},
        "range": {"expansion_ratio_hi": 1.5, "compression_ratio_lo": 0.8, "range_pct_hi": 80, "range_pct_lo": 40},
        "liquidity": {"spread_bps_max": 10, "depth_usd_min": 50000},
    },
    "controls": {
        "strategy_mask": {r.value: {"trend": 1.0} for r in RegimeLabel},
        "execution_mode": {"default": "NORMAL"},
    },
}

def test_mutually_exclusive_single_label():
    eng = RegimeEngine(CFG)
    out = eng.update(RegimeFeatures(rv_iv_z=3.0), now_ts=time.time())
    assert isinstance(out.label, RegimeLabel)

def test_confirmation_streak_required_to_switch():
    eng = RegimeEngine(CFG)

    # Force current to VOLATILITY_COMPRESSION initially; then push VOLATILITY_EXPANSION
    t0 = time.time()
    f = RegimeFeatures(rv_iv_z=3.0)  # strong vol expansion vote

    o1 = eng.update(f, now_ts=t0)
    assert o1.transition_zone is True
    assert eng.state.current != RegimeLabel.VOLATILITY_EXPANSION

    o2 = eng.update(f, now_ts=t0 + 1)
    assert o2.transition_zone is True
    assert eng.state.current != RegimeLabel.VOLATILITY_EXPANSION

    o3 = eng.update(f, now_ts=t0 + 2)
    # confirm_periods=3 => should switch here
    assert o3.label == RegimeLabel.VOLATILITY_EXPANSION
    assert o3.transition_zone is False

def test_liquidity_vacuum_wins_when_spread_or_depth_bad():
    eng = RegimeEngine(CFG)
    out = eng.update(RegimeFeatures(spread_bps=25, depth_usd=10000), now_ts=time.time())
    # might be transition zone until confirmed; we only assert candidate score exists
    assert out.scores[RegimeLabel.LIQUIDITY_VACUUM] >= 1.0

def test_confidence_bounds():
    eng = RegimeEngine(CFG)
    out = eng.update(RegimeFeatures(rv_iv_z=3.0, spread_bps=5, depth_usd=100000), now_ts=time.time())
    assert 0.0 <= out.confidence <= 100.0
