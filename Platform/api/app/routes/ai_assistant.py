"""
AI Assistant API routes (upgraded — LLM-powered with guardrails).

POST /api/ai/chat     — conversational assistant (JSON or SSE)
GET  /api/ai/overview  — cached market briefing
POST /api/ai/feedback  — user feedback on AI messages
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.dependencies import get_current_user
from app.models.user import User
from app.services.ai.cache import ai_cache
from app.services.ai.client import chat_completion, chat_completion_stream
from app.services.ai.guardrails import log_audit
from app.services.ai.prompts import build_chat_messages, build_overview_messages
from app.services.ai.rate_limit import ai_rate_limiter
from app.services.ai.schemas import (
    SAFE_FALLBACK,
    AIResponseSchema,
    ChatRequest,
    FeedbackRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])


# ---------------------------------------------------------------------------
# Internal: gather tool data for context
# ---------------------------------------------------------------------------


def _gather_tool_data(tickers: list[str] | None) -> dict[str, Any]:
    """Call data endpoints internally to build context for the AI model."""
    from app.routes.data import (
        get_fundamentals,
        get_news,
        get_quote,
        get_technicals,
    )

    if not tickers:
        return {}

    context: dict[str, Any] = {}
    for ticker in tickers[:5]:  # Cap at 5 tickers
        parts = []
        quote = get_quote(ticker)
        if "error" not in quote:
            parts.append(f"Quote: price=${quote['price']}, change={quote['changePct']}%")

        fund = get_fundamentals(ticker)
        if "error" not in fund:
            parts.append(
                f"Fundamentals: P/E={fund.get('peRatio')}, "
                f"MarketCap={fund.get('marketCap')}, "
                f"DivYield={fund.get('dividendYield')}%"
            )

        tech = get_technicals(ticker)
        if "error" not in tech:
            parts.append(
                f"Technicals: RSI={tech.get('rsi14')}, "
                f"SMA50={tech.get('sma50')}, SMA200={tech.get('sma200')}, "
                f"MACD={tech.get('macdSignal')}, RealizedVol={tech.get('realizedVol30d')}%"
            )

        news = get_news(ticker, limit=3)
        if news.get("items"):
            headlines = "; ".join(
                f"{n['headline']} ({n['sentiment']})" for n in news["items"]
            )
            parts.append(f"Recent news: {headlines}")

        if parts:
            context[ticker] = "\n".join(parts)

    return context


# ---------------------------------------------------------------------------
# POST /api/ai/chat
# ---------------------------------------------------------------------------


@router.post("/chat")
async def ai_chat(
    body: ChatRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    # Rate limit
    if not ai_rate_limiter.allow(user.id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment.")

    tickers = body.context.tickers if body.context else None
    view = body.context.view if body.context else None

    # Gather data context
    tool_data = _gather_tool_data(tickers)

    messages = build_chat_messages(
        body.message, tickers=tickers, view=view, tool_data=tool_data
    )

    # Check if client wants streaming
    accept = request.headers.get("accept", "")
    wants_stream = "text/event-stream" in accept

    if wants_stream:
        return StreamingResponse(
            _stream_sse(messages, user_id=user.id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming JSON response
    message_id = str(uuid.uuid4())
    result = chat_completion(messages, user_id=user.id, endpoint="chat")

    return JSONResponse(
        content={
            "message_id": message_id,
            **result.model_dump(),
        }
    )


async def _stream_sse(messages: list, user_id: int | str | None = None):
    """Generator that yields SSE events from the streaming AI response."""
    message_id = str(uuid.uuid4())

    yield f"data: {json.dumps({'type': 'start', 'message_id': message_id})}\n\n"

    collected_chunks: list[str] = []
    compliance_replacement = None

    async for chunk in chat_completion_stream(messages, user_id=user_id):
        if chunk.startswith("\n\n[COMPLIANCE_REPLACE]"):
            # Guardrails detected non-compliant output
            compliance_replacement = chunk.replace("\n\n[COMPLIANCE_REPLACE]", "")
            break
        collected_chunks.append(chunk)
        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

    if compliance_replacement:
        # Send the compliant replacement as a full message
        yield f"data: {json.dumps({'type': 'replace', 'content': compliance_replacement})}\n\n"
    else:
        # Send the final complete response for client-side assembly
        full_text = "".join(collected_chunks)
        yield f"data: {json.dumps({'type': 'done', 'message_id': message_id, 'full_text': full_text})}\n\n"

    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# GET /api/ai/overview
# ---------------------------------------------------------------------------


@router.get("/overview")
def ai_overview(
    tickers: str = Query("", description="Comma-separated tickers"),
    timeframe: str = Query("daily", pattern="^(daily|weekly)$"),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()] or None

    # Check cache
    cache_key = ("overview", tickers, timeframe)
    cached = ai_cache.get(*cache_key)
    if cached is not None:
        return {"cached": True, **cached}

    # Rate limit
    if not ai_rate_limiter.allow(user.id, cost=2.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment.")

    # Gather data
    tool_data = _gather_tool_data(ticker_list)

    messages = build_overview_messages(
        tickers=ticker_list, timeframe=timeframe, tool_data=tool_data
    )

    result = chat_completion(messages, user_id=user.id, endpoint="overview")
    result_dict = result.model_dump()

    # Cache the result
    ai_cache.set(result_dict, *cache_key)

    return {"cached": False, **result_dict}


# ---------------------------------------------------------------------------
# POST /api/ai/feedback
# ---------------------------------------------------------------------------


@router.post("/feedback")
def ai_feedback(
    body: FeedbackRequest,
    user: User = Depends(get_current_user),
) -> Dict[str, str]:
    log_audit(
        original=None,
        violations=[],
        rewrite_attempted=False,
        final_output={"feedback": body.rating, "notes": body.notes},
        user_id=user.id,
        endpoint="feedback",
    )
    logger.info(
        "AI feedback: user=%s message=%s rating=%s",
        user.id,
        body.message_id,
        body.rating,
    )
    return {"status": "ok"}
