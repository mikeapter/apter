from __future__ import annotations
from _bootstrap import bootstrap
bootstrap()


import yaml
from pathlib import Path

from App.order_executor import OrderExecutor
from App.opening_executor import OpeningExecutor, MarketDataClient


class FakeData(MarketDataClient):
    def get_prev_close(self, symbol): return 100.0
    def get_premarket_last(self, symbol): return 103.0
    def get_premarket_volume(self, symbol): return 999999
    def get_last_trade(self, symbol): return 103.2

    # Optional methods used by your YAML gates
    def has_real_catalyst(self, symbol): return True
    def get_bid_ask(self, symbol): return (103.19, 103.21)
    def get_rel_volume(self, symbol): return 2.0
    def get_avg_daily_volume(self, symbol): return 5_000_000


ROOT = Path(__file__).resolve().parents[1]
REG_PATH = ROOT / "config" / "strategy_registry.yaml"
STRATEGY_ID = "opening_playbook"


def _load_registry() -> dict:
    with REG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_registry(reg: dict) -> None:
    with REG_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(reg, f, sort_keys=False)


def _set_stage_enabled(stage: str, enabled: bool) -> None:
    reg = _load_registry()
    strategies = reg.get("strategies", [])
    found = False
    for s in strategies:
        if s.get("strategy_id") == STRATEGY_ID:
            s["stage"] = stage
            s["enabled"] = enabled
            found = True
            break
    if not found:
        raise RuntimeError(f"Strategy {STRATEGY_ID} not found in {REG_PATH}")
    reg["strategies"] = strategies
    _save_registry(reg)


def run_once(label: str) -> None:
    print(f"\n=== {label} ===")
    data = FakeData()
    oe = OrderExecutor(paper=True)  # paper fills only
    ex = OpeningExecutor(data=data, order_exec=oe)
    ex.run()


def main() -> None:
    # Back up current registry so we restore no matter what
    original = _load_registry()

    try:
        # 1) BLOCK TEST: should block (enabled false)
        _set_stage_enabled(stage="DEPLOY", enabled=False)
        run_once("BLOCK TEST (DEPLOY + enabled=false)  -> should GOVERNANCE BLOCK")

        # 2) ALLOW TEST: should allow paper fills (enabled true + MONITOR)
        _set_stage_enabled(stage="MONITOR", enabled=True)
        run_once("ALLOW TEST (MONITOR + enabled=true) -> should PAPER FILL")

    finally:
        _save_registry(original)
        print("\n(Restored original config/strategy_registry.yaml)")


if __name__ == "__main__":
    main()