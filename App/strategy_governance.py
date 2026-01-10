from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import yaml
except ImportError as e:
    raise SystemExit("Missing dependency: pyyaml. Install with: pip install pyyaml") from e


@dataclass
class CheckResult:
    ok: bool
    stage: str
    reasons: List[str]


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML must be a mapping at top-level: {path}")
    return data


def _find_dir(base: Path, candidates: List[str]) -> Path:
    for name in candidates:
        p = base / name
        if p.exists() and p.is_dir():
            return p
    return base / candidates[0]


class StrategyGovernance:
    def __init__(self, repo_root: Path | None = None) -> None:
        self.root = repo_root or Path(__file__).resolve().parent

        # ✅ Case-safe folder resolution (Windows + Linux friendly)
        self.cfg_dir = _find_dir(self.root, ["config", "Config"])
        self.strats_dir = _find_dir(self.root, ["strategies", "Strategies"])

        self.cfg_path = self.cfg_dir / "strategy_governance.yaml"
        self.registry_path = self.cfg_dir / "strategy_registry.yaml"

        self.cfg = _load_yaml(self.cfg_path)
        self.registry = _load_yaml(self.registry_path)

        self.thresholds = self.cfg.get("thresholds", {})
        self.required_artifacts = self.cfg.get("required_artifacts", {})
        self.stages_order = self.cfg.get("stages_order", [])
        if not self.stages_order:
            raise ValueError("strategy_governance.yaml missing stages_order")

    def list_strategies(self) -> List[Dict[str, Any]]:
        return list(self.registry.get("strategies", []))

    def strategy_dir(self, strategy_id: str) -> Path:
        return self.strats_dir / strategy_id

    def _missing_artifacts(self, strategy_id: str, stage: str) -> List[str]:
        base = self.strategy_dir(strategy_id)
        req = self.required_artifacts.get(stage, [])
        missing: List[str] = []
        for rel in req:
            if not (base / rel).exists():
                missing.append(rel)
        return missing

    def _read_metrics(self, strategy_id: str) -> Dict[str, Any]:
        metrics_path = self.strategy_dir(strategy_id) / "evidence" / "metrics.yaml"
        return _load_yaml(metrics_path)

    def _check_thresholds(self, metrics: Dict[str, Any], stage: str) -> List[str]:
        reasons: List[str] = []
        stage = stage.upper()

        # -----------------------------
        # Backtest thresholds (IPS)
        # -----------------------------
        bt = self.thresholds.get("backtest", {})
        if bt:
            sharpe = metrics.get("backtest_sharpe")
            mdd = metrics.get("backtest_max_drawdown")
            if sharpe is None or mdd is None:
                reasons.append("metrics.yaml missing backtest_sharpe/backtest_max_drawdown")
            else:
                if float(sharpe) < float(bt.get("sharpe_min", 0.0)):
                    reasons.append(f"Backtest Sharpe {sharpe} < {bt.get('sharpe_min')}")
                if float(mdd) > float(bt.get("max_drawdown_max", 1.0)):
                    reasons.append(f"Backtest max drawdown {mdd} > {bt.get('max_drawdown_max')}")

        # Backtest *requirements* (IPS minimum standards)
        yrs = metrics.get("backtest_years")
        if yrs is not None and float(yrs) < 5.0:
            reasons.append(f"Backtest horizon {yrs} < 5.0 years (IPS minimum).")
        crisis = metrics.get("backtest_includes_crisis")
        if crisis is not None and bool(crisis) is False:
            reasons.append("Backtest does not include a crisis period window (IPS requirement).")
        slip_ratio = metrics.get("backtest_slippage_variation_ratio")
        if slip_ratio is not None and float(slip_ratio) > 1.50:
            reasons.append(f"Slippage variation ratio {slip_ratio} > 1.50 (IPS: <50% deviation).")

        # -----------------------------
        # Walk-forward thresholds (IPS)
        # -----------------------------
        wf = self.thresholds.get("walkforward", {})
        if wf:
            oos = metrics.get("walkforward_oos_sharpe")
            if oos is None:
                reasons.append("metrics.yaml missing walkforward_oos_sharpe")
            else:
                if float(oos) < float(wf.get("oos_sharpe_min", 0.0)):
                    reasons.append(f"Walk-forward OOS Sharpe {oos} < {wf.get('oos_sharpe_min')}")

        # IPS model validation: OOS > 60% of IS
        ratio = metrics.get("walkforward_oos_over_is_ratio")
        if ratio is not None and float(ratio) < 0.60:
            reasons.append(f"Walk-forward OOS/IS ratio {ratio} < 0.60 (IPS minimum).")

        # -----------------------------
        # Monte Carlo thresholds (IPS)
        # -----------------------------
        mc = self.thresholds.get("monte_carlo", {})
        if mc:
            missing = [
                k for k in [
                    "mc_paths",
                    "mc_sim_max_drawdown",
                    "mc_prob_ruin",
                    "mc_worst_case_monthly_return_p95",
                ]
                if metrics.get(k) is None
            ]
            if missing:
                reasons.append(f"metrics.yaml missing {', '.join(missing)}")
            else:
                paths = int(metrics["mc_paths"])
                sim_mdd = float(metrics["mc_sim_max_drawdown"])
                ruin = float(metrics["mc_prob_ruin"])
                p95 = float(metrics["mc_worst_case_monthly_return_p95"])

                if paths < int(mc.get("paths_min", 0)):
                    reasons.append(f"MC paths {paths} < {mc.get('paths_min')}")
                if sim_mdd > float(mc.get("sim_max_drawdown_max", 1.0)):
                    reasons.append(f"MC sim max drawdown {sim_mdd} > {mc.get('sim_max_drawdown_max')}")
                if ruin > float(mc.get("prob_ruin_max", 1.0)):
                    reasons.append(f"MC prob ruin {ruin} > {mc.get('prob_ruin_max')}")
                if p95 < float(mc.get("worst_case_monthly_return_p95_min", -1.0)):
                    reasons.append(
                        f"MC 95% worst-case monthly return {p95} < {mc.get('worst_case_monthly_return_p95_min')}"
                    )

        # -----------------------------
        # Pilot days (IPS: shadow testing 10–20 days)
        # -----------------------------
        if stage in ("PILOT", "DEPLOY", "MONITOR"):
            pilot = self.thresholds.get("pilot", {})
            if pilot:
                days = metrics.get("pilot_trading_days")
                if days is None:
                    reasons.append("metrics.yaml missing pilot_trading_days")
                else:
                    if int(days) < int(pilot.get("min_trading_days", 0)):
                        reasons.append(f"Pilot trading days {days} < {pilot.get('min_trading_days')}")

        return reasons

    def _check_vote_majority(self, strategy_id: str) -> List[str]:
        vote_path = self.strategy_dir(strategy_id) / "approvals" / "pmc_vote.yaml"
        data = _load_yaml(vote_path)

        def norm(x: Any) -> str:
            return str(x).strip().lower()

        yes_raw = data.get("yes", 0)
        no_raw = data.get("no", 0)

        try:
            yes = int(yes_raw)
        except Exception:
            yes = 0

        try:
            no = int(no_raw)
        except Exception:
            no = 0

        if yes + no == 0:
            voters = data.get("voters", [])
            if isinstance(voters, list):
                for v in voters:
                    if isinstance(v, dict):
                        vote = norm(v.get("vote", ""))
                        if vote == "yes":
                            yes += 1
                        elif vote == "no":
                            no += 1

        total = yes + no
        if total == 0:
            return ["PMC vote has no counts (check approvals/pmc_vote.yaml yes/no or voters)."]
        if yes <= no:
            return [f"PMC vote failed: yes={yes}, no={no} (majority required)."]
        return []

    def check_strategy(self, strategy_id: str, stage: str) -> CheckResult:
        stage = stage.upper()
        reasons: List[str] = []

        missing = self._missing_artifacts(strategy_id, stage)
        if missing:
            reasons.append(f"Missing required artifacts for {stage}: {', '.join(missing)}")

        if stage in ("TEST", "REVIEW", "VOTE", "PILOT", "DEPLOY", "MONITOR"):
            try:
                metrics = self._read_metrics(strategy_id)
                reasons.extend(self._check_thresholds(metrics, stage))
            except FileNotFoundError:
                reasons.append("Missing evidence/metrics.yaml (required to validate IPS thresholds).")

        if stage in ("VOTE", "PILOT", "DEPLOY", "MONITOR"):
            try:
                reasons.extend(self._check_vote_majority(strategy_id))
            except FileNotFoundError:
                reasons.append("Missing approvals/pmc_vote.yaml (majority required).")

        ok = (len(reasons) == 0)
        return CheckResult(ok=ok, stage=stage, reasons=reasons)

    def can_trade(self, strategy_id: str) -> Tuple[bool, List[str]]:
        rec = next((s for s in self.list_strategies() if s.get("strategy_id") == strategy_id), None)
        if not rec:
            return False, [f"Strategy not found in registry: {strategy_id}"]

        enabled = bool(rec.get("enabled", False))
        stage = str(rec.get("stage", "DESIGN")).upper()

        if not enabled:
            return False, [f"{strategy_id} is not enabled in strategy_registry.yaml"]

        if stage not in ("DEPLOY", "MONITOR"):
            return False, [f"{strategy_id} stage is {stage} (only DEPLOY/MONITOR may trade)."]

        res = self.check_strategy(strategy_id, stage)
        if not res.ok:
            return False, res.reasons

        return True, []

    def print_report(self) -> int:
        strategies = self.list_strategies()
        if not strategies:
            print("No strategies found in strategy_registry.yaml")
            return 1

        exit_code = 0
        for s in strategies:
            sid = s.get("strategy_id")
            stage = str(s.get("stage", "DESIGN")).upper()
            enabled = bool(s.get("enabled", False))

            res = self.check_strategy(sid, stage)
            print(f"\n=== {sid}  stage={stage}  enabled={enabled} ===")
            if res.ok:
                print("PASS ✅")
            else:
                print("FAIL ❌")
                for r in res.reasons:
                    print(f" - {r}")
                exit_code = 2

        return exit_code


if __name__ == "__main__":
    gov = StrategyGovernance()
    raise SystemExit(gov.print_report())
