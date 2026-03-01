"""
Apter Intelligence API route — isolated from Market Overview.

POST /api/apter-intelligence — chat with live-data-grounded analysis.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.dependencies import get_current_user
from app.models.user import User
from app.services.apter_intelligence import answer_question

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Apter Intelligence"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

_TICKER_RE = re.compile(r"^[A-Z]{1,5}(?:[.\-][A-Z]{1,2})?$")


class ApterIntelligenceRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=600)
    tickers: List[str] = Field(default_factory=list, max_length=10)

    @field_validator("tickers", mode="before")
    @classmethod
    def sanitize_tickers(cls, v: Any) -> List[str]:
        if not isinstance(v, list):
            return []
        cleaned = []
        for raw in v[:10]:
            t = str(raw).strip().upper().replace("-", ".")
            if _TICKER_RE.match(t):
                cleaned.append(t)
        return cleaned


class ApterIntelligenceMeta(BaseModel):
    request_id: str
    data_quality: str  # "live" | "partial" | "unavailable"
    model: Optional[str] = None


class ApterIntelligenceResponse(BaseModel):
    answer: Dict[str, Any]
    context: Dict[str, Any]
    meta: ApterIntelligenceMeta


# ---------------------------------------------------------------------------
# POST /api/apter-intelligence
# ---------------------------------------------------------------------------


@router.post("/api/apter-intelligence", response_model=ApterIntelligenceResponse)
async def apter_intelligence_chat(
    body: ApterIntelligenceRequest,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    logger.info(
        "[Apter Intelligence] Request: user=%s question='%s' tickers=%s",
        user.id,
        body.question[:80],
        body.tickers,
    )

    try:
        result = await answer_question(
            question=body.question,
            tickers=body.tickers,
        )
    except Exception as exc:
        logger.exception("[Apter Intelligence] Error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Apter Intelligence service temporarily unavailable. Please try again.",
        )

    logger.info(
        "[Apter Intelligence] Response: data_quality=%s provider=%s model=%s",
        result.get("meta", {}).get("data_quality"),
        result.get("context", {}).get("meta", {}).get("provider"),
        result.get("meta", {}).get("model"),
    )
    return result
