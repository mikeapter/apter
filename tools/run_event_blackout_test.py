from __future__ import annotations
from _bootstrap import bootstrap
bootstrap()


import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# --- FIX: ensure project root is importable (so "import Core..." works) ---
ROOT = Path(__file__).resolve().parents[1]  # BotTrader/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.event_blackouts import EventBlackoutGate, VERSION  # noqa: E402


def next_weekday_et(tz: ZoneInfo) -> datetime:
    d = datetime.now(tz=tz)
    while d.weekday() >= 5:  # Sat/Sun -> move forward
        d = d + timedelta(days=1)
    return d


def main() -> None:
    tz = ZoneInfo("America/New_York")

    cfg = ROOT / "Config" / "event_blackouts.yaml"
    state = ROOT / "Config" / "event_blackouts_state.json"

    gate = EventBlackoutGate(config_path=cfg, state_path=state)

    base = next_weekday_et(tz)
    # Force a weekday date label (Mon–Fri) for the test
    base = base.replace(hour=0, minute=0, second=0, microsecond=0)

    # These times are intentionally INSIDE the typical 09:30–16:00 ET session
    session_open = base.replace(hour=9, minute=30)
    session_close = base.replace(hour=16, minute=0)

    ts_open = (session_open + timedelta(minutes=1)).timestamp()    # 09:31 ET (OPEN window)
    ts_mid = (session_open + timedelta(hours=2)).timestamp()       # 11:30 ET (MIDDAY)
    ts_close = (session_close - timedelta(minutes=1)).timestamp()  # 15:59 ET (CLOSE window)

    normal_quote = {"bid": 99.99, "ask": 100.01, "mid": 100.00, "last": 100.00}
    shock_quote = {"bid": 99.50, "ask": 100.50, "mid": 100.00, "last": 100.00}  # huge spread

    print("MODULE:", ROOT / "Core" / "event_blackouts.py")
    print("VERSION:", VERSION)

    # OPEN
    d1 = gate.pre_trade(
        symbol="SPY",
        side="BUY",
        qty=100,
        strategy="TEST",
        quote=normal_quote,
        meta={"ignore_weekends": True},
        now_ts=ts_open,
    )
    print(f"OPEN:    allowed={d1.allowed} action={d1.action} reason={d1.reason} cancel_resting={d1.cancel_resting}")

    # MIDDAY
    d2 = gate.pre_trade(
        symbol="SPY",
        side="BUY",
        qty=100,
        strategy="TEST",
        quote=normal_quote,
        meta={"ignore_weekends": True},
        now_ts=ts_mid,
    )
    print(f"MIDDAY:  allowed={d2.allowed} action={d2.action} reason={d2.reason}")

    # CLOSE
    d3 = gate.pre_trade(
        symbol="SPY",
        side="BUY",
        qty=100,
        strategy="TEST",
        quote=normal_quote,
        meta={"ignore_weekends": True},
        now_ts=ts_close,
    )
    print(f"CLOSE:   allowed={d3.allowed} action={d3.action} reason={d3.reason} cancel_resting={d3.cancel_resting}")

    # SHOCK
    if os.getenv("SHOCK_TEST", "").strip() == "1":
        d4 = gate.pre_trade(
            symbol="SPY",
            side="BUY",
            qty=100,
            strategy="TEST",
            quote=shock_quote,
            meta={"ignore_weekends": True},
            now_ts=ts_mid,
        )
        print(f"SHOCK:   allowed={d4.allowed} action={d4.action} reason={d4.reason} cancel_resting={d4.cancel_resting}")


if __name__ == "__main__":
    main()