from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional, Tuple

@dataclass(frozen=True)
class Bar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

@dataclass
class BacktestConfig:
    slippage_bps: float = 1.0
    commission_per_share: float = 0.0
    borrow_fee_annual: float = 0.0
    periods_per_year: int = 252

@dataclass
class BacktestResult:
    timestamps: List[datetime]
    returns: List[float]
    slippage_bps_realized: List[float]
    start_ts: Optional[datetime]
    end_ts: Optional[datetime]

SignalFunc = Callable[[List[Bar]], List[int]]
# returns target position per bar: -1, 0, +1

def run_simple_backtest(
    bars: List[Bar],
    signal_fn: SignalFunc,
    cfg: BacktestConfig,
) -> BacktestResult:
    """
    Simple, auditable backtest:
    - signal_fn returns target position per bar (-1/0/+1)
    - fills assumed at close with slippage applied
    - equity is normalized; we output per-bar returns
    """
    if not bars:
        return BacktestResult([], [], [], None, None)

    targets = signal_fn(bars)
    if len(targets) != len(bars):
        raise ValueError("signal_fn must return one target per bar")

    pos = 0
    eq = 1.0
    rets: List[float] = []
    slip_real: List[float] = []
    timestamps: List[datetime] = []

    # slippage model: when we change position, we pay slippage once on entry
    # (kept simple; refine later if you want microstructure detail)
    slip = float(cfg.slippage_bps) / 10000.0

    for i in range(1, len(bars)):
        prev = bars[i - 1]
        cur = bars[i]
        target = int(targets[i])

        # if position changes, apply slippage “hit”
        if target != pos:
            # approximate realized slippage bps as configured (could be dynamic later)
            slip_real.append(float(cfg.slippage_bps))
            # apply slippage cost as a negative return impulse
            eq *= (1.0 - slip)
            pos = target
        else:
            slip_real.append(0.0)

        # PnL from holding pos from prev close to cur close
        px0 = prev.close
        px1 = cur.close
        if px0 <= 0:
            rets.append(0.0)
        else:
            raw_r = (px1 - px0) / px0
            rets.append(float(pos) * raw_r)

        timestamps.append(cur.ts)

    return BacktestResult(
        timestamps=timestamps,
        returns=rets,
        slippage_bps_realized=slip_real,
        start_ts=bars[0].ts,
        end_ts=bars[-1].ts,
    )
