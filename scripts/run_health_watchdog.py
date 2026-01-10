from __future__ import annotations
from _bootstrap import bootstrap
bootstrap()


import argparse
import time
from pathlib import Path

from Core.monitoring.monitoring_manager import MonitoringManager


def main() -> None:
    ap = argparse.ArgumentParser(description="STEP 21 — Live monitoring watchdog (degradation triggers)")
    ap.add_argument("--repo", default=None, help="Repo root (defaults to this file's folder).")
    ap.add_argument("--interval", type=float, default=10.0, help="Seconds between checks.")
    args = ap.parse_args()

    repo_root = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[1]
    monitor = MonitoringManager(repo_root=repo_root, config_path=repo_root / "Config" / "monitoring.yaml")

    print(f"[WATCHDOG] trade_log={monitor.trade_log_path}")
    print(f"[WATCHDOG] safe_mode_state={monitor.safe_mode_state_path}")
    print(f"[WATCHDOG] slippage_state={monitor.slippage_state_path}")
    print(f"[WATCHDOG] interval={args.interval}s")

    last_level = None
    while True:
        action = monitor.check_and_apply_degradation()
        if action.level != last_level:
            print(f"[WATCHDOG] level={action.level} reason={action.reason} details={action.details}")
            last_level = action.level
        time.sleep(args.interval)


if __name__ == "__main__":
    main()