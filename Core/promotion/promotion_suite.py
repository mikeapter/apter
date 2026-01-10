from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import importlib.util
import sys
import time

import yaml

from .pathing import config_dir, strategies_dir
from .backtest_engine import BacktestConfig, Bar, run_simple_backtest
from .metrics import annualized_sharpe, equity_curve_from_returns, max_drawdown
from .walk_forward import WalkForwardConfig, run_walk_forward
from .monte_carlo import MonteCarloConfig, run_monte_carlo


@dataclass
class PromotionSuiteResult:
    metrics: Dict[str, Any]
    passed: bool
    reasons: List[str]


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML must be a mapping at top-level: {path}")
    return data


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _overlaps(a0: datetime, a1: datetime, b0: datetime, b1: datetime) -> bool:
    return (a0 <= b1) and (b0 <= a1)


def _import_adapter(adapter_path: Path, strategy_id: str):
    """
    Robust adapter loader that avoids Python module caching.
    Each run uses a unique module name so edits to backtest_adapter.py take effect immediately.
    """
    unique_name = f"strategy_backtest_adapter_{strategy_id}_{int(time.time()*1000)}"

    spec = importlib.util.spec_from_file_location(unique_name, str(adapter_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load adapter from {adapter_path}")

    mod = importlib.util.module_from_spec(spec)
    # Ensure no stale caching under this unique name
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def run_promotion_suite(repo_root: Path, strategy_id: str) -> PromotionSuiteResult:
    cfg_path = config_dir(repo_root) / "promotion_gates.yaml"
    cfg = _load_yaml(cfg_path)

    bt_cfg = BacktestConfig(
        slippage_bps=float(cfg["backtest"]["costs"]["slippage_bps"]),
        commission_per_share=float(cfg["backtest"]["costs"]["commission_per_share"]),
        borrow_fee_annual=float(cfg["backtest"]["costs"]["borrow_fee_annual"]),
        periods_per_year=int(cfg["backtest"].get("periods_per_year", 252)),
    )

    wf_cfg = WalkForwardConfig(
        train_years=int(cfg["walk_forward"]["train_years"]),
        test_months=int(cfg["walk_forward"]["test_months"]),
        overlap=bool(cfg["walk_forward"].get("overlap", True)),
    )

    mc_cfg = MonteCarloConfig(
        paths=int(cfg["monte_carlo"]["paths"]),
        block_size_days=int(cfg["monte_carlo"]["block_size_days"]),
        ruin_floor_nav=float(cfg["monte_carlo"]["ruin_floor_nav"]),
        monthly_tail_alpha=float(cfg["monte_carlo"].get("monthly_tail_alpha", 0.05)),
    )

    strat_dir = strategies_dir(repo_root) / strategy_id
    adapter_path = strat_dir / "backtest_adapter.py"
    if not adapter_path.exists():
        raise FileNotFoundError(f"Missing strategy adapter: {adapter_path}")

    adapter = _import_adapter(adapter_path, strategy_id)

    # --- Validate required adapter API ---
    for fn in ("fit", "signal"):
        if not hasattr(adapter, fn) or not callable(getattr(adapter, fn)):
            raise AttributeError(f"Strategy adapter missing required function: {fn}()")

    # Accept either load_bars() or load_bars() (some earlier versions used different name)
    bars_fn = None
    if hasattr(adapter, "load_bars") and callable(getattr(adapter, "load_bars")):
        bars_fn = getattr(adapter, "load_bars")
    elif hasattr(adapter, "load_bars") and callable(getattr(adapter, "load_bars")):
        bars_fn = getattr(adapter, "load_bars")

    if bars_fn is None:
        raise AttributeError("Strategy adapter missing required function: load_bars()")

    bars: List[Bar] = bars_fn()

    # -----------------------
    # Backtest
    # -----------------------
    bt_res = run_simple_backtest(
        bars,
        signal_fn=lambda bs: adapter.signal(bs, adapter.fit(bs)),
        cfg=bt_cfg,
    )
    bt_sharpe = annualized_sharpe(bt_res.returns, bt_cfg.periods_per_year)
    bt_eq = equity_curve_from_returns(bt_res.returns, 1.0)
    bt_mdd = max_drawdown(bt_eq)

    # Backtest span checks
    start = bt_res.start_ts
    end = bt_res.end_ts
    backtest_years = 0.0
    includes_crisis = False
    if start and end:
        backtest_years = (end - start).days / 365.25
        for w in cfg["backtest"]["crisis_periods"]:
            b0 = _parse_dt(w["start"])
            b1 = _parse_dt(w["end"])
            if _overlaps(start, end, b0, b1):
                includes_crisis = True
                break

    # Slippage variation ratio (approx)
    expected_slip = float(cfg["backtest"]["costs"]["slippage_bps"])
    realized_abs = [abs(x) for x in bt_res.slippage_bps_realized if x != 0.0]
    realized_mean = (sum(realized_abs) / len(realized_abs)) if realized_abs else 0.0
    slip_var_ratio = (realized_mean / expected_slip) if expected_slip > 0 else 0.0

    # -----------------------
    # Walk-forward
    # -----------------------
    wf_res = run_walk_forward(
        bars=bars,
        fit_fn=lambda train_bars: adapter.fit(train_bars),
        signal_fn=lambda bs, p: adapter.signal(bs, p),
        bt_cfg=bt_cfg,
        wf_cfg=wf_cfg,
    )

    # -----------------------
    # Monte Carlo
    # -----------------------
    mc_res = run_monte_carlo(
        timestamps=bt_res.timestamps,
        base_returns=bt_res.returns,
        cfg=mc_cfg,
    )

    metrics: Dict[str, Any] = {
        "backtest_sharpe": float(bt_sharpe),
        "backtest_max_drawdown": float(bt_mdd),
        "backtest_years": float(backtest_years),
        "backtest_includes_crisis": bool(includes_crisis),
        "backtest_slippage_variation_ratio": float(slip_var_ratio),

        "walkforward_oos_sharpe": float(wf_res.out_of_sample_sharpe),
        "walkforward_oos_over_is_ratio": float(wf_res.oos_over_is_ratio),
        "walkforward_oos_max_drawdown": float(wf_res.out_of_sample_max_drawdown),

        "mc_paths": int(mc_res.paths),
        "mc_sim_max_drawdown": float(mc_res.sim_max_drawdown_p95),
        "mc_prob_ruin": float(mc_res.prob_ruin),
        "mc_worst_case_monthly_return_p95": float(mc_res.worst_case_monthly_return_95),
    }

    # -----------------------
    # Promotion gates (STRICT)
    # -----------------------
    reasons: List[str] = []

    min_years = float(cfg["backtest"]["min_years"])
    if backtest_years < min_years:
        reasons.append(f"Backtest horizon too short: {backtest_years:.2f}y < {min_years:.2f}y")

    if not includes_crisis:
        reasons.append("Backtest does not include a required crisis window (e.g., 2008 or 2020).")

    max_slip_ratio = float(cfg["backtest"]["slippage_variation_max_ratio"])
    if slip_var_ratio > max_slip_ratio:
        reasons.append(f"Slippage variation ratio too high: {slip_var_ratio:.2f} > {max_slip_ratio:.2f}")

    min_ratio = float(cfg["walk_forward"]["min_oos_over_is_ratio"])
    if wf_res.oos_over_is_ratio < min_ratio:
        reasons.append(
            f"Walk-forward OOS/IS ratio too low: {wf_res.oos_over_is_ratio:.2f} < {min_ratio:.2f}"
        )

    passed = (len(reasons) == 0)
    return PromotionSuiteResult(metrics=metrics, passed=passed, reasons=reasons)


def write_metrics_yaml(repo_root: Path, strategy_id: str, metrics: Dict[str, Any]) -> Path:
    strat_dir = strategies_dir(repo_root) / strategy_id
    evidence_dir = strat_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    out = evidence_dir / "metrics.yaml"
    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(metrics, f, sort_keys=False)
    return out
