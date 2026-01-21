# tools/test_execution_rules.py

from datetime import datetime, timezone
from Core.execution_rules import ExecutionRules
from Core.market_snapshot import MarketSnapshot


class TestExecutionRules:

    def setup_method(self):
        self.rules = ExecutionRules()

    def _mkt(
        self,
        ts_utc: datetime,
        bid=99.0,
        ask=101.0,
        last=100.0,
        adv=500_000,
        tob=5_000,
        vol=0.3,
        fillp=0.8,
        impact=5.0,
    ):
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
        ts = datetime(2025, 12, 15, 14, 32, tzinfo=timezone.utc)
        mkt = self._mkt(ts)
        assert not self.rules.is_trade_allowed(mkt, "market")

    def test_allows_after_window(self):
        ts = datetime(2025, 12, 15, 14, 40, tzinfo=timezone.utc)
        mkt = self._mkt(ts)
        assert self.rules.is_trade_allowed(mkt, "market")

    def test_blocks_stop_market(self):
        ts = datetime(2025, 12, 15, 16, 0, tzinfo=timezone.utc)
        mkt = self._mkt(ts)
        assert not self.rules.is_trade_allowed(mkt, "stop")

    def test_no_market_in_thin_liquidity(self):
        ts = datetime(2025, 12, 15, 16, 0, tzinfo=timezone.utc)
        mkt = self._mkt(ts, adv=1_000, tob=10)
        assert not self.rules.is_trade_allowed(mkt, "market")

    def test_wide_spread_forces_passive(self):
        ts = datetime(2025, 12, 15, 16, 0, tzinfo=timezone.utc)
        mkt = self._mkt(ts, bid=90, ask=110)
        assert not self.rules.is_trade_allowed(mkt, "market")
