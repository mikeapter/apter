# src/alpha/trend_persistence.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence, Tuple

import pandas as pd


# --- Strategy doc defaults ---
DEFAULT_TIMEFRAMES: Tuple[str, ...] = ("1m", "5m", "15m", "1h", "4h", "1d")
DEFAULT_WEIGHTS: Tuple[float, ...] = (0.05, 0.10, 0.15, 0.25, 0.25, 0.20)

# Regime factor table (from Strategy doc's regime multipliers section)
REGIME_FACTOR_TABLE: Dict[str, float] = {
    "DIRECTIONAL_EXPANSION": 1.0,
    "DIRECTIONAL_COMPRESSION": 0.6,
    "VOLATILITY_EXPANSION": 0.5,
    "VOLATILITY_COMPRESSION": 0.8,
    "LIQUIDITY_VACUUM": 0.0,
    "EVENT_DOMINATED": 0.0,
}


@dataclass(frozen=True)
class TrendPersistenceOutput:
    """
    Output contract (matches Strategy doc intent)

    - trend_direction: {-1, 0, +1}
    - persistence_score: [0..10] magnitude (unsigned)
    - label: {"weak","neutral","strong"} based on thresholds
    """
    trend_direction: int
    persistence_score: float
    label: str

    # Diagnostics (useful for logging / debugging)
    trend_alignment: float
    per_tf_strength: Dict[str, float]
    per_tf_sign: Dict[str, int]
    regime_factor: float
    confidence_factor: float


def _sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _ema(series: pd.Series, span: int) -> pd.Series:
    # EMA via pandas EWM (adjust=False is the standard trading EMA)
    return series.ewm(span=int(span), adjust=False).mean()


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    # Classic True Range, smoothed as an EMA (common ATR implementation).
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    prev_close = close.shift(1)
    tr1 = (high - low).abs()
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    return _ema(true_range, span=int(period))


def _confidence_factor(regime_confidence: Optional[float]) -> float:
    # Strategy doc confidence adjustment: <60 => 0.7, >85 => 1.1 else 1.0
    if regime_confidence is None:
        return 1.0
    c = float(regime_confidence)
    if c < 60.0:
        return 0.7
    if c > 85.0:
        return 1.1
    return 1.0


def compute_trend_persistence(
    ohlcv_by_tf: Mapping[str, pd.DataFrame],
    *,
    regime: str,
    regime_confidence: Optional[float] = None,
    timeframes: Sequence[str] = DEFAULT_TIMEFRAMES,
    weights: Sequence[float] = DEFAULT_WEIGHTS,
    ema_fast_period: int = 20,
    atr_period: int = 14,
    score_scale_to_10: float = 10.0,
    weak_threshold: float = 1.0,
    strong_threshold: float = 2.5,
    use_regime_factor_table: bool = True,
    use_regime_confidence_adjustment: bool = True,
) -> TrendPersistenceOutput:
    """
    STEP 14 — Regime-conditioned Trend Persistence (Structural Alpha)

    Inputs / timeframes:
      - OHLCV per timeframe: 1m, 5m, 15m, 1h, 4h, 1d (Strategy doc default)
      - regime label + optional regime confidence

    Exact calculations (Strategy doc):
      1) For each timeframe tf:
         trend_strength[tf] = (close_last - EMA_fast_last) / ATR_last

      2) Convert each trend_strength into a sign:
         sgn_tf = sign(trend_strength[tf]) ∈ {-1, 0, +1}

      3) Trend alignment (weighted sum across timeframes):
         trend_alignment = Σ w_tf * sgn_tf
         (weights sum to 1 => trend_alignment ∈ [-1, +1])

      4) Persistence score (magnitude in 0..10):
         signed_score = trend_alignment * score_scale_to_10
         signed_score *= (1 + regime_factor)        (regime-conditioned)
         signed_score *= confidence_factor          (optional)
         persistence_score = clamp(|signed_score|, 0, 10)

      5) Thresholds (Strategy doc):
         strong if persistence_score > 2.5
         weak   if persistence_score < 1.0
         neutral otherwise

    Return signature:
      TrendPersistenceOutput(trend_direction, persistence_score, label, ...diagnostics)

    Notes:
      - In LIQUIDITY_VACUUM and EVENT_DOMINATED, we force the output to zero
        (regime_factor_table value = 0.0).
    """
    if len(timeframes) != len(weights):
        raise ValueError("timeframes and weights must have the same length")

    regime_u = (regime or "UNKNOWN").upper()
    regime_factor = REGIME_FACTOR_TABLE.get(regime_u, 1.0) if use_regime_factor_table else 1.0

    conf_factor = _confidence_factor(regime_confidence) if use_regime_confidence_adjustment else 1.0

    # Force OFF in unsafe regimes
    if use_regime_factor_table and regime_factor <= 0.0:
        return TrendPersistenceOutput(
            trend_direction=0,
            persistence_score=0.0,
            label="weak",
            trend_alignment=0.0,
            per_tf_strength={},
            per_tf_sign={},
            regime_factor=float(regime_factor),
            confidence_factor=float(conf_factor),
        )

    per_tf_strength: Dict[str, float] = {}
    per_tf_sign: Dict[str, int] = {}
    used_weight_sum = 0.0
    alignment = 0.0

    for tf, w in zip(timeframes, weights):
        df = ohlcv_by_tf.get(tf)
        if df is None or len(df) < max(ema_fast_period, atr_period, 5):
            continue
        if not {"high", "low", "close"}.issubset(set(df.columns)):
            continue

        close = df["close"].astype(float)
        ema_fast = _ema(close, span=ema_fast_period)
        atr = _atr(df, period=atr_period)

        c_last = float(close.iloc[-1])
        ema_last = float(ema_fast.iloc[-1])
        atr_last = float(atr.iloc[-1]) if float(atr.iloc[-1]) != 0.0 else 1e-9

        strength = (c_last - ema_last) / atr_last
        sgn = _sign(strength)

        per_tf_strength[str(tf)] = float(strength)
        per_tf_sign[str(tf)] = int(sgn)

        alignment += float(w) * float(sgn)
        used_weight_sum += float(w)

    if used_weight_sum <= 0.0:
        # Not enough data to compute
        return TrendPersistenceOutput(
            trend_direction=0,
            persistence_score=0.0,
            label="weak",
            trend_alignment=0.0,
            per_tf_strength={},
            per_tf_sign={},
            regime_factor=float(regime_factor),
            confidence_factor=float(conf_factor),
        )

    # If we skipped any TFs, normalize by the weights actually used.
    alignment = alignment / used_weight_sum
    alignment = _clamp(alignment, -1.0, 1.0)

    signed_score = alignment * float(score_scale_to_10)
    signed_score *= (1.0 + float(regime_factor))
    signed_score *= float(conf_factor)

    signed_score = _clamp(signed_score, -10.0, 10.0)

    persistence_score = abs(float(signed_score))

    # Threshold labels + direction rule
    if persistence_score < float(weak_threshold):
        label = "weak"
        trend_direction = 0
    elif persistence_score > float(strong_threshold):
        label = "strong"
        trend_direction = _sign(signed_score)
    else:
        label = "neutral"
        trend_direction = _sign(signed_score)

    return TrendPersistenceOutput(
        trend_direction=int(trend_direction),
        persistence_score=float(_clamp(persistence_score, 0.0, 10.0)),
        label=label,
        trend_alignment=float(alignment),
        per_tf_strength=per_tf_strength,
        per_tf_sign=per_tf_sign,
        regime_factor=float(regime_factor),
        confidence_factor=float(conf_factor),
    )
