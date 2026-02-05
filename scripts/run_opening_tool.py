from __future__ import annotations

import argparse
import json
import time

from _bootstrap import bootstrap


def _main() -> int:
    repo_root = bootstrap()

    # Lazy imports after sys.path/bootstrap
    from App.data_sources import DataRedundancyManager
    from App.opening_executor import OpeningExecutor

    parser = argparse.ArgumentParser(description="Signals-only Opening Tool runner (no trade execution).")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit (default).")
    parser.add_argument("--loop", action="store_true", help="Run continuously on an interval.")
    parser.add_argument("--interval", type=int, default=30, help="Loop interval seconds (default: 30).")
    args = parser.parse_args()

    cfg_path = repo_root / "Config" / "opening_playbook.yaml"
    data_cfg = repo_root / "Config" / "data_sources.yaml"

    data = DataRedundancyManager(config_path=str(data_cfg))
    executor = OpeningExecutor(data=data, order_exec=None, repo_root=repo_root, config_path=cfg_path)

    def run_cycle() -> None:
        res = executor.run_one_shot()
        print(json.dumps(res, indent=2, default=str))

    if args.loop:
        while True:
            run_cycle()
            time.sleep(max(1, int(args.interval)))
    else:
        run_cycle()

    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
