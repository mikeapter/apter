from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, TypedDict, Literal


Mode = Literal["PAPER", "PILOT", "LIVE"]
Side = Literal["BUY", "SELL"]


class PriceContext(TypedDict, total=False):
    bid: float
    ask: float
    mid: float
    last: float
    spread_bps: float
    quote_ts: float


class RegimeInfo(TypedDict, total=False):
    label: str
    confidence: float


class DataLineage(TypedDict, total=False):
    source: str
    acquisition_ts: float
    cleaning_version: str
    corporate_action_version: str
    serialization_id: str
    model_version: str


class DecisionTraceItem(TypedDict, total=False):
    module: str
    allowed: bool
    reason: str
    decision: Dict[str, Any]


class TradeMeta(TypedDict, total=False):
    run_id: str
    mode: Mode
    ts: float
    strategy_id: str
    symbol: str
    side: Side
    qty: int
    price_context: PriceContext
    regime: RegimeInfo
    data_lineage: DataLineage
    config_hash: str
    code_hash: str
    git_commit: str
    decision_trace: list[DecisionTraceItem]


@dataclass(frozen=True)
class GateOutcome:
    allowed: bool
    reason: str
    extras: Optional[Dict[str, Any]] = None
