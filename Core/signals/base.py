from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


def _sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _to_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


@dataclass(frozen=True)
class AlphaContext:
    symbol: str
    now: datetime
    regime_label: str = "UNKNOWN"
    regime_confidence: Optional[float] = None
    features: Dict[str, Any] = field(default_factory=dict)
    quote: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def f(self, key: str, default: Any = None) -> Any:
        return self.features.get(key, default)

    def q(self, key: str, default: Any = None) -> Any:
        return self.quote.get(key, default)

    def m(self, key: str, default: Any = None) -> Any:
        return self.meta.get(key, default)


@dataclass(frozen=True)
class SignalDecision:
    module: str
    kind: str  # structural | statistical | execution
    active: bool
    direction: int = 0
    score: float = 0.0
    confidence: float = 0.0
    urgency: float = 0.0
    reason: str = ""
    outputs: Dict[str, Any] = field(default_factory=dict)

    def urgency_tier(self) -> str:
        u = float(self.urgency or 0.0)
        if u >= 0.85:
            return "CRITICAL"
        if u >= 0.60:
            return "HIGH"
        if u >= 0.30:
            return "NORMAL"
        return "LOW"


class SignalModule:
    name: str = "base"
    kind: str = "structural"
    priority: str = "MEDIUM"

    def compute(self, ctx: AlphaContext, cfg: Dict[str, Any]) -> SignalDecision:
        raise NotImplementedError

    def _inactive(self, reason: str) -> SignalDecision:
        return SignalDecision(
            module=self.name,
            kind=self.kind,
            active=False,
            direction=0,
            score=0.0,
            confidence=0.0,
            urgency=0.0,
            reason=reason,
            outputs={},
        )

    def _mk(
        self,
        *,
        active: bool,
        direction: int,
        score: float,
        confidence: float,
        urgency: float,
        reason: str = "",
        outputs: Optional[Dict[str, Any]] = None,
    ) -> SignalDecision:
        return SignalDecision(
            module=self.name,
            kind=self.kind,
            active=bool(active),
            direction=int(direction),
            score=float(score),
            confidence=_clamp(float(confidence), 0.0, 1.0),
            urgency=_clamp(float(urgency), 0.0, 1.0),
            reason=reason or "",
            outputs=outputs or {},
        )

    def _sign(self, x: float) -> int:
        return _sign(x)

    def _to_float(self, x: Any, default: Optional[float] = None) -> Optional[float]:
        return _to_float(x, default=default)
