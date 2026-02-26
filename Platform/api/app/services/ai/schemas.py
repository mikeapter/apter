"""Structured response schemas for Apter Intelligence service outputs."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AIResponseSchema(BaseModel):
    """Structured AI response -- every field must be non-RIA compliant."""

    summary: str = Field(..., description="One-paragraph factual summary")
    data_used: List[str] = Field(
        default_factory=list,
        description="Data sources referenced (tickers, endpoints, etc.)",
    )
    explanation: str = Field(
        ..., description="Educational explanation of the analysis"
    )
    watchlist_items: List[str] = Field(
        default_factory=list, description="Tickers mentioned for monitoring"
    )
    risk_flags: List[str] = Field(
        default_factory=list, description="Descriptive risk observations"
    )
    checklist: List[str] = Field(
        default_factory=list, description="Things to monitor / consider"
    )
    disclaimer: str = Field(
        default="Not investment advice.",
        description="Must always include the standard disclaimer",
    )
    citations: List[str] = Field(
        default_factory=list,
        description="Source URLs or internal identifiers",
    )
    scenarios: Optional[List[str]] = Field(
        default=None, description="Optional scenario descriptions"
    )
    comparisons: Optional[List[str]] = Field(
        default=None, description="Optional comparison notes"
    )


class ChatContext(BaseModel):
    tickers: Optional[List[str]] = None
    view: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    context: Optional[ChatContext] = None


class FeedbackRequest(BaseModel):
    message_id: str
    rating: str = Field(..., pattern="^(helpful|not_helpful)$")
    notes: Optional[str] = None


SAFE_FALLBACK = AIResponseSchema(
    summary="Apter Intelligence is available to analyze stocks, market conditions, and financial metrics. Ask about a specific ticker or market topic for a data-driven breakdown.",
    data_used=["Quotes", "Fundamentals", "Financials", "Technicals", "News"],
    explanation="Try questions like 'Break down AAPL earnings' or 'Compare MSFT vs GOOG revenue growth' for structured, data-driven analysis.",
    watchlist_items=[],
    risk_flags=[
        "All investing involves risk including potential loss of principal"
    ],
    checklist=[
        "Define your own research criteria",
        "Consult a qualified financial advisor for personalized guidance",
        "Review official filings and disclosures before making decisions",
    ],
    disclaimer="Not investment advice.",
    citations=[],
)


# ---------------------------------------------------------------------------
# Stock Intelligence Brief schema
# ---------------------------------------------------------------------------


class RiskTagItem(BaseModel):
    category: str = Field(..., description="e.g. Competitive, Regulatory, Margin, Macro, Execution")
    level: str = Field(..., description="Low | Moderate | Elevated")


class StockIntelligenceBrief(BaseModel):
    ticker: str
    executive_summary: str = Field(..., description="5-8 sentence institutional-grade summary")
    key_drivers: List[str] = Field(default_factory=list)
    risk_tags: List[RiskTagItem] = Field(default_factory=list)
    regime_context: str = Field(default="Neutral", description="Risk-On | Neutral | Risk-Off")
    what_to_monitor: List[str] = Field(default_factory=list)
    snapshot: Dict[str, Optional[str]] = Field(default_factory=dict)
    as_of: str = ""
    disclaimer: str = "For informational/educational use only. Not investment advice."
    data_sources: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Market Intelligence Brief schema
# ---------------------------------------------------------------------------


class RiskDashboard(BaseModel):
    regime: str = Field(default="Neutral", description="Risk-On | Neutral | Risk-Off")
    volatility_context: str = ""
    breadth_context: str = ""


class MarketIntelligenceBrief(BaseModel):
    executive_summary: str = Field(..., description="Short paragraph market overview")
    risk_dashboard: RiskDashboard = Field(default_factory=RiskDashboard)
    catalysts: List[str] = Field(default_factory=list)
    what_changed: List[str] = Field(default_factory=list, description="Max 3 bullets")
    as_of: str = ""
    disclaimer: str = "For informational/educational use only. Not investment advice."
    data_sources: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Apter Rating schema
# ---------------------------------------------------------------------------


class RatingComponent(BaseModel):
    score: float = Field(ge=0, le=10)
    weight: float
    drivers: List[str] = Field(default_factory=list)


class AptRatingResponse(BaseModel):
    ticker: str
    rating: float = Field(ge=0, le=10)
    band: str
    components: Dict[str, RatingComponent]
    as_of: str = ""
    disclaimer: str = (
        "Apter Rating (1-10) is a proprietary composite research score derived "
        "from quantitative financial metrics, market structure indicators, and "
        "risk analysis. Informational only. Not investment advice."
    )
