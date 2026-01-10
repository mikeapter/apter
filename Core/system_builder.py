# Core/system_builder.py
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from Core.policy_engine import PolicyEngine
from Core.portfolio_constraints import PortfolioConstraintsGate, MetaPortfolioProvider
from Core.strategy_eligibility_mask import StrategyEligibilityMask, load_strategy_eligibility_mask


def _load_yaml_if_exists(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_system(config_dir: str = "Config") -> PolicyEngine:
    """
    Build a minimal working PolicyEngine from Config/* files.
    """
    cfg_dir = Path(config_dir)

    # Strategy eligibility mask
    sem_path = cfg_dir / "strategy_eligibility_mask.yaml"
    eligibility_mask = None
    if sem_path.exists():
        eligibility_mask = StrategyEligibilityMask(load_strategy_eligibility_mask(sem_path))

    # Portfolio constraints
    pc_path = cfg_dir / "portfolio_constraints.yaml"
    portfolio_gate = None
    if pc_path.exists():
        portfolio_gate = PortfolioConstraintsGate.from_yaml(pc_path, meta_provider=MetaPortfolioProvider())

    return PolicyEngine(
        eligibility_mask=eligibility_mask,
        portfolio_gate=portfolio_gate,
    )
