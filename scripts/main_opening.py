from __future__ import annotations
from _bootstrap import bootstrap
bootstrap()


import time
from premarket_planner import load_opening_playbook, preopen_plan
from App.opening_executor import run_opening_engine


def main() -> None:
    cfg = load_opening_playbook("config/opening_playbook.yaml")

    # PREOPEN
    t0 = time.perf_counter()
    plans = preopen_plan(cfg)
    preopen_ms = (time.perf_counter() - t0) * 1000.0

    print(f"[PREOPEN] plans={len(plans)} built in {preopen_ms:.1f}ms")
    for p in plans:
        print(f"  - {p.symbol} state={p.state} side={p.side} max_qty={p.max_qty}")

    if not plans:
        print("[PREOPEN] Nothing tradable today. Exiting.")
        return

    # OPEN (multi-symbol, single loop)
    tick_ms = int(cfg["execution"]["tick_ms"])
    run_opening_engine(plans=plans, tick_ms=tick_ms, avg_daily_volume_default=5_000_000)


if __name__ == "__main__":
    main()