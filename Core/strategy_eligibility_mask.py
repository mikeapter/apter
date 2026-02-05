# Core/strategy_eligibility_mask.py
from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from Core.decision import Decision


def _as_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i) for i in x]
    return [str(x)]


def _matches_any(patterns: List[str], value: str) -> bool:
    """
    Supports exact + wildcard patterns (e.g., 'MEAN_*').
    """
    for p in patterns:
        p = str(p)
        if p == value:
            return True
        # wildcard support
        if any(ch in p for ch in ["*", "?", "["]):
            if fnmatchcase(value, p):
                return True
    return False


@dataclass(frozen=True)
class RegimeRule:
    allow: List[str]
    prohibit: List[str]


class StrategyEligibilityMask:
    """
    Test-compatible API:
      - StrategyEligibilityMask(regimes=..., default_policy=..., min_confidence_to_trade=...)
      - decide(regime, strategy_id, confidence=...) -> Decision
      - from_yaml(path) -> StrategyEligibilityMask
      - load_strategy_eligibility_mask(path) helper

    Also supports older YAML shape:
      defaults:
        allow_if_missing: true
      matrix:
        NORMAL:
          allow: [...]
          block: [...]
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        *,
        regimes: Optional[Dict[str, Any]] = None,
        default_policy: str = "PROHIBIT",
        min_confidence_to_trade: float = 0.0,
    ) -> None:
        if config is None:
            config = {}

        if not isinstance(config, dict):
            raise TypeError("StrategyEligibilityMask config must be a dict (or use keyword args).")

        # If constructed via tests using kwargs, use them directly.
        if regimes is not None:
            self.default_policy = str(default_policy).upper()
            self.min_confidence_to_trade = float(min_confidence_to_trade)
            self.regimes = self._normalize_regimes(regimes)
            return

        # Otherwise parse from YAML-loaded dict.
        self._load_from_config_dict(config)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "StrategyEligibilityMask":
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cls(cfg)

    def _load_from_config_dict(self, cfg: Dict[str, Any]) -> None:
        self.min_confidence_to_trade = float(cfg.get("min_confidence_to_trade", 0.0))

        # New shape
        if "regimes" in cfg and isinstance(cfg["regimes"], dict):
            self.default_policy = str(cfg.get("default_policy", "PROHIBIT")).upper()
            self.regimes = self._normalize_regimes(cfg["regimes"])
            return

        # Old shape fallback
        defaults = cfg.get("defaults", {}) or {}
        allow_if_missing = bool(defaults.get("allow_if_missing", False))
        self.default_policy = "ALLOW" if allow_if_missing else "PROHIBIT"

        matrix = cfg.get("matrix", {}) or {}
        self.regimes = {}
        if isinstance(matrix, dict):
            for regime, row in matrix.items():
                row = row or {}
                allow = _as_list(row.get("allow"))
                prohibit = _as_list(row.get("prohibit")) + _as_list(row.get("block"))
                self.regimes[str(regime)] = RegimeRule(allow=allow, prohibit=prohibit)

    def _normalize_regimes(self, regimes: Dict[str, Any]) -> Dict[str, RegimeRule]:
        out: Dict[str, RegimeRule] = {}
        for regime, row in regimes.items():
            row = row or {}
            allow = _as_list(row.get("allow"))
            prohibit = _as_list(row.get("prohibit")) + _as_list(row.get("block"))
            out[str(regime)] = RegimeRule(allow=allow, prohibit=prohibit)
        return out

    # ----------- TEST SIGNATURE -----------
    def decide(self, regime: str, strategy_id: str, *, confidence: float = 1.0, qty: int = 1) -> Decision:
        """
        Unit tests call: decide("RANGE", "MEAN_REVERSION", confidence=0.90)
        """
        regime = str(regime)
        strategy_id = str(strategy_id)

        try:
            conf_f = float(confidence)
        except Exception:
            conf_f = 1.0

        # Confidence hard gate
        if conf_f < float(self.min_confidence_to_trade):
            return Decision(
                allowed=False,
                qty=0,
                reason="confidence_below_min",
                details={
                    "regime": regime,
                    "strategy": strategy_id,
                    "confidence": conf_f,
                    "min_confidence_to_trade": self.min_confidence_to_trade,
                },
                action="BLOCK",
            )

        rule = self.regimes.get(regime)
        if rule is None:
            allowed = (self.default_policy == "ALLOW")
            return Decision(
                allowed=allowed,
                qty=int(qty) if allowed else 0,
                reason="UNKNOWN_REGIME_DEFAULT_POLICY",
                details={"regime": regime, "strategy": strategy_id, "default_policy": self.default_policy},
                action="ALLOW" if allowed else "BLOCK",
            )

        # Prohibit always wins (supports wildcards)
        if _matches_any(rule.prohibit, strategy_id):
            return Decision(
                allowed=False,
                qty=0,
                reason="prohibited_by_mask",
                details={"regime": regime, "strategy": strategy_id, "prohibit": rule.prohibit},
                action="BLOCK",
            )

        # Allow-list exists => must match (supports wildcards)
        if rule.allow:
            if _matches_any(rule.allow, strategy_id):
                return Decision(
                    allowed=True,
                    qty=int(qty),
                    reason="ALLOWED_BY_MASK",
                    details={"regime": regime, "strategy": strategy_id, "allow": rule.allow},
                    action="ALLOW",
                )
            return Decision(
                allowed=False,
                qty=0,
                reason="NOT_IN_ALLOW_LIST",
                details={"regime": regime, "strategy": strategy_id, "allow": rule.allow},
                action="BLOCK",
            )

        # No allow list => allow unless prohibited
        return Decision(
            allowed=True,
            qty=int(qty),
            reason="ALLOWED_BY_DEFAULT",
            details={"regime": regime, "strategy": strategy_id},
            action="ALLOW",
        )

    # ----------- ENGINE COMPAT (optional) -----------
    def check(self, order: Any, meta: Dict[str, Any]) -> Decision:
        """
        Engine-friendly wrapper if you call it with order/meta.
        """
        strategy_id = str(getattr(order, "strategy_id", getattr(order, "strategy", "UNKNOWN")))
        regime = str(meta.get("regime") or meta.get("regime_label") or "UNKNOWN")
        confidence = meta.get("regime_conf", 1.0)
        qty = int(getattr(order, "qty", 1))
        return self.decide(regime, strategy_id, confidence=confidence, qty=qty)


def load_strategy_eligibility_mask(path: str | Path) -> StrategyEligibilityMask:
    """
    Backwards-compatible loader expected by unit tests.
    """
    return StrategyEligibilityMask.from_yaml(path)
# ----------------------------
# Backwards-compatibility aliases
# ----------------------------

# Older tests / modules expect these names
EligibilityDecision = Decision
EligibilityMask = StrategyEligibilityMask

