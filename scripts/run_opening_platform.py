from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Tuple

from App.opening_executor import OpeningExecutor
from App.order_executor import OrderExecutor
from Core.brokers.paper import PaperBroker
from Core.monitoring.trade_logger import TradeEvent, TradeLogger


@dataclass
class Quote:
    bid: float
    ask: float
    mid: float
    last: float


class PaperBrokerAdapter:
    """
    Adapter so OrderExecutor can use getattr(quote, "mid") etc.
    (Core.brokers.paper.PaperBroker returns dicts; this wraps them.)
    """
    def __init__(self, inner: PaperBroker):
        self.inner = inner

    def get_quote(self, symbol: str) -> Any:
        q: Dict[str, Any] = self.inner.get_quote(symbol)
        # Provide both dict-style keys and attribute access
        return SimpleNamespace(**q)

    def submit_order(self, symbol: str, side: str, qty: int, plan: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return self.inner.submit_order(symbol=symbol, side=side, qty=qty, plan=plan, meta=meta)


class StubOpeningData:
    """
    SAFE stub data source for opening_executor.
    This does NOT connect to live markets.
    """
    def __init__(self, broker: PaperBrokerAdapter):
        self.broker = broker

    def has_real_catalyst(self, symbol: str) -> bool:
        return True  # allow universe filter to pass in demo

    def get_prev_close(self, symbol: str) -> float:
        return 100.0

    def get_premarket_last(self, symbol: str) -> float:
        # Create a consistent “gap” per symbol so the playbook has something to work with.
        # Most symbols gap up a bit in this demo.
        base = 102.50
        bump = (sum(ord(c) for c in symbol.upper()) % 20) / 100.0  # 0.00 .. 0.19
        return base + bump

    def get_premarket_volume(self, symbol: str) -> int:
        return 500_000

    def get_last_trade(self, symbol: str) -> float:
        q = self.broker.get_quote(symbol)
        return float(getattr(q, "last", 0.0) or 0.0)

    def get_bid_ask(self, symbol: str) -> Tuple[float, float]:
        q = self.broker.get_quote(symbol)
        bid = float(getattr(q, "bid", 0.0) or 0.0)
        ask = float(getattr(q, "ask", 0.0) or 0.0)
        return bid, ask


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="Config/opening_playbook.yaml", help="Path relative to repo root")
    ap.add_argument("--seed", type=int, default=42, help="Paper broker seed")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / args.config

    # Broker (paper) + adapter
    paper = PaperBroker(seed=int(args.seed))
    broker = PaperBrokerAdapter(paper)

    # Stub data (safe)
    data = StubOpeningData(broker)

    # Order executor (paper mode)
    order_exec = OrderExecutor(broker, mode="PAPER")

    # Opening executor
    ex = OpeningExecutor(
        data=data,
        order_exec=order_exec,
        repo_root=repo_root,
        config_path=config_path,
    )

    # Run one-shot (safe)
    started = time.time()
    result = ex.run_one_shot()
    elapsed = time.time() - started

    # Log blocked decisions (so monitoring/TCA can see them)
    tl = TradeLogger(repo_root=repo_root)
    blocked = result.get("blocked", {}) or {}
    for sym, reason in blocked.items():
        tl.log(
            TradeEvent(
                ts=time.time(),
                event_type="ORDER_BLOCKED",
                symbol=str(sym).upper(),
                side="NA",
                qty=0,
                strategy="OPENING_PLAYBOOK",
                regime=str(getattr(ex, "regime_label", "UNKNOWN")).upper(),
                reason=str(reason),
                meta={"source": "scripts/run_opening.py"},
            )
        )

    print(f"[RUN_OPENING_DONE] elapsed_s={elapsed:.3f} fired={list((result.get('fired') or {}).keys())} blocked={blocked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
