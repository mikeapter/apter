# tests/test_trend_persistence.py

import pandas as pd

from src.alpha.trend_persistence import compute_trend_persistence


def _make_uptrend_df(n: int = 100) -> pd.DataFrame:
    # monotonic rising close so close > EMA_fast near the end
    close = pd.Series([100 + i * 0.1 for i in range(n)], dtype=float)
    high = close + 0.2
    low = close - 0.2
    open_ = close.shift(1).fillna(close.iloc[0])
    vol = pd.Series([1000] * n, dtype=float)

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": vol}
    )


def _make_downtrend_df(n: int = 100) -> pd.DataFrame:
    close = pd.Series([100 - i * 0.1 for i in range(n)], dtype=float)
    high = close + 0.2
    low = close - 0.2
    open_ = close.shift(1).fillna(close.iloc[0])
    vol = pd.Series([1000] * n, dtype=float)

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": vol}
    )


def test_trend_persistence_uptrend_directional_expansion_positive():
    ohlcv_by_tf = {tf: _make_uptrend_df() for tf in ["1m", "5m", "15m", "1h", "4h", "1d"]}

    res = compute_trend_persistence(
        ohlcv_by_tf,
        regime="DIRECTIONAL_EXPANSION",
        regime_confidence=90,  # should boost slightly
    )
    assert res.trend_direction == 1
    assert 0.0 <= res.persistence_score <= 10.0
    assert res.label in ("neutral", "strong")


def test_trend_persistence_downtrend_directional_expansion_negative():
    ohlcv_by_tf = {tf: _make_downtrend_df() for tf in ["1m", "5m", "15m", "1h", "4h", "1d"]}

    res = compute_trend_persistence(
        ohlcv_by_tf,
        regime="DIRECTIONAL_EXPANSION",
        regime_confidence=90,
    )
    assert res.trend_direction == -1
    assert 0.0 <= res.persistence_score <= 10.0


def test_trend_persistence_liquidity_vacuum_forces_zero():
    ohlcv_by_tf = {tf: _make_uptrend_df() for tf in ["1m", "5m", "15m", "1h", "4h", "1d"]}

    res = compute_trend_persistence(
        ohlcv_by_tf,
        regime="LIQUIDITY_VACUUM",
        regime_confidence=95,
    )
    assert res.trend_direction == 0
    assert res.persistence_score == 0.0
    assert res.label == "weak"
