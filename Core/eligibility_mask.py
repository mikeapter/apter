from __future__ import annotations

"""Compatibility shim.

Older code imported:
    from Core.eligibility_mask import EligibilityDecision, EligibilityMask

The actual implementation lives in Core.strategy_eligibility_mask as:
    EligibilityDecision, StrategyEligibilityMask

This file keeps legacy imports working.
"""

from Core.strategy_eligibility_mask import EligibilityDecision, StrategyEligibilityMask

# Backwards-compatible alias
EligibilityMask = StrategyEligibilityMask
