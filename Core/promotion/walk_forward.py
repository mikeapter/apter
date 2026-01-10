from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Any

from .backtest_engine import Bar, BacktestConfig, run_simple_backtest
from .metrics import annualized_sharpe, equity_curve_from_returns, max_drawdown


@dataclass
class WalkForwardConfig:
    # These are interpreted in trading-day approximations (stable for daily bars):
    train_years: int = 3
    test_months: int = 6
    overlap: bool = True


@dataclass
class WalkForwardResult:
    in_sample_sharpe: float
    out_of_sample_sharpe: float
    oos_over_is_ratio: float
    out_of_sample_max_drawdown: float
    windows: int


def run_walk_forward(
    bars: List[Bar],
    fit_fn: Callable[[List[Bar]], Any],
    signal_fn: Callable[[List[Bar], Any], List[int]],
    bt_cfg: BacktestConfig,
    wf_cfg: WalkForwardConfig,
) -> WalkForwardResult:
    """
    Walk-forward engine with correct signal-context handling:

    - Fit on TRAIN window.
    - Generate signals on TRAIN for IS stats.
    - Generate signals on (TRAIN + TEST) and take the tail for TEST stats.
      This prevents "lookback > test_len => all zeros" failures.

    If no valid windows, returns zeros (but that should not happen with 2015+ SPY data).
    """
    if not bars or len(bars) < 500:
        return WalkForwardResult(
            in_sample_sharpe=0.0,
            out_of_sample_sharpe=0.0,
            oos_over_is_ratio=0.0,
            out_of_sample_max_drawdown=0.0,
            windows=0,
        )

    # Approximate trading days:
    periods_per_year = int(getattr(bt_cfg, "periods_per_year", 252))
    train_len = int(wf_cfg.train_years * periods_per_year)
    test_len = int(wf_cfg.test_months * 21)  # ~21 trading days per month

    if train_len <= 0 or test_len <= 0:
        raise ValueError("Invalid walk-forward lengths. Check train_years/test_months.")

    # Step size
    step = test_len if wf_cfg.overlap else (train_len + test_len)

    is_returns_all: List[float] = []
    oos_returns_all: List[float] = []
    oos_equity_all: List[float] = [1.0]  # for overall OOS drawdown tracking
    windows = 0

    n = len(bars)
    start = 0

    while True:
        train_start = start
        train_end = train_start + train_len
        test_end = train_end + test_len

        if test_end > n:
            break

        train_bars = bars[train_start:train_end]
        test_bars = bars[train_end:test_end]

        # Fit only on train window (no leakage)
        params = fit_fn(train_bars)

        # --- In-sample backtest (train only) ---
        is_bt = run_simple_backtest(
            train_bars,
            signal_fn=lambda bs: signal_fn(bs, params),
            cfg=bt_cfg,
        )
        is_returns_all.extend(is_bt.returns)

        # --- Out-of-sample backtest (test only) with TRAIN+TEST context ---
        context_bars = train_bars + test_bars
        context_targets = signal_fn(context_bars, params)

        if len(context_targets) != len(context_bars):
            # Hard fail: strategy adapter is invalid
            raise ValueError(
                f"signal_fn returned {len(context_targets)} targets for {len(context_bars)} bars"
            )

        test_targets = context_targets[-len(test_bars):]

        oos_bt = run_simple_backtest(
            test_bars,
            signal_fn=lambda bs, tt=test_targets: tt,
            cfg=bt_cfg,
        )
        oos_returns_all.extend(oos_bt.returns)

        # Track OOS equity for drawdown
        eq = oos_equity_all[-1]
        for r in oos_bt.returns:
            eq *= (1.0 + r)
            oos_equity_all.append(eq)

        windows += 1
        start += step

    if windows == 0 or len(oos_returns_all) == 0 or len(is_returns_all) == 0:
        return WalkForwardResult(
            in_sample_sharpe=0.0,
            out_of_sample_sharpe=0.0,
            oos_over_is_ratio=0.0,
            out_of_sample_max_drawdown=0.0,
            windows=windows,
        )

    is_sharpe = float(annualized_sharpe(is_returns_all, periods_per_year))
    oos_sharpe = float(annualized_sharpe(oos_returns_all, periods_per_year))

    # Ratio gate: OOS / IS (protect against divide-by-zero / negative IS sharpe)
    if is_sharpe <= 0:
        ratio = 0.0
    else:
        ratio = float(oos_sharpe / is_sharpe)

    oos_mdd = float(max_drawdown(oos_equity_all))

    return WalkForwardResult(
        in_sample_sharpe=is_sharpe,
        out_of_sample_sharpe=oos_sharpe,
        oos_over_is_ratio=ratio,
        out_of_sample_max_drawdown=oos_mdd,
        windows=windows,
    )
