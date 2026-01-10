from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from typing import Iterable, List, Tuple, Dict

def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0

def _stdev(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return var ** 0.5

def equity_curve_from_returns(returns: List[float], start_equity: float = 1.0) -> List[float]:
    eq = [start_equity]
    for r in returns:
        eq.append(eq[-1] * (1.0 + r))
    return eq

def max_drawdown(equity: List[float]) -> float:
    peak = equity[0] if equity else 1.0
    mdd = 0.0
    for x in equity:
        if x > peak:
            peak = x
        dd = (peak - x) / peak if peak > 0 else 0.0
        if dd > mdd:
            mdd = dd
    return mdd

def annualized_sharpe(returns: List[float], periods_per_year: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    mu = _mean(returns)
    sd = _stdev(returns)
    if sd == 0:
        return 0.0
    return (mu / sd) * sqrt(periods_per_year)

def month_key(ts: datetime) -> str:
    return f"{ts.year:04d}-{ts.month:02d}"

def monthly_returns(timestamps: List[datetime], returns: List[float]) -> List[float]:
    """
    Compounded monthly returns from (timestamp, per-period return).
    Assumes timestamps align with returns.
    """
    if len(timestamps) != len(returns):
        raise ValueError("timestamps and returns must be the same length")

    buckets: Dict[str, float] = {}
    for ts, r in zip(timestamps, returns):
        k = month_key(ts)
        # compound within the month
        buckets[k] = buckets.get(k, 1.0) * (1.0 + r)

    out = []
    for k in sorted(buckets.keys()):
        out.append(buckets[k] - 1.0)
    return out

def percentile(xs: List[float], q: float) -> float:
    """
    q in [0,1]. Simple nearest-rank percentile.
    """
    if not xs:
        return 0.0
    ys = sorted(xs)
    idx = int(round((len(ys) - 1) * q))
    idx = max(0, min(len(ys) - 1, idx))
    return ys[idx]
