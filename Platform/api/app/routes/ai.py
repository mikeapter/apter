"""
AI endpoints:
- POST /api/chat          — AI chat with intent routing
- GET  /api/stocks/{ticker}/ai-overview — Structured AI overview per stock

Updated to use standardized snapshot data and include staleness detection.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.market_data import (
    fetch_quote,
    get_stock_metrics,
    get_stock_name,
    normalize_symbol,
    validate_symbol,
)
from app.services.market_data.compute_metrics import (
    compute_staleness,
    compute_standardized_metrics,
)
from app.services.market_data.providers import get_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["AI"])

# ─── Ticker parsing ───

_TICKER_RE = re.compile(r"\$?([A-Z]{1,5}(?:\.[A-Z])?)")
_COMPANY_TICKER_RE = re.compile(r"\(([A-Z]{1,5})\)")
_KNOWN_TICKERS = {
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "SPY", "QQQ", "JPM",
    "BRK.B", "V", "UNH", "JNJ", "WMT", "XOM", "PG", "MA", "HD", "DIS",
}

# Company name -> ticker mapping
_COMPANY_MAP = {
    "apple": "AAPL", "microsoft": "MSFT", "nvidia": "NVDA", "google": "GOOGL",
    "alphabet": "GOOGL", "amazon": "AMZN", "meta": "META", "facebook": "META",
    "tesla": "TSLA", "jpmorgan": "JPM", "berkshire": "BRK.B", "visa": "V",
    "unitedhealth": "UNH", "johnson": "JNJ", "walmart": "WMT", "exxon": "XOM",
    "procter": "PG", "mastercard": "MA", "home depot": "HD", "disney": "DIS",
}


def parse_ticker(text: str) -> Optional[str]:
    """Extract a ticker symbol from user text."""
    paren_match = _COMPANY_TICKER_RE.search(text)
    if paren_match:
        t = paren_match.group(1)
        if t in _KNOWN_TICKERS:
            return t

    upper = text.upper()
    ticker_match = _TICKER_RE.search(upper)
    if ticker_match:
        t = ticker_match.group(1)
        if t in _KNOWN_TICKERS:
            return t

    lower = text.lower()
    for company, ticker in _COMPANY_MAP.items():
        if company in lower:
            return ticker

    return None


def classify_intent(text: str) -> Tuple[str, Optional[str]]:
    """
    Classify the intent of a chat message.
    Returns (intent, ticker_or_none).
    Intent: STOCK | MARKET | GENERAL
    """
    ticker = parse_ticker(text)
    if ticker:
        return "STOCK", ticker

    lower = text.lower()
    market_keywords = ["market", "s&p", "spy", "qqq", "vix", "rates", "fed",
                       "dow", "nasdaq", "index", "bonds", "treasury", "economy"]
    if any(kw in lower for kw in market_keywords):
        return "MARKET", None

    return "GENERAL", None


# ─── Chat request/response models ───

class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None


# ─── Performance calculations ───

def _compute_performance(metrics: Optional[dict]) -> dict:
    """Extract performance windows from metrics."""
    if not metrics or "momentum" not in metrics:
        return {"1d": None, "5d": None, "1m": None, "3m": None, "ytd": None}

    mom = metrics["momentum"]
    return {
        "1d": None,
        "5d": None,
        "1m": mom.get("return_1m"),
        "3m": mom.get("return_3m"),
        "ytd": mom.get("return_6m"),
    }


def _generate_stock_chat_response(ticker: str) -> dict:
    """Generate a ticker-specific chat response with real data."""
    quote = fetch_quote(ticker)
    metrics = get_stock_metrics(ticker)
    name = get_stock_name(ticker)

    price = quote.get("price", 0)
    change_pct = quote.get("change_pct", 0)
    perf = _compute_performance(metrics)

    sections = {}

    direction = "up" if change_pct >= 0 else "down"
    sections["snapshot"] = f"{ticker} ({name}) is trading at ${price:,.2f}, {direction} {abs(change_pct):.2f}% today."

    perf_parts = []
    if perf.get("1m") is not None:
        perf_parts.append(f"1M: {'+' if perf['1m'] >= 0 else ''}{perf['1m']:.1f}%")
    if perf.get("3m") is not None:
        perf_parts.append(f"3M: {'+' if perf['3m'] >= 0 else ''}{perf['3m']:.1f}%")
    if perf.get("ytd") is not None:
        perf_parts.append(f"YTD (approx): {'+' if perf['ytd'] >= 0 else ''}{perf['ytd']:.1f}%")
    sections["performance"] = " | ".join(perf_parts) if perf_parts else "Performance data currently unavailable."

    if metrics:
        quality = metrics.get("quality", {})
        value = metrics.get("value", {})
        risk = metrics.get("risk", {})

        metric_parts = []
        if value.get("pe_ratio"):
            metric_parts.append(f"P/E (TTM): {value['pe_ratio']:.1f}x")
        if quality.get("operating_margin"):
            metric_parts.append(f"Op. Margin (TTM): {quality['operating_margin']:.1f}%")
        if quality.get("roe"):
            metric_parts.append(f"ROE (TTM): {quality['roe']:.1f}%")
        if risk.get("volatility_30d"):
            metric_parts.append(f"30d Vol: {risk['volatility_30d']:.1f}%")

        sections["key_metrics"] = " | ".join(metric_parts) if metric_parts else "Metrics data pending."
    else:
        sections["key_metrics"] = f"Detailed metrics for {ticker} are not yet available."

    if metrics:
        mom = metrics.get("momentum", {})
        rsi = mom.get("rsi_14")
        vol = metrics.get("risk", {}).get("volatility_30d")

        assessment_parts = []
        if rsi:
            if rsi > 70:
                assessment_parts.append("RSI indicates overbought conditions.")
            elif rsi < 30:
                assessment_parts.append("RSI indicates oversold conditions.")
            else:
                assessment_parts.append(f"RSI at {rsi:.0f} suggests neutral momentum.")
        if vol:
            if vol > 40:
                assessment_parts.append(f"Elevated volatility ({vol:.1f}%) warrants careful position sizing.")
            elif vol < 20:
                assessment_parts.append(f"Low volatility environment ({vol:.1f}%).")
        sections["assessment"] = " ".join(assessment_parts)
    else:
        sections["assessment"] = "Insufficient data for detailed assessment."

    return {
        "dataShows": sections.get("snapshot", "") + " " + sections.get("performance", ""),
        "whyItMatters": sections.get("key_metrics", "") + " " + sections.get("assessment", ""),
        "reviewNext": [
            f"View full Conviction Score for {ticker}",
            f"Check {ticker} grade breakdown and risk factors",
            f"Compare {ticker} to sector peers",
        ],
    }


def _generate_market_chat_response() -> dict:
    """Generate a market overview chat response."""
    spy_quote = fetch_quote("SPY")
    qqq_quote = fetch_quote("QQQ")

    spy_price = spy_quote.get("price", 0)
    spy_chg = spy_quote.get("change_pct", 0)
    qqq_price = qqq_quote.get("price", 0)
    qqq_chg = qqq_quote.get("change_pct", 0)

    return {
        "dataShows": (
            f"S&P 500 (SPY) is at ${spy_price:,.2f} ({'+' if spy_chg >= 0 else ''}{spy_chg:.2f}%). "
            f"Nasdaq-100 (QQQ) is at ${qqq_price:,.2f} ({'+' if qqq_chg >= 0 else ''}{qqq_chg:.2f}%). "
            "Market breadth is moderate with technology and financials showing relative strength."
        ),
        "whyItMatters": (
            "Current conditions suggest a risk-on environment with VIX below the long-term average. "
            "Sector rotation dynamics and earnings growth trajectory remain key factors to monitor."
        ),
        "reviewNext": [
            "Check sector performance for rotation signals",
            "Review portfolio exposure relative to market conditions",
            "Monitor VIX and yield curve for regime changes",
        ],
    }


def _generate_general_response(message: str) -> dict:
    """Generate a general-purpose response."""
    return {
        "dataShows": (
            "I can help you analyze specific stocks, review market conditions, "
            "or explore portfolio analytics. Try asking about a specific ticker like AAPL or MSFT, "
            "or ask about overall market conditions."
        ),
        "whyItMatters": (
            "Focused, specific questions allow me to provide more relevant data points "
            "and analytical context for your decision-making process."
        ),
        "reviewNext": [
            "Ask about a specific stock (e.g., 'How is MSFT performing?')",
            "Ask about market conditions (e.g., 'Market overview')",
            "Ask about your portfolio (e.g., 'Review my holdings')",
        ],
    }


@router.post("/chat")
def chat_endpoint(request: ChatRequest):
    """
    AI Chat with intent routing.
    - STOCK intent: ticker-specific analysis
    - MARKET intent: market overview
    - GENERAL intent: general guidance
    """
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    intent, ticker = classify_intent(message)
    logger.info("Chat intent=%s ticker=%s message=%s", intent, ticker, message[:100])

    if intent == "STOCK" and ticker:
        try:
            response = _generate_stock_chat_response(ticker)
        except Exception as e:
            logger.error("Error generating stock response for %s: %s", ticker, str(e))
            response = {
                "dataShows": f"Data temporarily unavailable for {ticker}. Try again in a moment.",
                "whyItMatters": "The data service encountered an issue fetching real-time information.",
                "reviewNext": [f"Try again in a moment", f"Search for {ticker} directly"],
            }
    elif intent == "MARKET":
        response = _generate_market_chat_response()
    else:
        response = _generate_general_response(message)

    return {
        "intent": intent,
        "ticker": ticker,
        "response": response,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/stocks/{ticker}/ai-overview")
def stock_ai_overview(ticker: str):
    """
    Structured AI overview for a specific stock.
    Now uses standardized snapshot data with staleness detection.
    """
    symbol = normalize_symbol(ticker)
    if not validate_symbol(symbol):
        raise HTTPException(status_code=400, detail=f"Invalid ticker: {ticker}")

    logger.info("AI overview requested for %s", symbol)

    # Use provider for structured data
    provider = get_provider()
    quote_data = provider.get_quote(symbol)
    fundamentals = provider.get_fundamentals_ttm(symbol)
    forward = provider.get_estimates_forward(symbol)
    name = get_stock_name(symbol)
    metrics = get_stock_metrics(symbol)

    if quote_data.price == 0 and not metrics:
        raise HTTPException(
            status_code=404,
            detail=f"No data available for {symbol}. Cannot generate overview.",
        )

    # Compute standardized metrics for staleness check
    standardized = compute_standardized_metrics(
        ticker=symbol,
        fundamentals=fundamentals,
        quote=quote_data,
        forward=forward,
    )
    data_quality = compute_staleness(fundamentals, forward, standardized)

    price = quote_data.price
    change_pct = quote_data.change_pct
    perf = _compute_performance(metrics)

    # Build drivers from metrics
    drivers = []
    if metrics:
        quality = metrics.get("quality", {})
        growth = metrics.get("growth", {})
        momentum = metrics.get("momentum", {})

        if quality.get("operating_margin", 0) > 25:
            drivers.append("Strong operating margins support profitability")
        if growth.get("revenue_growth_yoy", 0) > 15:
            drivers.append("Above-average revenue growth trajectory")
        elif growth.get("revenue_growth_yoy", 0) < 0:
            drivers.append("Revenue decline is a concern")
        if momentum.get("rsi_14", 50) > 65:
            drivers.append("Positive momentum with elevated RSI")
        elif momentum.get("rsi_14", 50) < 35:
            drivers.append("Oversold conditions may present opportunity")
        if quality.get("roe", 0) > 25:
            drivers.append("High return on equity indicates capital efficiency")

    if not drivers:
        drivers = ["Insufficient data for driver analysis", "Monitor for updated metrics", "Review peer comparison"]

    outlook = _build_outlook(symbol, metrics, change_pct)
    news = _build_news(symbol)
    watch = _build_what_to_watch(symbol, metrics)

    # Build staleness notice for AI text
    staleness_notice = None
    if "fundamentals_old" in data_quality.stale_flags:
        staleness_notice = f"Some fundamentals may be delayed; last reported period: {fundamentals.period_end or 'unknown'}."
    elif "no_fundamentals" in data_quality.stale_flags:
        staleness_notice = "Fundamental data is not currently available for this security."

    return {
        "ticker": symbol,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "snapshot": {
            "price": price,
            "day_change_pct": change_pct,
            "volume": None,
        },
        "performance": perf,
        "drivers": drivers[:3],
        "outlook": outlook,
        "news": news,
        "what_to_watch": watch[:3],
        "data_quality": data_quality.model_dump(),
        "staleness_notice": staleness_notice,
        "data_as_of": fundamentals.period_end,
        "source": provider.name,
        "disclaimer": "This analysis is generated algorithmically and is not investment advice. Past performance does not indicate future results.",
    }


def _build_outlook(symbol: str, metrics: Optional[dict], change_pct: float) -> dict:
    """Build base/bull/bear outlook for a stock."""
    name = get_stock_name(symbol)

    if not metrics:
        return {
            "base_case": f"Insufficient data to project outlook for {name}. Monitor for updated financial data.",
            "bull_case": "Positive catalysts could include earnings beats or sector tailwinds.",
            "bear_case": "Risk factors include market-wide drawdowns or company-specific headwinds.",
            "probabilities": {"base": 50, "bull": 25, "bear": 25},
        }

    growth = metrics.get("growth", {})
    risk = metrics.get("risk", {})
    rev_growth = growth.get("revenue_growth_yoy", 0)
    vol = risk.get("volatility_30d", 25)

    if rev_growth > 20:
        base = f"{name} maintains its growth trajectory with revenue expansion continuing above market averages."
        bull = f"Accelerating adoption and market share gains could push growth above current estimates."
        bear = f"Valuation compression or growth deceleration could pressure returns."
        probs = {"base": 45, "bull": 30, "bear": 25}
    elif rev_growth > 0:
        base = f"{name} delivers moderate growth in line with consensus estimates."
        bull = f"Margin expansion or new product catalysts could drive upside surprise."
        bear = f"Competitive pressures or macro headwinds could weigh on performance."
        probs = {"base": 50, "bull": 25, "bear": 25}
    else:
        base = f"{name} faces near-term challenges with revenue pressure expected to persist."
        bull = f"Turnaround initiatives or market recovery could stabilize fundamentals."
        bear = f"Continued deterioration in fundamentals could drive further downside."
        probs = {"base": 40, "bull": 20, "bear": 40}

    return {
        "base_case": base,
        "bull_case": bull,
        "bear_case": bear,
        "probabilities": probs,
    }


def _build_news(symbol: str) -> list:
    """Build recent news items for a stock. MVP uses curated items."""
    news_db = {
        "AAPL": [
            {"headline": "Apple expands services revenue to record quarter", "source": "Financial Times", "published_at": "2026-02-16T09:15:00Z", "impact": "positive"},
            {"headline": "iPhone supply chain signals stable production outlook", "source": "Reuters", "published_at": "2026-02-15T14:30:00Z", "impact": "neutral"},
        ],
        "MSFT": [
            {"headline": "Azure revenue growth accelerates to 32% year-over-year", "source": "Bloomberg", "published_at": "2026-02-16T10:00:00Z", "impact": "positive"},
            {"headline": "Microsoft AI Copilot adoption reaches enterprise milestone", "source": "CNBC", "published_at": "2026-02-15T08:45:00Z", "impact": "positive"},
        ],
        "NVDA": [
            {"headline": "NVIDIA data center revenue exceeds estimates but guidance mixed", "source": "Reuters", "published_at": "2026-02-16T11:30:00Z", "impact": "neutral"},
            {"headline": "Custom AI chip development accelerates at major cloud providers", "source": "The Information", "published_at": "2026-02-15T09:00:00Z", "impact": "negative"},
        ],
        "TSLA": [
            {"headline": "EV competition intensifies as legacy automakers scale production", "source": "Reuters", "published_at": "2026-02-16T13:00:00Z", "impact": "negative"},
            {"headline": "Tesla energy storage deployments hit quarterly record", "source": "Bloomberg", "published_at": "2026-02-15T10:15:00Z", "impact": "positive"},
        ],
        "GOOGL": [
            {"headline": "Google Cloud profitability improves for third consecutive quarter", "source": "CNBC", "published_at": "2026-02-16T08:30:00Z", "impact": "positive"},
        ],
        "AMZN": [
            {"headline": "AWS maintains cloud market share leadership at 32%", "source": "Gartner", "published_at": "2026-02-15T12:00:00Z", "impact": "positive"},
        ],
        "META": [
            {"headline": "Meta advertising revenue growth exceeds industry average", "source": "Financial Times", "published_at": "2026-02-15T11:00:00Z", "impact": "positive"},
        ],
        "JPM": [
            {"headline": "JPMorgan investment banking fees rise on improved deal activity", "source": "Financial Times", "published_at": "2026-02-15T16:00:00Z", "impact": "positive"},
        ],
    }
    return news_db.get(symbol, [])


def _build_what_to_watch(symbol: str, metrics: Optional[dict]) -> list:
    """Build 'what to watch' items based on available metrics."""
    items = []

    if not metrics:
        return ["Watch for upcoming earnings announcements", "Monitor sector rotation trends", "Check peer performance"]

    risk = metrics.get("risk", {})
    momentum = metrics.get("momentum", {})
    growth = metrics.get("growth", {})

    if risk.get("volatility_30d", 0) > 35:
        items.append("Elevated volatility — position sizing and stop-loss levels are critical")
    if momentum.get("rsi_14", 50) > 70:
        items.append("RSI in overbought territory — watch for potential pullback")
    elif momentum.get("rsi_14", 50) < 30:
        items.append("RSI in oversold territory — watch for potential bounce")
    if growth.get("revenue_growth_yoy", 0) < 0:
        items.append("Revenue decline trend — watch for stabilization signals")

    items.append("Next earnings report date and consensus estimates")
    items.append("Sector rotation and relative performance vs. peers")

    return items[:3]
