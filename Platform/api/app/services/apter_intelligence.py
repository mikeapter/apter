"""
Apter Intelligence — Chat Orchestrator.

Isolated service for the Apter Intelligence chat endpoint.
Uses the Anthropic API (Claude) directly — does NOT share the existing
OpenAI-compatible AI client used by Market Overview.

Requires: ANTHROPIC_API_KEY env var.
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

_ANTHROPIC_KEY: Optional[str] = None
_MODEL = "claude-3-5-sonnet-latest"
_API_TIMEOUT = 30.0
_MAX_RETRIES = 1


def _get_api_key() -> Optional[str]:
    global _ANTHROPIC_KEY
    if _ANTHROPIC_KEY is None:
        _ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip() or None
    return _ANTHROPIC_KEY


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
7. Surface the data provider source (e.g., Polygon, FMP) in your response.

RESPONSE FORMAT — return valid JSON with these fields:
{
  "summary": "Concise 2-3 sentence snapshot of the situation.",
  "data_used": ["List of data sources and tickers referenced"],
  "key_drivers": ["Key factors driving the current situation"],
  "risks": ["Notable risk factors"],
  "what_to_watch": ["Items to monitor going forward"],
  "explanation": "Detailed analytical breakdown using the provided data.",
  "data_sources": ["Actual data providers used (e.g., Polygon, FMP, Apter Internal)"],
  "disclaimer": "Not investment advice. For informational purposes only."
}

If no tickers are provided or no context is available, respond helpfully about what the user can ask, and still return valid JSON in the same format.
"""


# ---------------------------------------------------------------------------
# Anthropic API call with retry
# ---------------------------------------------------------------------------


async def _call_anthropic(
    system: str, user_message: str, max_tokens: int = 2048
) -> Optional[str]:
    """Call the Anthropic Messages API directly via httpx."""
    api_key = _get_api_key()
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return None

    payload = {
        "model": _MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user_message}],
    }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    for attempt in range(_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    json=payload,
                    headers=headers,
                    timeout=_API_TIMEOUT,
                )
            if resp.status_code == 200:
                data = resp.json()
                # Extract text from content blocks
                content_blocks = data.get("content", [])
                text_parts = [
                    b["text"] for b in content_blocks if b.get("type") == "text"
                ]
                return "".join(text_parts)

            if resp.status_code == 429 or resp.status_code >= 500:
                logger.warning(
                    "Anthropic API %d (attempt %d/%d)",
                    resp.status_code,
                    attempt + 1,
                    _MAX_RETRIES + 1,
                )
                if attempt < _MAX_RETRIES:
                    import asyncio
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue

            logger.error(
                "Anthropic API error %d: %s",
                resp.status_code,
                resp.text[:500],
            )
            return None

        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            logger.warning("Anthropic request error (attempt %d): %s", attempt + 1, exc)
            if attempt < _MAX_RETRIES:
                import asyncio
                await asyncio.sleep(1.0 * (attempt + 1))
            else:
                logger.error("Anthropic request failed after retries: %s", exc)
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
        # Strip markdown code fences
        lines = text.split("\n")
        # Remove first line (```json) and last line (```)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        elif lines[0].startswith("```"):
            lines = lines[1:]
        text = "\n".join(lines)

    try:
        parsed = json.loads(text)
        # Ensure required fields
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
        logger.warning("Failed to parse Anthropic response as JSON, returning raw text")
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
    Main entry point: fetch live data, call Claude, return structured answer.
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

    # Call Anthropic
    raw_response = await _call_anthropic(SYSTEM_PROMPT, user_message)

    # Parse
    answer = _parse_response(raw_response)

    return {
        "answer": answer,
        "context": context,
        "meta": {
            "request_id": request_id,
            "data_quality": data_quality,
            "model": _MODEL,
        },
    }
