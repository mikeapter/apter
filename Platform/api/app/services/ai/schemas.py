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
        default="Educational information only — not investment advice.",
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
    summary="I can provide educational market information. Please ask a specific question about market data, financial concepts, or analytical frameworks.",
    data_used=[],
    explanation="This platform offers factual market data summaries, analytical framework explanations, risk factor descriptions, and educational financial content. All information is general in nature and not tailored to any individual.",
    watchlist_items=[],
    risk_flags=[
        "All investing involves risk including potential loss of principal"
    ],
    checklist=[
        "Define your own research criteria",
        "Consult a qualified financial advisor for personalized guidance",
        "Review official filings and disclosures before making decisions",
    ],
    disclaimer="Educational information only — not investment advice.",
    citations=[],
)
