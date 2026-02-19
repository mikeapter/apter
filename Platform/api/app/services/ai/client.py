"""
Provider-agnostic AI model client.

Starts with an OpenAI-compatible interface (works with OpenAI, Azure OpenAI,
local vLLM, Ollama, etc.). Swap the provider by changing env vars.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.services.ai.guardrails import (
    ValidationResult,
    log_audit,
    validate_ai_output,
)
from app.services.ai.prompts import COMPLIANCE_REWRITE_PROMPT
from app.services.ai.schemas import SAFE_FALLBACK, AIResponseSchema

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

_PROVIDER = os.getenv("AI_PROVIDER", "openai_compatible")
_API_KEY = os.getenv("AI_API_KEY", "")
_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
_STREAMING = os.getenv("AI_ENABLE_STREAMING", "true").lower() == "true"
_TIMEOUT = int(os.getenv("AI_TIMEOUT_SECONDS", "60"))


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if _API_KEY:
        h["Authorization"] = f"Bearer {_API_KEY}"
    return h


# ---------------------------------------------------------------------------
# Synchronous (non-streaming) completion
# ---------------------------------------------------------------------------


def chat_completion(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    user_id: str | int | None = None,
    endpoint: str = "chat",
) -> AIResponseSchema:
    """
    Send a chat completion request, validate the response through guardrails,
    and return a compliant AIResponseSchema.
    """
    body = {
        "model": _MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{_BASE_URL}/chat/completions",
                headers=_headers(),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("AI API error: %s %s", exc.response.status_code, exc.response.text[:500])
        return SAFE_FALLBACK
    except Exception:
        logger.exception("AI API request failed")
        return SAFE_FALLBACK

    raw_content = data["choices"][0]["message"]["content"]
    return _validate_and_return(
        raw_content, user_id=user_id, endpoint=endpoint
    )


# ---------------------------------------------------------------------------
# Streaming completion (SSE)
# ---------------------------------------------------------------------------


async def chat_completion_stream(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    user_id: str | int | None = None,
) -> AsyncIterator[str]:
    """
    Stream chat completion tokens via SSE. Yields raw text chunks.
    After the full response is assembled, it is validated through guardrails.
    If non-compliant, yields a corrected/safe response instead.
    """
    body = {
        "model": _MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    collected = []

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{_BASE_URL}/chat/completions",
                headers=_headers(),
                json=body,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            collected.append(content)
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
    except Exception:
        logger.exception("AI streaming request failed")
        fallback_json = SAFE_FALLBACK.model_dump_json()
        yield f"\n\n[COMPLIANCE_REPLACE]{fallback_json}"
        return

    # Post-stream validation
    full_text = "".join(collected)
    validation = validate_ai_output(full_text)
    if not validation.ok:
        corrected = _attempt_rewrite_or_fallback(
            full_text, validation, user_id=user_id, endpoint="chat_stream"
        )
        yield f"\n\n[COMPLIANCE_REPLACE]{corrected.model_dump_json()}"


# ---------------------------------------------------------------------------
# Validation + rewrite pipeline
# ---------------------------------------------------------------------------


def _validate_and_return(
    raw_content: str,
    *,
    user_id: str | int | None = None,
    endpoint: str = "",
) -> AIResponseSchema:
    """Parse, validate, attempt rewrite if needed, return compliant schema."""
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        logger.warning("AI returned non-JSON: %s", raw_content[:300])
        log_audit(
            original=raw_content,
            violations=["invalid_json"],
            rewrite_attempted=False,
            final_output=SAFE_FALLBACK.model_dump(),
            user_id=user_id,
            endpoint=endpoint,
        )
        return SAFE_FALLBACK

    validation = validate_ai_output(parsed)

    if validation.ok:
        # Ensure disclaimer is set
        parsed.setdefault(
            "disclaimer",
            "Educational information only — not investment advice.",
        )
        try:
            return AIResponseSchema(**parsed)
        except Exception:
            return SAFE_FALLBACK

    return _attempt_rewrite_or_fallback(
        parsed, validation, user_id=user_id, endpoint=endpoint
    )


def _attempt_rewrite_or_fallback(
    original: dict | str,
    validation: ValidationResult,
    *,
    user_id: str | int | None = None,
    endpoint: str = "",
) -> AIResponseSchema:
    """Try one compliance rewrite; fall back to safe template on failure."""
    original_json = (
        json.dumps(original, default=str) if isinstance(original, dict) else str(original)
    )

    rewrite_prompt = COMPLIANCE_REWRITE_PROMPT.replace(
        "{original_json}", original_json
    )
    rewrite_messages = [
        {"role": "system", "content": "You are a compliance rewriter."},
        {"role": "user", "content": rewrite_prompt},
    ]

    try:
        body = {
            "model": _MODEL,
            "messages": rewrite_messages,
            "temperature": 0.1,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{_BASE_URL}/chat/completions",
                headers=_headers(),
                json=body,
            )
            resp.raise_for_status()
            rewrite_raw = resp.json()["choices"][0]["message"]["content"]
            rewrite_parsed = json.loads(rewrite_raw)
    except Exception:
        logger.exception("Compliance rewrite failed")
        log_audit(
            original=original,
            violations=validation.violations,
            rewrite_attempted=True,
            final_output=SAFE_FALLBACK.model_dump(),
            user_id=user_id,
            endpoint=endpoint,
        )
        return SAFE_FALLBACK

    # Validate the rewrite
    rewrite_validation = validate_ai_output(rewrite_parsed)
    if rewrite_validation.ok:
        rewrite_parsed.setdefault(
            "disclaimer",
            "Educational information only — not investment advice.",
        )
        log_audit(
            original=original,
            violations=validation.violations,
            rewrite_attempted=True,
            final_output=rewrite_parsed,
            user_id=user_id,
            endpoint=endpoint,
        )
        try:
            return AIResponseSchema(**rewrite_parsed)
        except Exception:
            pass

    # Rewrite still non-compliant — use safe fallback
    log_audit(
        original=original,
        violations=validation.violations + rewrite_validation.violations,
        rewrite_attempted=True,
        final_output=SAFE_FALLBACK.model_dump(),
        user_id=user_id,
        endpoint=endpoint,
    )
    return SAFE_FALLBACK
