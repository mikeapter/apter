"""
Apter Intelligence API routes (LLM-powered with guardrails).

POST /api/ai/chat                   -- conversational assistant (JSON or SSE)
GET  /api/ai/overview               -- cached market briefing (legacy)
GET  /api/ai/intelligence/stock     -- Stock Intelligence Brief
GET  /api/ai/intelligence/market    -- Market Intelligence Brief
POST /api/ai/feedback               -- user feedback on AI messages
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.dependencies import get_current_user
from app.models.user import User
from app.services.ai.cache import ai_cache
from app.services.ai.client import chat_completion, chat_completion_stream
from app.services.ai.guardrails import log_audit
from app.services.ai.prompts import (
    build_chat_messages,
    build_market_intelligence_messages,
    build_overview_messages,
    build_stock_intelligence_messages,
)
from app.services.ai.rate_limit import ai_rate_limiter
from app.services.ai.schemas import (
    SAFE_FALLBACK,
    AIResponseSchema,
    ChatRequest,
    FeedbackRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["Apter Intelligence"])


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
    for ticker in tickers[:5]:
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


def _gather_market_data() -> dict[str, Any]:
    """Gather broad market data for the market intelligence brief."""
    from app.routes.data import get_quote, get_technicals

    context: dict[str, Any] = {}
    indices = ["SPY", "QQQ"]
    for idx in indices:
        parts = []
        quote = get_quote(idx)
        if "error" not in quote:
            parts.append(f"Price: ${quote['price']}, Change: {quote['changePct']}%")

        tech = get_technicals(idx)
        if "error" not in tech:
            parts.append(
                f"RSI={tech.get('rsi14')}, SMA50={tech.get('sma50')}, "
                f"SMA200={tech.get('sma200')}, Vol30d={tech.get('realizedVol30d')}%"
            )

        if parts:
            context[idx] = "\n".join(parts)

    sector_tickers = ["AAPL", "MSFT", "NVDA", "META", "JPM", "XOM"]
    for t in sector_tickers:
        quote = get_quote(t)
        if "error" not in quote:
            context[t] = f"Price: ${quote['price']}, Change: {quote['changePct']}%"

    return context


def _gather_stock_data(ticker: str) -> dict[str, Any]:
    """Gather comprehensive data for a single stock intelligence brief."""
    from app.routes.data import get_fundamentals, get_news, get_quote, get_technicals
    from app.services.market_data import get_stock_metrics, get_stock_name

    context: dict[str, Any] = {}
    parts = []

    name = get_stock_name(ticker)
    parts.append(f"Company: {name}")

    quote = get_quote(ticker)
    if "error" not in quote:
        parts.append(
            f"Price: ${quote['price']}, Day Change: {quote['changePct']}%, "
            f"Volume: {quote.get('volume', 'N/A')}"
        )

    fund = get_fundamentals(ticker)
    if "error" not in fund:
        parts.append(
            f"Market Cap: {fund.get('marketCap')}, P/E: {fund.get('peRatio')}, "
            f"PEG: {fund.get('pegRatio')}, Div Yield: {fund.get('dividendYield')}%, "
            f"Sector: {fund.get('sector')}, Industry: {fund.get('industry')}"
        )

    tech = get_technicals(ticker)
    if "error" not in tech:
        parts.append(
            f"RSI14: {tech.get('rsi14')}, SMA50: {tech.get('sma50')}, "
            f"SMA200: {tech.get('sma200')}, MACD: {tech.get('macdSignal')}, "
            f"ATR14: {tech.get('atr14')}, RealizedVol30d: {tech.get('realizedVol30d')}%"
        )

    metrics = get_stock_metrics(ticker)
    if metrics:
        quality = metrics.get("quality", {})
        value = metrics.get("value", {})
        growth = metrics.get("growth", {})
        momentum = metrics.get("momentum", {})
        risk = metrics.get("risk", {})

        parts.append(
            f"Quality: ROE={quality.get('roe')}%, ROIC={quality.get('roic')}%, "
            f"Gross Margin={quality.get('gross_margin')}%, "
            f"Op Margin={quality.get('operating_margin')}%, "
            f"FCF Margin={quality.get('fcf_margin')}%"
        )
        parts.append(
            f"Growth: Rev YoY={growth.get('revenue_growth_yoy')}%, "
            f"EPS YoY={growth.get('earnings_growth_yoy')}%, "
            f"FCF YoY={growth.get('fcf_growth_yoy')}%, "
            f"Rev 3Y CAGR={growth.get('revenue_growth_3y_cagr')}%"
        )
        parts.append(
            f"Value: P/E={value.get('pe_ratio')}, P/B={value.get('pb_ratio')}, "
            f"P/S={value.get('ps_ratio')}, EV/EBITDA={value.get('ev_ebitda')}, "
            f"FCF Yield={value.get('fcf_yield')}%"
        )
        parts.append(
            f"Momentum: vs SMA50={momentum.get('price_vs_sma50')}%, "
            f"vs SMA200={momentum.get('price_vs_sma200')}%, "
            f"1M Return={momentum.get('return_1m')}%, "
            f"3M Return={momentum.get('return_3m')}%"
        )
        parts.append(
            f"Risk: Vol30d={risk.get('volatility_30d')}%, "
            f"MaxDD 1Y={risk.get('max_drawdown_1y')}%, "
            f"D/E={risk.get('debt_to_equity')}, "
            f"Interest Coverage={risk.get('interest_coverage')}x, "
            f"Beta={risk.get('beta')}"
        )

    news_data = get_news(ticker, limit=3)
    if news_data.get("items"):
        headlines = "; ".join(
            f"{n['headline']} ({n['sentiment']})" for n in news_data["items"]
        )
        parts.append(f"Recent News: {headlines}")

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
    if not ai_rate_limiter.allow(user.id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment.")

    tickers = body.context.tickers if body.context else None
    view = body.context.view if body.context else None

    tool_data = _gather_tool_data(tickers)

    messages = build_chat_messages(
        body.message, tickers=tickers, view=view, tool_data=tool_data
    )

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
            compliance_replacement = chunk.replace("\n\n[COMPLIANCE_REPLACE]", "")
            break
        collected_chunks.append(chunk)
        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

    if compliance_replacement:
        yield f"data: {json.dumps({'type': 'replace', 'content': compliance_replacement})}\n\n"
    else:
        full_text = "".join(collected_chunks)
        yield f"data: {json.dumps({'type': 'done', 'message_id': message_id, 'full_text': full_text})}\n\n"

    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# GET /api/ai/overview (legacy)
# ---------------------------------------------------------------------------


@router.get("/overview")
def ai_overview(
    tickers: str = Query("", description="Comma-separated tickers"),
    timeframe: str = Query("daily", pattern="^(daily|weekly)$"),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()] or None

    cache_key = ("overview", tickers, timeframe)
    cached = ai_cache.get(*cache_key)
    if cached is not None:
        return {"cached": True, **cached}

    if not ai_rate_limiter.allow(user.id, cost=2.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment.")

    tool_data = _gather_tool_data(ticker_list)
    messages = build_overview_messages(tickers=ticker_list, timeframe=timeframe, tool_data=tool_data)
    result = chat_completion(messages, user_id=user.id, endpoint="overview")
    result_dict = result.model_dump()
    ai_cache.set(result_dict, *cache_key)

    return {"cached": False, **result_dict}


# ---------------------------------------------------------------------------
# GET /api/ai/intelligence/stock
# ---------------------------------------------------------------------------


@router.get("/intelligence/stock")
def stock_intelligence_brief(
    ticker: str = Query(..., min_length=1, max_length=10, description="Stock ticker"),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Generate a Stock Intelligence Brief for a single ticker."""
    ticker = ticker.strip().upper()

    cache_key = ("stock_intel", ticker)
    cached = ai_cache.get(*cache_key)
    if cached is not None:
        return {"cached": True, **cached}

    if not ai_rate_limiter.allow(user.id, cost=3.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment.")

    tool_data = _gather_stock_data(ticker)
    if not tool_data:
        raise HTTPException(status_code=404, detail=f"No data available for {ticker}.")

    messages = build_stock_intelligence_messages(ticker, tool_data=tool_data)
    result = chat_completion(messages, user_id=user.id, endpoint="stock_intelligence")

    from app.routes.data import get_fundamentals, get_quote, get_technicals
    from app.services.market_data import get_stock_metrics

    quote = get_quote(ticker)
    fund = get_fundamentals(ticker)
    tech = get_technicals(ticker)
    metrics = get_stock_metrics(ticker)

    snapshot: dict[str, str | None] = {}
    if "error" not in quote:
        snapshot["price"] = f"${quote['price']:,.2f}"
        snapshot["day_change"] = f"{quote['changePct']:+.2f}%"
    if "error" not in fund:
        snapshot["market_cap"] = str(fund.get("marketCap", "N/A"))
        snapshot["pe_ratio"] = str(fund.get("peRatio", "N/A"))
        snapshot["sector"] = str(fund.get("sector", "N/A"))
    if "error" not in tech:
        snapshot["rsi"] = str(tech.get("rsi14", "N/A"))
        snapshot["realized_vol_30d"] = f"{tech.get('realizedVol30d', 'N/A')}%"
    if metrics:
        growth = metrics.get("growth", {})
        quality = metrics.get("quality", {})
        risk = metrics.get("risk", {})
        snapshot["revenue_yoy"] = f"{growth.get('revenue_growth_yoy', 'N/A')}%"
        snapshot["eps_yoy"] = f"{growth.get('earnings_growth_yoy', 'N/A')}%"
        snapshot["gross_margin"] = f"{quality.get('gross_margin', 'N/A')}%"
        snapshot["operating_margin"] = f"{quality.get('operating_margin', 'N/A')}%"
        snapshot["roe"] = f"{quality.get('roe', 'N/A')}%"
        snapshot["debt_to_equity"] = str(risk.get("debt_to_equity", "N/A"))
        snapshot["beta"] = str(risk.get("beta", "N/A"))

    result_dict = result.model_dump()
    now_iso = datetime.now(timezone.utc).isoformat()

    op_margin = quality.get("operating_margin", 30) if metrics else 30

    brief = {
        "ticker": ticker,
        "executive_summary": result_dict.get("summary", ""),
        "key_drivers": result_dict.get("checklist", [])[:5],
        "risk_tags": [
            {"category": "Competitive", "level": "Moderate"},
            {"category": "Regulatory", "level": "Low"},
            {"category": "Margin", "level": "Moderate" if op_margin < 25 else "Low"},
            {"category": "Macro", "level": "Moderate"},
            {"category": "Execution", "level": "Low"},
        ] if metrics else [],
        "regime_context": _infer_regime(metrics),
        "what_to_monitor": result_dict.get("risk_flags", [])[:5],
        "snapshot": snapshot,
        "as_of": now_iso,
        "disclaimer": "For informational/educational use only. Not investment advice.",
        "data_sources": result_dict.get("data_used", []),
    }

    ai_cache.set(brief, *cache_key, ttl=600)
    return {"cached": False, **brief}


# ---------------------------------------------------------------------------
# GET /api/ai/intelligence/market
# ---------------------------------------------------------------------------


@router.get("/intelligence/market")
def market_intelligence_brief(
    mode: str = Query("daily", pattern="^(daily|weekly)$"),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Generate a Market Intelligence Brief."""
    cache_key = ("market_intel", mode)
    cached = ai_cache.get(*cache_key)
    if cached is not None:
        return {"cached": True, **cached}

    if not ai_rate_limiter.allow(user.id, cost=3.0):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment.")

    tool_data = _gather_market_data()
    messages = build_market_intelligence_messages(timeframe=mode, tool_data=tool_data)
    result = chat_completion(messages, user_id=user.id, endpoint="market_intelligence")
    result_dict = result.model_dump()

    from app.routes.data import get_technicals

    spy_tech = get_technicals("SPY")

    vol_context = "N/A"
    if "error" not in spy_tech:
        vol = spy_tech.get("realizedVol30d", 0)
        if vol < 15:
            vol_context = f"Low volatility environment ({vol}% realized). Below long-term average."
        elif vol < 25:
            vol_context = f"Moderate volatility ({vol}% realized). Within normal range."
        else:
            vol_context = f"Elevated volatility ({vol}% realized). Above long-term average."

    regime = "Neutral"
    if "error" not in spy_tech:
        rsi = spy_tech.get("rsi14", 50)
        if rsi > 60 and spy_tech.get("macdSignal") == "bullish":
            regime = "Risk-On"
        elif rsi < 40 and spy_tech.get("macdSignal") == "bearish":
            regime = "Risk-Off"

    now_iso = datetime.now(timezone.utc).isoformat()

    brief = {
        "executive_summary": result_dict.get("summary", ""),
        "risk_dashboard": {
            "regime": regime,
            "volatility_context": vol_context,
            "breadth_context": "Moderate breadth with technology and financials showing relative strength.",
        },
        "catalysts": result_dict.get("checklist", [])[:6],
        "what_changed": result_dict.get("risk_flags", [])[:3],
        "as_of": now_iso,
        "disclaimer": "For informational/educational use only. Not investment advice.",
        "data_sources": result_dict.get("data_used", []),
    }

    ai_cache.set(brief, *cache_key, ttl=900)
    return {"cached": False, **brief}


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


# ---------------------------------------------------------------------------
# POST /api/ai/cache/clear — bust the AI response cache
# ---------------------------------------------------------------------------


@router.post("/cache/clear")
def clear_ai_cache(
    user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Clear all cached AI responses. Useful after deploys or prompt changes."""
    ai_cache.clear()
    logger.info("AI cache cleared by user=%s", user.id)
    return {"status": "ok", "message": "AI cache cleared"}


# ---------------------------------------------------------------------------
# GET /api/ai/diagnostics — check AI pipeline health
# ---------------------------------------------------------------------------


@router.get("/diagnostics")
def ai_diagnostics(
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Check AI pipeline configuration and connectivity."""
    import httpx
    from app.services.ai.client import _API_KEY, _BASE_URL, _MODEL, _TIMEOUT, _headers

    diag: Dict[str, Any] = {
        "api_key_set": bool(_API_KEY),
        "api_key_prefix": _API_KEY[:8] + "..." if _API_KEY else "(empty)",
        "base_url": _BASE_URL,
        "model": _MODEL,
        "timeout": _TIMEOUT,
    }

    # Test connectivity with a minimal request
    try:
        body = {
            "model": _MODEL,
            "messages": [
                {"role": "user", "content": "Say hello in JSON: {\"greeting\": \"hello\"}"}
            ],
            "temperature": 0,
            "max_tokens": 50,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{_BASE_URL}/chat/completions",
                headers=_headers(),
                json=body,
            )
            diag["status_code"] = resp.status_code
            if resp.status_code == 200:
                data = resp.json()
                diag["test_response"] = data["choices"][0]["message"]["content"][:200]
                diag["ai_connected"] = True
            else:
                diag["error"] = resp.text[:500]
                diag["ai_connected"] = False
    except Exception as exc:
        diag["ai_connected"] = False
        diag["error"] = str(exc)[:500]

    return diag


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer_regime(metrics: dict | None) -> str:
    """Infer market regime from available metrics."""
    if not metrics:
        return "Neutral"
    momentum = metrics.get("momentum", {})
    risk = metrics.get("risk", {})
    rsi = momentum.get("rsi_14", 50)
    vol = risk.get("volatility_30d", 20)
    sma50_pct = momentum.get("price_vs_sma50", 0)
    if rsi > 60 and vol < 25 and sma50_pct > 0:
        return "Risk-On"
    elif rsi < 40 or vol > 40 or sma50_pct < -5:
        return "Risk-Off"
    return "Neutral"
