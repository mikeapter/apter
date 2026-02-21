"""Structured response schemas for AI service outputs."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class AIResponseSchema(BaseModel):
    """Structured AI response — every field must be non-RIA compliant."""

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
    summary="I can pull real-time quotes, fundamentals, financials, technicals, and news for any ticker. Try asking about a specific stock or market topic.",
    data_used=["Quotes", "Fundamentals", "Financials", "Technicals", "News"],
    explanation="Ask me things like 'Break down AAPL earnings' or 'Compare MSFT vs GOOG revenue growth' — I'll fetch the relevant data and walk you through it.",
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
