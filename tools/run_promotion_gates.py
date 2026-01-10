from __future__ import annotations
from _bootstrap import bootstrap
bootstrap()


import sys
from pathlib import Path

# ✅ Make project root importable (so `import Core...` works)
REPO_ROOT = Path(__file__).resolve().parents[1]  # BotTrader/
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Core.promotion.promotion_suite import run_promotion_suite, write_metrics_yaml


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python \"Testing Rules/run_promotion_gates.py\" <strategy_id>")
        return 2

    strategy_id = sys.argv[1].strip()

    res = run_promotion_suite(REPO_ROOT, strategy_id)
    out_path = write_metrics_yaml(REPO_ROOT, strategy_id, res.metrics)

    print(f"\nWrote: {out_path}")
    print("\n=== STEP 20 — Promotion Suite Results ===")
    for k, v in res.metrics.items():
        print(f"{k}: {v}")

    if res.passed:
        print("\nPromotion Suite: PASS ✅")
        return 0

    print("\nPromotion Suite: FAIL ❌")
    for r in res.reasons:
        print(f" - {r}")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())