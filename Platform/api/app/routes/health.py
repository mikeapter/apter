"""Health check endpoint for monitoring and client warmup."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/healthz")
def healthz():
    """
    Lightweight health check.
    Verifies: app alive + DB reachable.
    """
    db_ok = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_ok = True
    except Exception as e:
        logger.error("Health check DB failure: %s", str(e))

    return {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "unreachable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
