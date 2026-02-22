# Platform/api/app/security/audit.py
"""
Structured audit logger for security-relevant events.

Writes JSONL to a rotating log file. Never logs secrets, tokens, or passwords.
Events: auth_success, auth_failure, token_refresh, lockout, password_reset_request,
        role_change, 2fa_setup, 2fa_disable.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import Request

logger = logging.getLogger(__name__)

# Audit log directory — same location as guardrails audit logs
_AUDIT_LOG_DIR = Path(__file__).resolve().parents[3] / "runtime" / "logs"
_AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
_AUDIT_LOG_FILE = _AUDIT_LOG_DIR / "security_audit.jsonl"

# Fields that must NEVER appear in audit logs
_REDACTED_FIELDS = frozenset({
    "password", "token", "access_token", "refresh_token", "secret",
    "secret_key", "api_key", "hashed_password", "twofa_secret",
    "backup_codes", "authorization",
})


def _sanitize(data: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive fields from audit data."""
    return {k: v for k, v in data.items() if k.lower() not in _REDACTED_FIELDS}


def _get_client_ip(request: Optional[Request]) -> str:
    if request is None:
        return "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_request_id(request: Optional[Request]) -> str:
    if request is None:
        return "unknown"
    return getattr(request.state, "request_id", "unknown")


def audit_log(
    event: str,
    *,
    request: Optional[Request] = None,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    success: bool = True,
    details: Optional[dict[str, Any]] = None,
):
    """
    Write a structured audit log entry.

    Args:
        event: Event type (e.g. "auth_success", "auth_failure", "lockout")
        request: The FastAPI request (for IP and request ID)
        user_id: User ID if available
        email: Email if available (logged for failed attempts too)
        success: Whether the action succeeded
        details: Additional context (sensitive fields auto-stripped)
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "success": success,
        "client_ip": _get_client_ip(request),
        "request_id": _get_request_id(request),
    }

    if user_id is not None:
        entry["user_id"] = user_id
    if email is not None:
        entry["email"] = email
    if details:
        entry["details"] = _sanitize(details)

    # Write to file
    try:
        with open(_AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        logger.exception("Failed to write audit log entry")

    # Also emit via standard logging for log aggregators
    log_level = logging.INFO if success else logging.WARNING
    logger.log(
        log_level,
        "AUDIT: %s | user=%s email=%s ip=%s",
        event,
        user_id,
        email,
        entry["client_ip"],
    )
