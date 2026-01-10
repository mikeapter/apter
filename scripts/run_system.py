# scripts/run_system.py
from __future__ import annotations

import argparse

from Core.system_builder import build_system


class SimpleOrder:
    def __init__(self, symbol: str, side: str, qty: int, strategy_id: str) -> None:
        self.symbol = symbol
        self.side = side
        self.qty = int(qty)
        self.strategy_id = strategy_id


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["PAPER", "SIM", "PILOT", "LIVE"])
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--qty", type=int, required=True)
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--regime", required=True)
    ap.add_argument("--regime_conf", type=float, required=True)
    ap.add_argument("--nav", type=float, default=100000)
    ap.add_argument("--equity", type=float, default=100000)
    ap.add_argument("--cash", type=float, default=0)
    ap.add_argument("--price", type=float, default=100.0)
    ap.add_argument("--config_dir", default="Config")
    return ap.parse_args()


def main():
    args = parse_args()
    engine = build_system(config_dir=args.config_dir)

    meta = {
        "mode": args.mode,
        "regime": args.regime,
        "regime_conf": args.regime_conf,
        "portfolio": {
            "nav": args.nav,
            "equity": args.equity,
            "cash": args.cash,
            "positions": [],
            "risk_metrics": {"var_95": 0.0, "var_99": 0.0, "es_97_5": 0.0},
        },
        # include for VaR gate if you want it to trigger in live runs:
        # "var_95_increment": 0.005,
    }

    order = SimpleOrder(args.symbol, "BUY", args.qty, args.strategy)
    decision = engine.evaluate(order, meta=meta, price=float(args.price))

    print("ALLOWED:", decision.allowed)
    print("ACTION:", decision.action)
    print("FINAL_QTY:", decision.qty)
    print("REASON:", decision.reason)
    print("DETAILS:", decision.details)


if __name__ == "__main__":
    main()
