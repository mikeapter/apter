from __future__ import annotations

import os
from fastapi import Header, HTTPException, status


def _get_expected_api_key() -> str:
    """
    Reads the API key from environment.
    We fail loudly if it's not set so you don't accidentally run "open".
    """
    expected = os.getenv("BOTTRADER_API_KEY", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfigured: BOTTRADER_API_KEY is not set",
        )
    return expected


def RequireApiKey(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> bool:
    """
    Dependency that enforces X-API-Key header matches BOTTRADER_API_KEY env var.
    """
    expected = _get_expected_api_key()

    if not x_api_key or x_api_key.strip() != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return True
