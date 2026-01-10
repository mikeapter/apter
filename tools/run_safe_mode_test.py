from _bootstrap import bootstrap
bootstrap()

import os
import logging

from App.order_executor import OrderExecutor, OrderRequest
from Core.strategy_eligibility_mask import load_strategy_eligibility_mask
from Core.trade_throttle import TradeThrottle
from Core.execution_alpha import ExecutionAlpha
from Core.slippage_tracker import SlippageTracker
from Core.adverse_selection import AdverseSelectionMonitor
from Core.execution_safe_mode import ExecutionSafeModeMonitor


def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")


def project_path(*parts: str) -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(here)  # parent of "Testing Rules" is BotTrader/
    return os.path.join(repo, *parts)


class DummyBroker:
    def __init__(self):
        self.account_equity = 100000.0

    def get_quote(self, symbol: str):
        # Wide spread quote to trigger safe mode
        return {"bid": 99.50, "ask": 100.50, "last": 100.00, "mid": 100.00}

    def submit_order(self, **kwargs):
        return "ORDER_ID_DEMO"

    # optional cancel API
    def cancel_all_orders(self, symbol=None):
        return True


def main():
    setup_logging()

    mask = load_strategy_eligibility_mask(project_path("Config", "strategy_eligibility_mask.yaml"))
    throttle = TradeThrottle(project_path("Config", "trade_throttle.yaml"))
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

    safe_mode = ExecutionSafeModeMonitor(
        config_path=project_path("Config", "execution_safe_mode.yaml"),
        state_path=project_path("Config", "execution_safe_mode_state.json"),
        events_path=project_path("Config", "execution_safe_mode_events.jsonl"),
        logger=logging.getLogger("SafeMode"),
    )

    exe = OrderExecutor(
        broker=DummyBroker(),
        eligibility_mask=mask,
        throttle=throttle,
        execution_alpha=execution_alpha,
        slippage_tracker=slippage,
        adverse_selection=adverse,
        safe_mode=safe_mode,
        logger=logging.getLogger("OrderExecutor"),
        mode="PAPER",
    )

    req = OrderRequest(
        symbol="SPY",
        side="BUY",
        qty=1000,
        strategy="MEAN_REVERSION",
        meta={
            "expected_price": 100.0,
            "avg_minute_volume": 15000,
            "volatility": 0.030,
            "vol_z": 3.2,           # triggers ALERT
            "depth_ratio": 0.35,    # triggers ALERT
            "latency_ms": 60,
            "reject_rate": 0.05,
            "is_event_window": True # adds points
        },
    )

    out = exe.place_order(req, regime="RANGE", confidence=0.80)
    print(out)


if __name__ == "__main__":
    main()