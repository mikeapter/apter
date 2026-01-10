from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union, List

import yaml


# =========================================================
# STEP 02 — Performance/Risk Guardrails
# - Loads config/performance_risk_guardrails.yaml
# - APPROACH mode: risk_scale = 0.75 unless drawdown is low
# =========================================================


@dataclass
class GuardrailDecision:
    passed: bool
    reason: str = ""
    notes: List[str] = field(default_factory=list)

    # optional outputs for later position sizing
    risk_scale: float = 1.0
    risk_mode: str = "APPROACH"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pass": self.passed,
            "reason": self.reason,
            "notes": self.notes,
            "risk_scale": self.risk_scale,
            "risk_mode": self.risk_mode,
        }


class GuardrailGate:
    """
    Guardrail gate object.
    Use:
        gate = load_guardrail_gate(...)
        decision = gate.evaluate(portfolio_state)
    """

    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg or {}

        limits = self.cfg.get("limits", {}) or {}
        self.max_drawdown = float(limits.get("max_drawdown", 0.25))         # 25%
        self.max_daily_loss = float(limits.get("max_daily_loss", 0.03))     # 3%
        self.max_weekly_loss = float(limits.get("max_weekly_loss", 0.06))   # 6%

        modes = self.cfg.get("modes", {}) or {}

        # APPROACH mode rule you requested:
        # reduce risk to 0.75 unless drawdown is lower (i.e., very small)
        approach = modes.get("APPROACH", {}) or {}
        self.approach_reduce_to = float(approach.get("reduce_risk_to", 0.75))
        self.approach_no_reduce_if_dd_below = float(approach.get("no_reduce_if_drawdown_below", 0.02))  # 2%

        reduce = modes.get("REDUCE", {}) or {}
        self.reduce_risk_to = float(reduce.get("risk_scale", 0.50))

        pause = modes.get("PAUSE", {}) or {}
        self.pause_blocks_trading = bool(pause.get("block_trading", True))

    def evaluate(self, portfolio_state: Dict[str, Any]) -> GuardrailDecision:
        ps = portfolio_state or {}
        notes: List[str] = []

        risk_mode = str(ps.get("risk_mode", "APPROACH")).upper().strip()

        # compute drawdown if not provided
        dd = ps.get("current_drawdown", None)
        if dd is None:
            equity = float(ps.get("equity", 0.0))
            peak = float(ps.get("peak_equity", equity if equity > 0 else 0.0))
            if peak > 0:
                dd = max(0.0, (peak - equity) / peak)
            else:
                dd = 0.0
            notes.append("current_drawdown not provided; computed from equity/peak_equity.")
        dd = float(dd)

        daily_pnl_pct = ps.get("daily_pnl_pct", None)
        weekly_pnl_pct = ps.get("weekly_pnl_pct", None)

        # -----------------------------
        # Hard stops
        # -----------------------------
        if dd >= self.max_drawdown:
            return GuardrailDecision(
                passed=False,
                reason=f"Max drawdown breached: {dd:.2%} >= {self.max_drawdown:.2%}",
                notes=notes,
                risk_scale=0.0,
                risk_mode=risk_mode,
            )

        if daily_pnl_pct is not None:
            d = float(daily_pnl_pct)
            if d <= -self.max_daily_loss:
                return GuardrailDecision(
                    passed=False,
                    reason=f"Daily loss limit breached: {d:.2%} <= -{self.max_daily_loss:.2%}",
                    notes=notes,
                    risk_scale=0.0,
                    risk_mode=risk_mode,
                )

        if weekly_pnl_pct is not None:
            w = float(weekly_pnl_pct)
            if w <= -self.max_weekly_loss:
                return GuardrailDecision(
                    passed=False,
                    reason=f"Weekly loss limit breached: {w:.2%} <= -{self.max_weekly_loss:.2%}",
                    notes=notes,
                    risk_scale=0.0,
                    risk_mode=risk_mode,
                )

        # -----------------------------
        # Mode-based risk scaling
        # -----------------------------
        if risk_mode == "PAUSE" and self.pause_blocks_trading:
            return GuardrailDecision(
                passed=False,
                reason="Trading paused by risk_mode=PAUSE",
                notes=notes,
                risk_scale=0.0,
                risk_mode=risk_mode,
            )

        risk_scale = 1.0

        if risk_mode == "REDUCE":
            risk_scale = self.reduce_risk_to
            notes.append(f"REDUCE mode active: risk_scale={risk_scale:.2f}")

        elif risk_mode == "APPROACH":
            if dd < self.approach_no_reduce_if_dd_below:
                risk_scale = 1.0
                notes.append(
                    f"APPROACH mode: drawdown {dd:.2%} < {self.approach_no_reduce_if_dd_below:.2%} so no risk reduction."
                )
            else:
                risk_scale = self.approach_reduce_to
                notes.append(
                    f"APPROACH mode: drawdown {dd:.2%} >= {self.approach_no_reduce_if_dd_below:.2%} so risk_scale={risk_scale:.2f}"
                )
        else:
            # Unknown mode: conservative but not a hard stop
            risk_scale = self.approach_reduce_to
            notes.append(f"Unknown risk_mode='{risk_mode}'. Using conservative risk_scale={risk_scale:.2f}")

        return GuardrailDecision(
            passed=True,
            reason="Guardrails OK",
            notes=notes,
            risk_scale=risk_scale,
            risk_mode=risk_mode,
        )


# -------------------------
# Config loader (FIXED Path handling)
# -------------------------
def load_guardrail_gate(cfg_path: Optional[str] = None) -> GuardrailGate:
    """
    Loads config/performance_risk_guardrails.yaml by default.
    Accepts optional path override.
    """
    base_dir = Path(__file__).resolve().parent

    if cfg_path is None:
        cfg_file = base_dir / "config" / "performance_risk_guardrails.yaml"
    else:
        p = Path(cfg_path)
        cfg_file = p if p.is_absolute() else (base_dir / p)

    if not cfg_file.exists():
        raise FileNotFoundError(f"Guardrails config not found: {cfg_file}")

    with cfg_file.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    return GuardrailGate(cfg)


# Backward-compatible aliases (safe)
def load_guardrails(cfg_path: Optional[str] = None) -> GuardrailGate:
    return load_guardrail_gate(cfg_path)


def evaluate_guardrails(portfolio_state: Dict[str, Any], gate_or_cfg: Union[GuardrailGate, Dict[str, Any]]) -> Dict[str, Any]:
    gate = gate_or_cfg if isinstance(gate_or_cfg, GuardrailGate) else GuardrailGate(gate_or_cfg)
    return gate.evaluate(portfolio_state).to_dict()
