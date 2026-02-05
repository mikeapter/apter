"""
Canonical bot entrypoint.
STEP 6 — deterministic wiring validation.
Signals-only: emits signals, never places orders.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import logging
from datetime import datetime

# ============================================================
# TOOL MODE ENFORCEMENT (signals only)
# ============================================================
# This entrypoint is now signal-only. No orders are ever placed.
os.environ.setdefault("BOTTRADER_EXECUTION_MODE", "TOOL")

# ============================================================
# FORCE REPO ROOT
# ============================================================
def force_repo_root() -> Path:
    here = Path(__file__).resolve()
    root = here.parents[1]
    os.chdir(str(root))
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("run_opening")

    REPO_ROOT = force_repo_root()
    log.info(f"REPO_ROOT={REPO_ROOT}")

    from App.data_sources import DataRedundancyManager
    from App.opening_executor import OpeningExecutor
    from App.order_executor import OrderExecutor

    data = DataRedundancyManager(
        config_path=str(REPO_ROOT / "config" / "data_sources.yaml")
    )

    order_exec = OrderExecutor()

    opening_cfg = REPO_ROOT / "config" / "opening_playbook.yaml"
    if not opening_cfg.exists():
        raise FileNotFoundError(f"Missing config file: {opening_cfg}")

    log.info("Initializing OpeningExecutor")
    executor = OpeningExecutor(
        data=data,
        order_exec=order_exec,
        repo_root=REPO_ROOT,
        config_path=str(opening_cfg),
    )

    log.info("Calling run_one_shot()")
    result = executor.run_one_shot()

    signaled = sorted(list(result.get("signaled", {}).keys()))
    blocked = result.get("blocked", {})

    print(f"[SIGNALS] signaled={signaled}")
    if blocked:
        print(f"[SIGNALS_BLOCKED] blocked={blocked}")

    print("[VALIDATION] OpeningExecutor executed successfully")
    log.info("BOT EXIT CLEAN")


if __name__ == "__main__":
    main()
