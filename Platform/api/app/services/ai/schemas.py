"""Structured response schemas for AI service outputs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SectorNote(BaseModel):
    """A sector with an explanatory note."""

    sector: str = Field(..., description="Sector name")
    note: str = Field("", description="Brief context")


class WatchlistFocusItem(BaseModel):
    """A ticker from the user's watchlist with relevance context."""

    ticker: str
    note: str = Field("", description="Why it matters right now")


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

    # -- Daily Brief structured sections (populated by overview endpoint) --
    market_regime: Optional[Dict[str, Any]] = Field(
        default=None,
        description='{"label": "RISK-ON"|"NEUTRAL"|"RISK-OFF", "rationale": ["bullet1", ...]}',
    )
    breadth_internals: Optional[List[str]] = Field(
        default=None,
        description="Advance/decline, leaders/laggards, volatility tone",
    )
    sector_rotation: Optional[Dict[str, Any]] = Field(
        default=None,
        description='{"strong": [{"sector": "...", "note": "..."}], "weak": [...]}',
    )
    key_drivers: Optional[List[str]] = Field(
        default=None,
        description="Macro, earnings, or thematic drivers (3-6 bullets)",
    )
    watchlist_focus: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description='[{"ticker": "AAPL", "note": "why it matters"}]',
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
