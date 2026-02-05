import os
from fastapi import Header, HTTPException

def require_api_key(x_api_key: str = Header(None)):
    expected = os.getenv("BOTTRADER_API_KEY")

    if not expected:
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: BOTTRADER_API_KEY is not set",
        )

    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )
