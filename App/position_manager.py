from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Literal
import time

Side = Literal["BUY", "SELL"]


@dataclass
class Position:
    symbol: str
    side: Side
    qty: int
    entry_price: float
    stop_price: float
    entry_time: float  # perf_counter timestamp

    r_value: float            # $/share risk (abs(entry - stop))
    partial_targets: List[float]  # in R multiples (e.g., 0.5R, 1R)
    taken_partials: int = 0

    breakeven_moved: bool = False


def _pnl_R(pos: Position, price: float) -> float:
    # Positive is favorable
    if pos.side == "BUY":
        return (price - pos.entry_price) / pos.r_value
    else:
        return (pos.entry_price - price) / pos.r_value


def maybe_manage_position(
    *,
    pos: Position,
    price: float,
    now: float,
    time_stop_seconds: int,
    loser_kill_R: float,
    move_stop_to_breakeven_after_first_partial: bool,
) -> dict:
    """
    Returns an action dict:
      {"action": "HOLD"} or {"action":"EXIT","reason":...} or {"action":"PARTIAL","qty":...,"reason":...}
    """
    r = _pnl_R(pos, price)

    # Kill losers instantly at loser_kill_R (ex: -0.5R)
    if r <= loser_kill_R:
        return {"action": "EXIT", "reason": f"Loser kill: {r:.2f}R <= {loser_kill_R:.2f}R"}

    # Full stop
    if (pos.side == "BUY" and price <= pos.stop_price) or (pos.side == "SELL" and price >= pos.stop_price):
        return {"action": "EXIT", "reason": "Stop hit"}

    # Time stop
    if (now - pos.entry_time) >= float(time_stop_seconds):
        return {"action": "EXIT", "reason": f"Time stop: {time_stop_seconds}s"}

    # Take partials quickly
    if pos.taken_partials < len(pos.partial_targets):
        target_R = pos.partial_targets[pos.taken_partials]
        if r >= target_R:
            # take 1/2 then 1/2 of remaining (simple)
            if pos.qty <= 1:
                return {"action": "HOLD"}

            sell_qty = max(1, pos.qty // 2)
            pos.qty -= sell_qty
            pos.taken_partials += 1

            # Move stop to breakeven after first partial
            if move_stop_to_breakeven_after_first_partial and not pos.breakeven_moved and pos.taken_partials >= 1:
                pos.stop_price = pos.entry_price
                pos.breakeven_moved = True

            return {"action": "PARTIAL", "qty": sell_qty, "reason": f"Partial at {target_R:.2f}R"}

    return {"action": "HOLD"}
