from __future__ import annotations
from _bootstrap import bootstrap
bootstrap()


import json
import time
from pathlib import Path

from Core.execution_safe_mode import ExecutionSafeModeMonitor


def main() -> None:
    root = Path(__file__).resolve().parents[1]  # BotTrader/
    cfg = root / "Config" / "execution_safe_mode.yaml"
    state = root / "Config" / "execution_safe_mode_state.json"

    print(f"[TEST] repo_root = {root}")
    print(f"[TEST] cfg      = {cfg}")
    print(f"[TEST] state    = {state}")

    # 1) Write what STEP 21 watchdog/degradation would write
    forced_payload = {
        "level": "NORMAL",
        "since_ts": time.time() - 120,
        "last_level_change_ts": time.time() - 120,
        "forced_level": "ALERT",
        "forced_reason": "TCA_DEGRADATION:avg_total_cost_bps=12>8",
        "forced_ts": time.time(),
    }
    state.write_text(json.dumps(forced_payload, indent=2), encoding="utf-8")
    print("[TEST] wrote forced override into execution_safe_mode_state.json")

    # 2) Instantiate monitor + call pre_trade WITHOUT meta override
    mon = ExecutionSafeModeMonitor(
        config_path=cfg,
        state_path=state,
        events_path=root / "Config" / "execution_safe_mode_events.jsonl",
        logger=None,
    )

    quote = {"bid": 99.50, "ask": 100.50, "last": 100.00, "mid": 100.00}
    meta = {}  # IMPORTANT: no force_safe_mode_level in meta

    d = mon.pre_trade(symbol="SPY", side="BUY", qty=100, quote=quote, meta=meta)
    print("[TEST] decision level  :", d.level)
    print("[TEST] decision reasons:", d.reasons)

    # 3) Confirm the override was NOT wiped out by persist
    after = json.loads(state.read_text(encoding="utf-8"))
    print("[TEST] state forced_level :", after.get("forced_level"))
    print("[TEST] state forced_reason:", after.get("forced_reason"))

    assert d.level == "ALERT", "Expected ALERT from forced_level in state file"
    assert after.get("forced_level") == "ALERT", "forced_level got wiped out (persist bug)"
    print("PASS ✅ forced override works AND is preserved.")


if __name__ == "__main__":
    main()