from _bootstrap import bootstrap
bootstrap()

import unittest
from App.strategy_governance import StrategyGovernance


class TestStrategyGovernance(unittest.TestCase):
    def test_deployed_strategies_must_pass(self):
        gov = StrategyGovernance()
        for s in gov.list_strategies():
            sid = s.get("strategy_id")
            stage = str(s.get("stage", "DESIGN")).upper()
            enabled = bool(s.get("enabled", False))

            # Only enforce strict pass/fail for strategies that claim they can trade
            if enabled and stage in ("DEPLOY", "MONITOR"):
                res = gov.check_strategy(sid, stage)
                self.assertTrue(res.ok, msg=f"{sid} failed governance: {res.reasons}")


if __name__ == "__main__":
    unittest.main()