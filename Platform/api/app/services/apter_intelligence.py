"""
Apter Intelligence — Chat Orchestrator.

Isolated service for the Apter Intelligence chat endpoint.
Uses OpenAI Chat Completions API — does NOT share the existing
AI client used by Market Overview.

Requires: APTER_INTELLIGENCE_API_KEY (or falls back to AI_API_KEY) env var.
Model:    APTER_INTELLIGENCE_MODEL  (default: gpt-4o-mini)
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import httpx

from app.services.apter_intelligence_market_data import (
    build_context as fetch_market_context,
    sanitize_ticker,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_API_KEY: Optional[str] = None
_BASE_URL: Optional[str] = None
_MODEL: Optional[str] = None
_API_TIMEOUT = 30.0
_MAX_RETRIES = 1


def _get_config() -> tuple[Optional[str], str, str]:
    """Return (api_key, base_url, model) reading from env once."""
    global _API_KEY, _BASE_URL, _MODEL
    if _API_KEY is None:
        _API_KEY = (
            os.getenv("APTER_INTELLIGENCE_API_KEY", "").strip()
            or os.getenv("AI_API_KEY", "").strip()
            or None
        )
    if _BASE_URL is None:
        _BASE_URL = (
            os.getenv("APTER_INTELLIGENCE_BASE_URL", "").strip()
            or os.getenv("AI_BASE_URL", "").strip()
            or "https://api.openai.com/v1"
        )
    if _MODEL is None:
        _MODEL = (
            os.getenv("APTER_INTELLIGENCE_MODEL", "").strip()
            or os.getenv("AI_MODEL", "").strip()
            or "gpt-4o-mini"
        )
    return _API_KEY, _BASE_URL, _MODEL


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are Apter Intelligence, an institutional-grade financial analysis assistant.

RULES — follow strictly:
1. You only use the PROVIDED live data context to form your analysis.
2. Never mention training dates, knowledge cutoffs, or "as of" dates referencing model training.
3. If live data is missing for a requested ticker, say: "Live data temporarily unavailable."
4. Do NOT give buy, sell, or hold recommendations. Use neutral, analytical language.
5. Do NOT claim to be a registered investment adviser.
6. Always include "Not investment advice." in your disclaimer.
7. Surface the data provider source (e.g., Finnhub, Polygon, FMP) in your response.

RESPONSE FORMAT — return valid JSON with these fields:
{
  "summary": "Concise 2-3 sentence snapshot of the situation.",
  "data_used": ["List of data sources and tickers referenced"],
  "key_drivers": ["Key factors driving the current situation"],
  "risks": ["Notable risk factors"],
  "what_to_watch": ["Items to monitor going forward"],
  "explanation": "Detailed analytical breakdown using the provided data.",
  "data_sources": ["Actual data providers used (e.g., Finnhub, Polygon, FMP)"],
  "disclaimer": "Not investment advice. For informational purposes only."
}

If no tickers are provided or no context is available, respond helpfully about what the user can ask, and still return valid JSON in the same format.
"""


# ---------------------------------------------------------------------------
# OpenAI Chat Completions API call with retry
# ---------------------------------------------------------------------------


async def _call_llm(
    system: str, user_message: str, max_tokens: int = 2048
) -> Optional[str]:
    """Call OpenAI-compatible Chat Completions API directly via httpx."""
    api_key, base_url, model = _get_config()
    if not api_key:
        logger.error("No API key set (APTER_INTELLIGENCE_API_KEY or AI_API_KEY)")
        return None

    url = f"{base_url.rstrip('/')}/chat/completions"

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=_API_TIMEOUT,
                )
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return None

            if resp.status_code == 429 or resp.status_code >= 500:
                logger.warning(
                    "LLM API %d (attempt %d/%d)",
                    resp.status_code,
                    attempt + 1,
                    _MAX_RETRIES + 1,
                )
                if attempt < _MAX_RETRIES:
                    import asyncio
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue

            logger.error(
                "LLM API error %d: %s",
                resp.status_code,
                resp.text[:500],
            )
            return None

        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            logger.warning("LLM request error (attempt %d): %s", attempt + 1, exc)
            if attempt < _MAX_RETRIES:
                import asyncio
                await asyncio.sleep(1.0 * (attempt + 1))
            else:
                logger.error("LLM request failed after retries: %s", exc)
                return None

    return None


# ---------------------------------------------------------------------------
# Parse response JSON
# ---------------------------------------------------------------------------

_FALLBACK_RESPONSE = {
    "summary": "I was unable to generate an analysis at this time. Please try again.",
    "data_used": [],
    "key_drivers": [],
    "risks": [],
    "what_to_watch": [],
    "explanation": "",
    "data_sources": [],
    "disclaimer": "Not investment advice. For informational purposes only.",
}


def _parse_response(raw: Optional[str]) -> dict:
    """Try to parse the LLM response as JSON, with fallback."""
    if not raw:
        return {**_FALLBACK_RESPONSE}

    # Try to extract JSON from the response (handle markdown code blocks)
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        elif lines[0].startswith("```"):
            lines = lines[1:]
        text = "\n".join(lines)

    try:
        parsed = json.loads(text)
        parsed.setdefault("summary", "")
        parsed.setdefault("data_used", [])
        parsed.setdefault("key_drivers", [])
        parsed.setdefault("risks", [])
        parsed.setdefault("what_to_watch", [])
        parsed.setdefault("explanation", "")
        parsed.setdefault("data_sources", [])
        parsed.setdefault("disclaimer", "Not investment advice. For informational purposes only.")
        return parsed
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response as JSON, returning raw text")
        return {
            **_FALLBACK_RESPONSE,
            "summary": raw[:500],
            "explanation": raw,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def answer_question(
    question: str,
    tickers: List[str],
) -> Dict[str, Any]:
    """
    Main entry point: fetch live data, call LLM, return structured answer.
    """
    request_id = str(uuid.uuid4())

    # Sanitize tickers
    clean_tickers = []
    for t in tickers:
        clean = sanitize_ticker(t)
        if clean:
            clean_tickers.append(clean)

    # Fetch live market data
    context = await fetch_market_context(clean_tickers) if clean_tickers else {
        "tickers": {},
        "meta": {"provider": "none", "data_quality": "unavailable", "fetched_at": ""},
    }

    data_quality = context["meta"]["data_quality"]

    # Build user message with context
    context_text = json.dumps(context["tickers"], indent=2, default=str)
    user_message = f"""USER QUESTION: {question}

TICKERS REQUESTED: {', '.join(clean_tickers) if clean_tickers else 'None specified'}

LIVE MARKET DATA CONTEXT:
{context_text}

DATA PROVIDER: {context['meta']['provider']}
DATA QUALITY: {data_quality}
FETCHED AT: {context['meta']['fetched_at']}

Analyze the above data and answer the user's question. Return your response as valid JSON."""

    # Call LLM
    _, _, model = _get_config()
    raw_response = await _call_llm(SYSTEM_PROMPT, user_message)

    # Parse
    answer = _parse_response(raw_response)

    return {
        "answer": answer,
        "context": context,
        "meta": {
            "request_id": request_id,
            "data_quality": data_quality,
            "model": model,
        },
    }
