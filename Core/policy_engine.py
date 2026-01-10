# Core/policy_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from Core.decision import Decision
from Core.portfolio_constraints import PortfolioConstraintsGate
from Core.strategy_eligibility_mask import StrategyEligibilityMask


@dataclass
class PolicyEngine:
    eligibility_mask: Optional[StrategyEligibilityMask] = None
    portfolio_gate: Optional[PortfolioConstraintsGate] = None

    def evaluate(self, order: Any, meta: Dict[str, Any], price: float) -> Decision:
        # 1) Eligibility mask first (hard block)
        if self.eligibility_mask is not None:
            d = self.eligibility_mask.check(order, meta)
            if not d.allowed:
                return d

        # 2) Portfolio constraints (may resize or block)
        if self.portfolio_gate is not None:
            return self.portfolio_gate.check_pre_trade(order, meta=meta, price=price)

        # If nothing configured, allow as-is
        return Decision(True, int(getattr(order, "qty")), reason="NO_GATES_CONFIGURED", action="ALLOW")
