# Core/decision.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Decision:
    """
    Standard decision object returned by gates.
    Tests expect attributes like: allowed, action, adjusted_qty.
    """
    allowed: bool
    qty: int
    reason: str = "OK"
    details: Dict[str, Any] = field(default_factory=dict)
    action: str = "ALLOW"

    @property
    def adjusted_qty(self) -> int:
        return int(self.qty)
