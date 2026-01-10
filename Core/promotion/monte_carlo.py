from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import random
from typing import List, Tuple

from .metrics import equity_curve_from_returns, max_drawdown, monthly_returns, percentile

@dataclass
class MonteCarloConfig:
    paths: int = 10000
    block_size_days: int = 5
    ruin_floor_nav: float = 0.50
    monthly_tail_alpha: float = 0.05  # 5th percentile

@dataclass
class MonteCarloResult:
    paths: int
    sim_max_drawdown_p95: float
    prob_ruin: float
    worst_case_monthly_return_95: float  # “worst-case at 95% confidence” => 5th percentile

def _block_bootstrap(returns: List[float], n: int, block: int) -> List[float]:
    if not returns:
        return [0.0] * n
    out: List[float] = []
    L = len(returns)
    block = max(1, int(block))
    while len(out) < n:
        start = random.randint(0, max(0, L - block))
        out.extend(returns[start:start + block])
    return out[:n]

def run_monte_carlo(
    timestamps: List[datetime],
    base_returns: List[float],
    cfg: MonteCarloConfig,
) -> MonteCarloResult:
    if not base_returns or len(base_returns) < 10:
        return MonteCarloResult(cfg.paths, 0.0, 0.0, 0.0)

    n = len(base_returns)
    mdds: List[float] = []
    ruins = 0
    all_monthly: List[float] = []

    for _ in range(int(cfg.paths)):
        sim_rets = _block_bootstrap(base_returns, n=n, block=cfg.block_size_days)
        eq = equity_curve_from_returns(sim_rets, 1.0)
        mdd = max_drawdown(eq)
        mdds.append(mdd)

        if min(eq) <= float(cfg.ruin_floor_nav):
            ruins += 1

        # monthly tail metric from this path
        # reuse the *same timestamps* shape as base (good enough for a tail test)
        mr = monthly_returns(timestamps, sim_rets)
        all_monthly.extend(mr)

    sim_mdd_p95 = percentile(mdds, 0.95)
    prob_ruin = ruins / float(cfg.paths)

    # “95% worst-case monthly return” => 5th percentile
    worst_case_95 = percentile(all_monthly, float(cfg.monthly_tail_alpha))

    return MonteCarloResult(
        paths=int(cfg.paths),
        sim_max_drawdown_p95=float(sim_mdd_p95),
        prob_ruin=float(prob_ruin),
        worst_case_monthly_return_95=float(worst_case_95),
    )
