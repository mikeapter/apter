from _bootstrap import bootstrap
bootstrap()

from pathlib import Path
import sys

# Ensure BotTrader/ is on the import path when running from "Testing Rules/"
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

import App.guardrails as gr


def _get_loader():
    """
    Your guardrails.py might name the loader differently.
    We'll try common names and use whichever exists.
    """
    candidates = [
        "load_guardrail_gate",
        "load_guardrails",
        "load_gate",
        "load_guardrail",
        "load_guardrails_gate",
    ]
    for name in candidates:
        if hasattr(gr, name):
            return getattr(gr, name), name

    available = [n for n in dir(gr) if n.startswith("load")]
    raise RuntimeError(
        "Could not find a loader function in guardrails.py.\n"
        f"Tried: {candidates}\n"
        f"Found load* functions: {available}\n"
        "Fix: add a function named load_guardrail_gate(base_dir) in BotTrader/guardrails.py."
    )


def run_case(name: str, state: dict):
    loader, loader_name = _get_loader()
    gate = loader(BASE_DIR)
    d = gate.evaluate(state)

    print("\n==", name, "==")
    print(f"loader: {loader_name}")
    print(f"status: {d.status} | allowed_new_entries: {d.allowed_new_entries} | risk_multiplier: {d.risk_multiplier:.2f}")

    if getattr(d, "reasons", None):
        print("reasons:")
        for r in d.reasons:
            print(" -", r)

    if getattr(d, "actions", None):
        print("actions:")
        for a in d.actions:
            print(" -", a)


if __name__ == "__main__":
    base_state = {
        # All values are in percent units: -1.2 means -1.2%
        "day_pnl_pct": 0.0,
        "var_95_1d_pct": 1.0,
        "ann_vol_pct": 12.0,
        "drawdown_pct": 0.0,
    }

    run_case("OK (baseline)", base_state)

    s = dict(base_state); s["day_pnl_pct"] = -2.1
    run_case("RESTRICT (no new entries)", s)

    s = dict(base_state); s["day_pnl_pct"] = -3.2
    run_case("HALT (intraday)", s)

    s = dict(base_state); s["var_95_1d_pct"] = 2.5
    run_case("APPROACH (VaR)", s)

    s = dict(base_state); s["var_95_1d_pct"] = 3.2
    run_case("HALT (VaR breach)", s)

    s = dict(base_state); s["ann_vol_pct"] = 14.6
    run_case("APPROACH (vol high)", s)

    s = dict(base_state); s["drawdown_pct"] = 12.0
    run_case("APPROACH (drawdown ladder throttle)", s)

    s = dict(base_state); s["drawdown_pct"] = 21.0
    run_case("HALT (max drawdown breach)", s)