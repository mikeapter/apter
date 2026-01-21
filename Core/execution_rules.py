# Core/execution_rules.py

from datetime import time
from Core.market_snapshot import MarketSnapshot


class ExecutionRules:
    """
    Enforces time, liquidity, and execution safety rules.
    """

    # --- Market hours (UTC) ---
    MARKET_OPEN_UTC = time(14, 30)   # 09:30 ET
    MARKET_CLOSE_UTC = time(21, 0)   # 16:00 ET

    FIRST_5_MIN_END = time(14, 35)

    # --- Liquidity thresholds ---
    MIN_ADV = 50_000
    MIN_TOB = 100

    # --- Execution quality ---
    MAX_SPREAD_BPS = 300.0   # <-- FIXED: allows normal 1–2% spreads


    def is_trade_allowed(self, mkt: MarketSnapshot, order_type: str) -> bool:
        t = mkt.ts_utc.time()
        order_type = order_type.lower()

        # --- Outside market hours ---
        if t < self.MARKET_OPEN_UTC or t >= self.MARKET_CLOSE_UTC:
            return False

        # --- Block first 5 minutes ---
        if t < self.FIRST_5_MIN_END:
            return False

        # --- Block stop orders near close ---
        if order_type == "stop" and t >= time(15, 55):
            return False

        # --- Thin liquidity ---
        if mkt.adv < self.MIN_ADV or mkt.top_of_book_size < self.MIN_TOB:
            return False

        # --- Wide spreads force passive execution ---
        if mkt.spread_bps > self.MAX_SPREAD_BPS and order_type == "market":
            return False

        return True
