"""Pydantic models for Apter Conviction Score API responses."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BandInfo(BaseModel):
    label: str
    color: str


class PillarScores(BaseModel):
    quality: float = Field(..., ge=0, le=10)
    value: float = Field(..., ge=0, le=10)
    growth: float = Field(..., ge=0, le=10)
    momentum: float = Field(..., ge=0, le=10)
    risk: float = Field(..., ge=0, le=10)


class DriverItem(BaseModel):
    name: str
    impact: float
    detail: str


class Drivers(BaseModel):
    positive: List[DriverItem]
    negative: List[DriverItem]


class PenaltyOrCap(BaseModel):
    type: str  # "cap" or "penalty"
    name: str
    value: float
    reason: str


class ConvictionScoreResponse(BaseModel):
    ticker: str
    overall_score: float = Field(..., ge=0, le=10)
    band: BandInfo
    pillars: PillarScores
    drivers: Drivers
    penalties_and_caps_applied: List[PenaltyOrCap]
    confidence: int = Field(..., ge=0, le=100)
    model_version: str
    computed_at: str


class BatchScoreRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, max_length=50)


class BatchScoreResponse(BaseModel):
    results: List[ConvictionScoreResponse]
    errors: List[dict] = []


# ─── Market Data / Quotes ───

class QuoteData(BaseModel):
    symbol: str
    price: float
    change: float = 0.0
    change_pct: float = 0.0
    as_of: str
    session: str = "REGULAR"  # REGULAR | AFTER_HOURS | PRE_MARKET
    delay_seconds: int = 0
    source: str = "internal"
    error: Optional[str] = None


class QuotesResponse(BaseModel):
    quotes: dict  # symbol -> QuoteData dict
    meta: dict


class SingleQuoteResponse(BaseModel):
    symbol: str
    price: float
    change: float = 0.0
    change_pct: float = 0.0
    as_of: str
    session: str = "REGULAR"
    delay_seconds: int = 0
    source: str = "internal"


# ─── AI Overview ───

class SnapshotData(BaseModel):
    price: Optional[float] = None
    day_change_pct: Optional[float] = None
    volume: Optional[int] = None


class OutlookData(BaseModel):
    base_case: str
    bull_case: str
    bear_case: str
    probabilities: dict


class NewsItemAI(BaseModel):
    headline: str
    source: Optional[str] = None
    published_at: Optional[str] = None
    impact: str = "neutral"


class AIOverviewResponse(BaseModel):
    ticker: str
    as_of: str
    snapshot: SnapshotData
    performance: dict
    drivers: List[str]
    outlook: OutlookData
    news: List[NewsItemAI]
    what_to_watch: List[str]
    disclaimer: str


# ─── Chat ───

class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    intent: str
    ticker: Optional[str] = None
    response: dict
