from __future__ import annotations

from typing import Any, Dict, Protocol


class Broker(Protocol):
    def get_quote(self, symbol: str) -> Dict[str, Any]: ...
    def submit_order(self, symbol: str, side: str, qty: int, plan: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]: ...
