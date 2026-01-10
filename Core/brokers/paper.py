from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Dict


def _mid(bid: float, ask: float) -> float:
    return (float(bid) + float(ask)) / 2.0


@dataclass
class PaperBroker:
    """
    Simple paper broker:
      - returns a synthetic quote
      - "fills" immediately at mid (+/- tiny noise)
    """
    seed: int = 42
    base_price: float = 100.0
    spread_bps: float = 5.0

    def __post_init__(self) -> None:
        random.seed(self.seed)

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        drift = (random.random() - 0.5) * 0.02
        self.base_price = max(0.01, self.base_price * (1.0 + drift / 100.0))

        mid = float(self.base_price)
        spread = mid * (self.spread_bps / 10_000.0)
        bid = mid - spread / 2.0
        ask = mid + spread / 2.0
        return {
            "bid": bid,
            "ask": ask,
            "mid": _mid(bid, ask),
            "last": mid,
            "spread_bps": self.spread_bps,
            "quote_ts": time.time(),
        }

    def submit_order(self, symbol: str, side: str, qty: int, plan: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        q = self.get_quote(symbol)
        mid = float(q["mid"])
        noise = (random.random() - 0.5) * (mid * 0.5 / 10_000.0)  # +/-0.5bp
        fill_price = mid + noise if str(side).upper() == "BUY" else mid - noise

        return {
            "status": "FILLED",
            "symbol": symbol,
            "side": str(side).upper(),
            "qty": int(qty),
            "fill_price": float(fill_price),
            "price": float(fill_price),
            "latency_ms": 3.0,
            "plan": plan,
        }
