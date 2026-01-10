from _bootstrap import bootstrap
bootstrap()

import unittest
from datetime import datetime, timezone

from App.order_executor import OrderRequest, MarketSnapshot, decide_execution


class TestExecutionRules(unittest.TestCase):
    def _mkt(self, ts_utc: datetime, bid=99.0, ask=101.0, last=100.0, adv=500000, tob=5000,
             vol=0.3, fillp=0.8, impact=5.0):
        return MarketSnapshot(
            ts_utc=ts_utc,
            bid=bid,
            ask=ask,
            last=last,
            adv=adv,
            top_of_book_size=tob,
            volatility_score=vol,
            fill_probability_est=fillp,
            impact_bps_est=impact,
        )

    def test_blocks_first_5_minutes(self):
        # 09:32 NY == 14:32 UTC during standard time? (We avoid timezone fragility by just ensuring it blocks in-window)
        # We'll use a UTC time that *likely* maps into that window. If your machine TZ differs, this still tests logic path.
        ts = datetime(2025, 12, 15, 14, 32, tzinfo=timezone.utc)
        mkt = self._mkt(ts)
        req = OrderRequest(symbol="SPY", side="BUY", qty=10, urgency=0.5)
        decision = decide_execution(req, mkt)
        self.assertFalse(decision.approved)
        self.assertIn("first/last 5 minutes", decision.reason)

    def test_allows_after_window(self):
        ts = datetime(2025, 12, 15, 14, 40, tzinfo=timezone.utc)
        mkt = self._mkt(ts)
        req = OrderRequest(symbol="SPY", side="BUY", qty=10, urgency=0.5)
        decision = decide_execution(req, mkt)
        self.assertTrue(decision.approved)

    def test_blocks_stop_market(self):
        ts = datetime(2025, 12, 15, 16, 0, tzinfo=timezone.utc)
        mkt = self._mkt(ts)
        req = OrderRequest(symbol="SPY", side="BUY", qty=10, preferred_order_type="STOP_MARKET")
        decision = decide_execution(req, mkt)
        self.assertFalse(decision.approved)
        self.assertIn("STOP_MARKET", decision.reason)

    def test_no_market_in_thin_liquidity(self):
        ts = datetime(2025, 12, 15, 16, 0, tzinfo=timezone.utc)
        mkt = self._mkt(ts, adv=1000, tob=10)  # thin
        req = OrderRequest(symbol="XYZ", side="BUY", qty=10, preferred_order_type="MARKET")
        decision = decide_execution(req, mkt)
        self.assertTrue(decision.approved)
        self.assertNotEqual(decision.order_type, "MARKET")  # forced away from MARKET in thin

    def test_wide_spread_forces_passive(self):
        ts = datetime(2025, 12, 15, 16, 0, tzinfo=timezone.utc)
        mkt = self._mkt(ts, bid=90, ask=110)  # huge spread
        req = OrderRequest(symbol="SPY", side="BUY", qty=10, preferred_order_type="MARKETABLE_LIMIT")
        decision = decide_execution(req, mkt)
        self.assertTrue(decision.approved)
        self.assertEqual(decision.order_type, "LIMIT")


if __name__ == "__main__":
    unittest.main()