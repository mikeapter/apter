from __future__ import annotations
from _bootstrap import bootstrap
bootstrap()


from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from App.opening_executor import OpeningExecutor

# STEP 21 (LIGHT): trade logging only
from Core.monitoring.trade_logger import TradeLogger


class FakeMarketDataClient:
    def __init__(self) -> None:
        self._prev_close = 100.0
        self._pm_last = 105.0
        self._pm_vol = 2_000_000
        self._last_trade = 104.8
        self._bid = 104.79
        self._ask = 104.81

    def get_prev_close(self, symbol: str) -> float:
        return float(self._prev_close)

    def get_premarket_last(self, symbol: str) -> float:
        return float(self._pm_last)

    def get_premarket_volume(self, symbol: str) -> int:
        return int(self._pm_vol)

    def get_last_trade(self, symbol: str) -> float:
        px = float(self._last_trade)
        print(f"[FAKE] get_last_trade({symbol}) -> {px}")
        return px

    def get_bid_ask(self, symbol: str) -> Tuple[float, float]:
        return float(self._bid), float(self._ask)

    def has_real_catalyst(self, symbol: str) -> bool:
        return True

    def get_fill_probability(self, symbol: str, side: Optional[str], order_size: float) -> float:
        return 0.78

    def get_expected_fill_time_s(self, symbol: str, side: Optional[str], order_size: float) -> float:
        return 0.63

    def get_trend_direction(self, symbol: str) -> int:
        return -1 if symbol.upper() == "SPY" else +1

    def get_persistence_score(self, symbol: str) -> float:
        return 2.5


@dataclass
class PaperOrderExecutor:
    _n: int = 0

    def place_order(
        self,
        *,
        strategy_id: str,
        symbol: str,
        side: str,
        qty: int,
        type: str = "market",
        meta: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        self._n += 1
        oid = f"paper-{self._n}"
        print(
            f"[PAPER] place_order | id={oid} | strategy_id={strategy_id} | "
            f"symbol={symbol} | side={side} | qty={qty} | type={type}"
        )
        return {
            "status": "PAPER",
            "id": oid,
            "strategy_id": strategy_id,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "type": type,
            "meta": meta or {},
            # helpful defaults for TCA
            "fill_price": (meta or {}).get("quote", {}).get("mid") or (meta or {}).get("mid") or (meta or {}).get("last"),
        }


def log_blocked(logger: TradeLogger, *, blocked: Dict[str, str], data: FakeMarketDataClient) -> None:
    # Write a monitoring record even when executor was never called.
    for sym, reason in (blocked or {}).items():
        bid, ask = data.get_bid_ask(sym)
        mid = (bid + ask) / 2.0
        meta = {
            "regime": "UNKNOWN",
            "reason": reason,
            "quote": {"bid": bid, "ask": ask, "mid": mid, "last": data.get_last_trade(sym)},
            "arrival_price": mid,
        }
        logger.log_from_result(
            symbol=sym,
            side="NA",
            qty=0,
            strategy="OPENING_PLAYBOOK",
            meta=meta,
            result={"status": "BLOCKED", "reason": reason},
            broker="SIM",
            venue=None,
            order_type=None,
            started_ts=None,
        )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    config_dir = root / "Config"
    opening_cfg = config_dir / "opening_playbook.yaml"

    print(f"[RUN] root={root}")
    print(f"[RUN] config_dir={config_dir}")
    print(f"[RUN] opening_cfg={opening_cfg}")

    data_client = FakeMarketDataClient()
    order_exec = PaperOrderExecutor()

    trade_logger = TradeLogger(repo_root=root)

    ex = OpeningExecutor(
        data=data_client,
        order_exec=order_exec,
        repo_root=root,
        config_path=opening_cfg,
    )

    result = ex.run_one_shot()
    print("[RUN] completed run_one_shot()")

    # STEP 21: if opening_executor returns blocked dict, log it.
    if isinstance(result, dict) and isinstance(result.get("blocked"), dict):
        log_blocked(trade_logger, blocked=result["blocked"], data=data_client)
        print(f"[RUN] logged BLOCKED events: {len(result['blocked'])}")
    else:
        print("[RUN] NOTE: run_one_shot() did not return a blocked dict. Patch opening_executor.py to return it.")


if __name__ == "__main__":
    main()