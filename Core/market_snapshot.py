# Core/market_snapshot.py

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MarketSnapshot:
    """
    Canonical immutable snapshot of market state.
    This object is the ONLY allowed market data carrier
    across execution, throttles, and risk gates.
    """

    # --- Time ---
    ts_utc: datetime

    # --- Prices ---
    bid: float
    ask: float
    last: float

    # --- Liquidity ---
    adv: float
    top_of_book_size: int

    # --- Execution signals ---
    volatility_score: float
    fill_probability_est: float
    impact_bps_est: float

    # --- Derived helpers ---
    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float:
        return self.ask - self.bid

    @property
    def spread_bps(self) -> float:
        if self.mid <= 0:
            return 0.0
        return (self.spread / self.mid) * 10_000
