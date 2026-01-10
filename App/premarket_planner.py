from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Literal, Any
import yaml


State = Literal["CONTINUATION", "FADE", "NO_TRADE"]
Side = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class PremarketSnapshot:
    symbol: str
    prev_close: float
    premarket_price: float
    premarket_volume: int
    bid: float
    ask: float
    avg_daily_volume: int
    price: float
    has_catalyst: bool

    @property
    def gap_pct(self) -> float:
        if self.prev_close <= 0:
            return 0.0
        return (self.premarket_price - self.prev_close) / self.prev_close

    @property
    def spread_pct(self) -> float:
        mid = (self.bid + self.ask) / 2.0
        if mid <= 0:
            return 1.0
        return (self.ask - self.bid) / mid


@dataclass(frozen=True)
class TradePlan:
    symbol: str
    state: State
    side: Side
    max_qty: int
    max_slippage_bps: float
    stop_distance_pct: float
    kill_after_seconds: int

    # execution thresholds (precomputed)
    opening_range_seconds: int
    min_rel_volume: float
    max_spread_pct: float

    # position mgmt
    partials_R: List[float]
    time_stop_seconds: int
    loser_kill_R: float
    move_stop_to_breakeven_after_first_partial: bool


def load_opening_playbook(path: str = "config/opening_playbook.yaml") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# -------------------------
# DATA FEED STUBS (replace later with real feeds)
# -------------------------
def get_premarket_snapshot_stub(symbol: str) -> PremarketSnapshot:
    # You will replace this with real premarket data.
    prev_close = 100.0
    pre = 102.5  # +2.5% gap
    vol = 350_000
    bid, ask = 102.45, 102.55
    adv = 5_000_000
    price = pre
    has_catalyst = True
    return PremarketSnapshot(
        symbol=symbol,
        prev_close=prev_close,
        premarket_price=pre,
        premarket_volume=vol,
        bid=bid,
        ask=ask,
        avg_daily_volume=adv,
        price=price,
        has_catalyst=has_catalyst,
    )


# -------------------------
# PREOPEN PLANNER (fast)
# -------------------------
def classify_state(cfg: Dict[str, Any], snap: PremarketSnapshot) -> State:
    fade_gap = float(cfg["state_rules"]["fade_gap_abs_pct"])
    if abs(snap.gap_pct) >= fade_gap:
        return "FADE"
    return "CONTINUATION"


def decide_side(state: State, snap: PremarketSnapshot) -> Side:
    # Continuation: follow gap direction
    # Fade: go opposite gap direction
    if state == "NO_TRADE":
        return "BUY"
    gap_up = snap.gap_pct >= 0
    if state == "CONTINUATION":
        return "BUY" if gap_up else "SELL"
    # FADE
    return "SELL" if gap_up else "BUY"


def is_tradable_today(cfg: Dict[str, Any], snap: PremarketSnapshot) -> bool:
    u = cfg["universe"]
    pf = cfg["premarket_filters"]

    if snap.price < float(u["min_price"]):
        return False
    if snap.avg_daily_volume < int(u["min_avg_daily_volume"]):
        return False
    if abs(snap.gap_pct) < float(pf["gap_abs_min_pct"]):
        return False
    if snap.premarket_volume < int(pf["premarket_volume_min"]):
        return False
    if snap.spread_pct > float(pf["max_spread_pct"]):
        return False
    if bool(pf["require_catalyst"]) and not snap.has_catalyst:
        return False

    return True


def build_trade_plan(cfg: Dict[str, Any], snap: PremarketSnapshot) -> TradePlan:
    state = classify_state(cfg, snap)
    side = decide_side(state, snap)

    r = cfg["risk"]
    ex = cfg["execution"]
    pm = cfg["position_mgmt"]

    return TradePlan(
        symbol=snap.symbol,
        state=state,
        side=side,
        max_qty=int(r["max_qty"]),
        max_slippage_bps=float(r["max_slippage_bps"]),
        stop_distance_pct=float(r["stop_distance_pct"]),
        kill_after_seconds=int(r["kill_after_seconds"]),
        opening_range_seconds=int(ex["opening_range_seconds"]),
        min_rel_volume=float(ex["min_rel_volume"]),
        max_spread_pct=float(ex["max_spread_pct"]),
        partials_R=list(pm["partials_R"]),
        time_stop_seconds=int(pm["time_stop_seconds"]),
        loser_kill_R=float(pm["loser_kill_R"]),
        move_stop_to_breakeven_after_first_partial=bool(pm["move_stop_to_breakeven_after_first_partial"]),
    )


def preopen_plan(cfg: Dict[str, Any]) -> List[TradePlan]:
    symbols = list(cfg["universe"]["symbols"])
    plans: List[TradePlan] = []

    for sym in symbols:
        snap = get_premarket_snapshot_stub(sym)
        if not is_tradable_today(cfg, snap):
            continue
        plan = build_trade_plan(cfg, snap)
        if plan.state != "NO_TRADE":
            plans.append(plan)

    return plans
