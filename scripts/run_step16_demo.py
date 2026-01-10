from __future__ import annotations
from _bootstrap import bootstrap
bootstrap()


import os
import logging

from App.order_executor import OrderExecutor, OrderRequest

from Core.strategy_eligibility_mask import load_strategy_eligibility_mask
from Core.execution_alpha import ExecutionAlpha
from Core.slippage_tracker import SlippageTracker
from Core.adverse_selection import AdverseSelectionMonitor


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )


def project_path(*parts: str) -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, *parts)


class DummyBroker:
    def __init__(self) -> None:
        self.account_equity = 100000.0

    def get_quote(self, symbol: str):
        return {"bid": 99.99, "ask": 100.01, "last": 100.00, "mid": 100.00}

    def submit_order(self, **kwargs):
        return "ORDER_ID_DEMO"

    def submit_algo(self, **kwargs):
        return "ALGO_ID_DEMO"


# ---- THROTTLE BYPASS (TEST ONLY) ----
class _ThrottleDecision:
    def __init__(self, allowed: bool, reason: str):
        self.allowed = allowed
        self.reason = reason


class NullThrottle:
    """Test-only throttle that always allows."""
    def can_trade(self, regime: str, urgency: str):
        return _ThrottleDecision(True, "NULL_THROTTLE_TEST_ONLY")

    def record_trade(self, regime: str, symbol: str, strategy: str):
        return


def build_executor(mode: str = "PAPER") -> OrderExecutor:
    mask = load_strategy_eligibility_mask(project_path("Config", "strategy_eligibility_mask.yaml"))

    execution_alpha = ExecutionAlpha(project_path("Config", "execution_alpha.yaml"))

    slippage = SlippageTracker(
        state_path=project_path("Config", "slippage_state.json"),
        events_path=project_path("Config", "slippage_events.jsonl"),
        max_acceptable_slippage_bps=5.0,
        severe_multiplier=2.0,
        warn_multiplier=1.5,
        hourly_slippage_limit_usd=500.0,
        daily_slippage_limit_usd=2000.0,
        equity_slippage_limit_pct=0.001,
    )

    adverse = AdverseSelectionMonitor(
        config_path=project_path("Config", "adverse_selection.yaml"),
        state_path=project_path("Config", "adverse_selection_state.json"),
        events_path=project_path("Config", "adverse_selection_events.jsonl"),
    )

    broker = DummyBroker()

    return OrderExecutor(
        broker=broker,
        eligibility_mask=mask,
        throttle=NullThrottle(),  # <<< BYPASS Step 12 for this demo
        execution_alpha=execution_alpha,
        slippage_tracker=slippage,
        adverse_selection=adverse,
        logger=logging.getLogger("OrderExecutor"),
        mode=mode,
    )


def main() -> None:
    setup_logging()
    exe = build_executor(mode=os.getenv("BOT_MODE", "PAPER").upper())

    # RANGE allows MEAN_REVERSION (your mask blocks TREND_FOLLOW in RANGE)
    req = OrderRequest(
        symbol="SPY",
        side="BUY",
        qty=2500,
        strategy="MEAN_REVERSION",
        meta={
            "expected_price": 100.00,

            # STEP 16 demo knobs:
            "latency_ms": 40,
            "sim_fill_speed_s": 0.20,        # fast fill
            "sim_post_fill_move_bps": -8.0,  # adverse move after fill
        },
    )

    out1 = exe.place_order(req, regime="RANGE", confidence=0.75)
    logging.info("Order #1 result: %s", out1)

    # Option B: make #2 urgent (doesn't matter now, but keeps the test aligned)
    req2 = OrderRequest(
        symbol=req.symbol,
        side=req.side,
        qty=req.qty,
        strategy=req.strategy,
        meta={**(req.meta or {}), "urgent": True, "urgency_tier": "HIGH"},
    )

    out2 = exe.place_order(req2, regime="RANGE", confidence=0.75)
    logging.info("Order #2 result: %s", out2)


if __name__ == "__main__":
    main()