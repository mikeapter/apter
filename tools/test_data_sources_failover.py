from _bootstrap import bootstrap
bootstrap()

import os
import sys

# Add project root (BotTrader) to import path so pytest can import modules in root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from App.data_sources import FailoverFeed, StubAdapter


def test_failover_on_exception():
    primary = StubAdapter("primary", fail=True)
    secondary = StubAdapter("secondary", fail=False, price=101.0)

    policy = {
        "max_missed_heartbeats": 1,
        "max_stale_seconds": 2,
        "latency_outage_ms": 1000,
    }

    feed = FailoverFeed("l1", primary, secondary, policy)
    q = feed.get_l1("AAPL")

    assert feed.active.name == "secondary"
    assert q.symbol == "AAPL"


def test_failover_on_stale():
    primary = StubAdapter("primary", stale_seconds=10.0)  # too stale
    secondary = StubAdapter("secondary", stale_seconds=0.0)

    policy = {
        "max_missed_heartbeats": 3,
        "max_stale_seconds": 2,
        "latency_outage_ms": 1000,
    }

    feed = FailoverFeed("l1", primary, secondary, policy)
    _ = feed.get_l1("TSLA")

    assert feed.active.name == "secondary"