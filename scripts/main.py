from _bootstrap import bootstrap
bootstrap()

import time
from dataclasses import dataclass
from typing import Any

from Core.adverse_selection import AdverseSelectionModule
from Core.eligibility_mask import EligibilityMask
from Core.event_blackouts import EventBlackoutGate
from Core.portfolio_constraints import PortfolioConstraintsGate, MetaPortfolioProvider
from Core.execution_alpha import ExecutionAlphaModule
from Core.execution_safe_mode import ExecutionSafeModeModule
from Core.slippage_tracker import SlippageTracker
from Core.trade_throttle import TradeThrottle
from App.order_executor import OrderExecutor


@dataclass
class Quote:
    bid: float
    ask: float
    last: float

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0


class DummyBroker:
    def get_quote(self, symbol: str) -> Quote:
        return Quote(bid=99.95, ask=100.05, last=100.00)

    def submit_order(self, symbol: str, side: str, qty: int, plan: Any, meta: Any):
        # Replace with your real broker
        q = self.get_quote(symbol)
        return {"status": "LIVE_SUBMITTED", "symbol": symbol, "side": side, "qty": qty, "fill_price": q.mid, "plan": plan, "meta": meta}


def build_executor() -> OrderExecutor:
    broker = DummyBroker()

    eligibility = EligibilityMask.from_yaml("Config/strategy_eligibility.yaml")  # STEP 09
    throttle = TradeThrottle.from_yaml("Config/trade_throttle.yaml")  # STEP 12
    slippage = SlippageTracker.from_yaml("Config/slippage_tracker.yaml")  # STEP 15
    exec_alpha = ExecutionAlphaModule.from_yaml("Config/execution_alpha.yaml")  # STEP 15
    adverse = AdverseSelectionModule.from_yaml("Config/adverse_selection.yaml")  # STEP 16
    safe_mode = ExecutionSafeModeModule.from_yaml("Config/execution_safe_mode.yaml")  # STEP 17
    event_blackout = EventBlackoutGate.from_yaml("Config/event_blackouts.yaml")  # STEP 18

    portfolio_constraints = PortfolioConstraintsGate.from_yaml(
        "Config/portfolio_constraints.yaml",
        meta_provider=MetaPortfolioProvider(),
    )

    return OrderExecutor(
        broker,
        eligibility_mask=eligibility,
        throttle=throttle,
        slippage_tracker=slippage,
        execution_alpha=exec_alpha,
        adverse_selection=adverse,
        safe_mode=safe_mode,
        event_blackout=event_blackout,  # STEP 18
        portfolio_constraints=portfolio_constraints,  # STEP 19
        mode="PAPER",
    )


def main():
    ex = build_executor()

    meta = {
        "now_ts": time.time(),
        "regime": "NORMAL",
        "sector": "TECH",
        "country": "US",
        # DEMO portfolio snapshot (replace with a real PortfolioProvider later)
        "portfolio": {
            "nav": 100_000,
            "equity": 100_000,
            "cash": 25_000,
            "positions": [
                {"symbol": "SPY", "qty": 20, "price": 100, "sector": "EQUITY_INDEX", "country": "US", "strategy": "CORE", "daily_vol": 0.012},
            ],
            "risk_metrics": {"var_95": 0.01, "var_99": 0.02, "es_97_5": 0.02},
        },
    }

    print(ex.place_order("AAPL", "BUY", 50, "OPENING_PLAYBOOK", meta))


if __name__ == "__main__":
    main()