from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from Core.compliance import forbid_automated_execution


@dataclass
class PaperBroker:
    """
    Paper broker (DISABLED).

    This repo is a **signals-only trading tool**. Automated execution is not permitted,
    including simulated auto-fills.

    Keep this class only as a placeholder so older imports don't break; any call to
    submit orders will hard-stop.
    """

    name: str = "paper"

    def get_quote(self, symbol: str) -> Dict[str, float]:
        # Safe stub quote for analytics pipelines.
        return {"bid": 100.0, "ask": 100.02, "mid": 100.01, "last": 100.01}

    def submit_order(self, symbol: str, side: str, qty: int, order_type: str, limit_price: float | None = None) -> Dict:
        forbid_automated_execution(context="PaperBroker.submit_order")
        # unreachable
        return {}
