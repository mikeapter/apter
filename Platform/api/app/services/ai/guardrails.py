"""
Non-RIA compliance guardrails.

Validates AI output for disallowed advice language, suitability cues,
overconfidence claims, and portfolio guidance. Attempts automatic rewrite
if violations are found; falls back to a safe template if rewrite fails.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Disallowed patterns — compiled once at import time
# ---------------------------------------------------------------------------

_ADVICE_ACTION: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        # Direct action directives — "buy AAPL", "sell now", "hold the stock"
        r"\b(buy|sell)\s+(the\s+)?(stock|shares|position|calls?|puts?|options?|now|here|at)\b",
        r"\b(accumulate|dump)\s+(shares?|the\s+stock|more|now)\b",
        r"\btrim\s+(your|the)?\s*(position|shares?|holdings?)\b",
        # "you should" / "I recommend" — actual directive phrasing
        r"\byou\s+should\b",
        r"\bi\s+recommend\b",
        r"\bi\s+suggest\b",
        r"\bmy\s+advice\b",
        r"\bbest\s+move\b",
        r"\bperfect\s+time\b",
        r"\btime\s+to\s+(buy|sell)\b",
        r"\btake\s+profit\b",
        r"\bstop\s+loss\b",
        r"\bprice\s+target\b.*\b(buy|sell|until|at)\b",
        r"\btarget\s+price\b.*\b(buy|sell|until|at)\b",
    ]
]

_PORTFOLIO_GUIDANCE: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\brebalance\s+your\b",
        r"\ballocate\s+(your|\d+%)\b",
        r"\b(position\s+siz(e|ing))\b",
        r"\bpercent\s+allocation\b",
        r"\bputt?(?:ing)?\s+\d+%\s+in\b",
        r"\byour\s+(portfolio|holdings|account)\b",
        r"\bbased\s+on\s+your\s+account\b",
        r"\bfor\s+your\s+(retirement|goals)\b",
    ]
]

_SUITABILITY: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\brisk\s+tolerance\b",
        r"\b(your|their)\s+(age|income|net\s+worth|time\s+horizon|goals|retirement|family\s+situation|debt\s+level)\b",
        r"\bgiven\s+your\s+situation\b",
        r"\bfor\s+someone\s+like\s+you\b",
        r"\bsince\s+you\s+are\b",
    ]
]

_OVERCONFIDENCE: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bguaranteed\s+(returns?|gains?|profit|growth)\b",
        r"\bcan'?t\s+miss\b",
        r"\bsure\s+thing\b",
        r"\brisk[\s-]?free\s+(return|investment|profit)\b",
        r"\b(definitely\s+will|will\s+definitely)\s+(go\s+up|rise|outperform|beat)\b",
        r"\bwill\s+(go\s+up|outperform|beat\s+the\s+market)\b",
    ]
]

ALL_PATTERNS: list[tuple[str, list[re.Pattern]]] = [
    ("advice_action", _ADVICE_ACTION),
    ("portfolio_guidance", _PORTFOLIO_GUIDANCE),
    ("suitability", _SUITABILITY),
    ("overconfidence", _OVERCONFIDENCE),
]

REQUIRED_DISCLAIMER = "Not investment advice."

# ---------------------------------------------------------------------------
# Audit log path
# ---------------------------------------------------------------------------

_AUDIT_LOG_DIR = Path(__file__).resolve().parents[3] / "runtime" / "logs"


def _audit_log_path() -> Path:
    _AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    return _AUDIT_LOG_DIR / "ai_audit.jsonl"


# ---------------------------------------------------------------------------
# Validator result
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    ok: bool
    violations: List[str] = field(default_factory=list)
    corrected_json: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------


def _scan_text(text: str) -> List[str]:
    """Scan a string for all disallowed patterns and return violations."""
    violations: list[str] = []
    for category, patterns in ALL_PATTERNS:
        for pat in patterns:
            match = pat.search(text)
            if match:
                violations.append(f"{category}: matched '{match.group()}' in text")
    return violations


def validate_ai_output(data: dict | str) -> ValidationResult:
    """
    Validate an AI response (parsed dict or raw JSON string).

    Returns ValidationResult with ok=True if compliant, or ok=False with
    a list of violations.
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return ValidationResult(
                ok=False,
                violations=["invalid_json: could not parse response"],
            )

    violations: list[str] = []

    # Check all string fields
    for key in [
        "summary",
        "explanation",
        "disclaimer",
    ]:
        val = data.get(key, "")
        if isinstance(val, str):
            violations.extend(_scan_text(val))

    # Check list-of-string fields
    for key in [
        "risk_flags",
        "checklist",
        "scenarios",
        "comparisons",
        "watchlist_items",
        "citations",
    ]:
        val = data.get(key)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    violations.extend(_scan_text(item))

    # Check disclaimer is present
    disclaimer = data.get("disclaimer", "")
    if REQUIRED_DISCLAIMER.lower() not in str(disclaimer).lower():
        violations.append("missing_disclaimer: required disclaimer not found")

    return ValidationResult(ok=len(violations) == 0, violations=violations)


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


def log_audit(
    *,
    original: dict | str | None,
    violations: list[str],
    rewrite_attempted: bool,
    final_output: dict | str | None,
    user_id: int | str | None = None,
    endpoint: str = "",
) -> None:
    """Append an audit record to the JSONL log."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user_id": str(user_id) if user_id else None,
        "endpoint": endpoint,
        "violations": violations,
        "rewrite_attempted": rewrite_attempted,
        "original_snippet": _snippet(original),
        "final_snippet": _snippet(final_output),
    }
    try:
        with open(_audit_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception:
        logger.exception("Failed to write audit log")


def _snippet(data: dict | str | None, max_len: int = 500) -> str | None:
    if data is None:
        return None
    text = json.dumps(data, default=str) if isinstance(data, dict) else str(data)
    return text[:max_len]
