from __future__ import annotations

import os
from fastapi import Header, HTTPException, status


def get_required_api_key() -> str:
    """
    BOTTRADER_API_KEY must be set in the process environment.
    We load it from .env in main.py.
    """
    key = os.getenv("BOTTRADER_API_KEY")
    if not key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfigured: BOTTRADER_API_KEY is not set",
        )
    return key


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    required = get_required_api_key()
    if not x_api_key or x_api_key != required:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: invalid API key",
        )
