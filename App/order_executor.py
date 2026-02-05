from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class OrderRequest:
    symbol: str
    side: str
    qty: int
    urgency: float = 0.0
    preferred_order_type: str = "MARKET"


@dataclass
class MarketSnapshot:
    ts: datetime
    bid: float = 100.0
    ask: float = 100.1
    adv: int = 1_000_000
    tob: int = 100


@dataclass
class ExecutionDecision:
    approved: bool
    order_type: Optional[str] = None
    reason: Optional[str] = None


def _is_first_or_last_5_minutes(ts: datetime) -> bool:
    """
    Market assumed open 14:30–21:00 UTC (NYSE regular session).
    Blocks first and last 5 minutes.
    """
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    minutes_since_open = (ts.hour * 60 + ts.minute) - (14 * 60 + 30)
    minutes_until_close = (21 * 60) - (ts.hour * 60 + ts.minute)

    return minutes_since_open < 5 or minutes_until_close <= 5


def decide_execution(req: OrderRequest, mkt: MarketSnapshot) -> ExecutionDecision:
    # 🚫 Hard block: STOP-MARKET orders
    if req.preferred_order_type.upper() == "STOP_MARKET":
        return ExecutionDecision(
            approved=False,
            reason="STOP_MARKET orders are blocked by execution policy",
        )

    # 🚫 Block first / last 5 minutes
    if _is_first_or_last_5_minutes(mkt.ts):
        return ExecutionDecision(
            approved=False,
            reason="Trade blocked during first/last 5 minutes of market session",
        )

    # 🟡 Thin liquidity handling
    spread = mkt.ask - mkt.bid
    if req.preferred_order_type.upper() == "MARKET":
        if mkt.adv < 5_000 or mkt.tob < 25 or spread > 0.5:
            return ExecutionDecision(
                approved=True,
                order_type="LIMIT",
                reason="MARKET order converted to LIMIT due to thin liquidity",
            )

    # ✅ Default approval
    return ExecutionDecision(
        approved=True,
        order_type=req.preferred_order_type.upper(),
        reason="Approved for execution",
    )
class OrderExecutor:
    """
    Thin execution wrapper required by tests and future runtime wiring.
    """

    def decide(self, req: OrderRequest, mkt: MarketSnapshot) -> ExecutionDecision:
        return decide_execution(req, mkt)
