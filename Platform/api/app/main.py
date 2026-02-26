# Platform/api/app/main.py

import logging
import os
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes import auth, twofa, bots, logs, system, dashboard, signals, insights
from app.routes import subscriptions, admin, profile
from app.routes import stripe as stripe_routes
from app.routes import scores, quotes, ai, health, auth_refresh
from app.routes import ai_assistant
from app.routes import rating as rating_routes
from app.routes import data as data_routes
from app.db.init_db import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def _parse_cors_origins() -> List[str]:
    """
    Reads CORS_ORIGINS from env (comma-separated), falls back to safe defaults.
    """
    raw = os.getenv("CORS_ORIGINS", "").strip()

    defaults = [
        "https://www.apterfinancial.com",
        "https://apterfinancial.com",
        "https://apter-web.onrender.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    if not raw:
        return defaults

    origins = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    return origins if origins else defaults


app = FastAPI(
    title="Apter Financial API",
    version="0.3.0",
    openapi_version="3.1.0",
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    logger.info("Apter Financial API started -- v0.3.0")


allowed_origins = _parse_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for avatar uploads
uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Routers
app.include_router(health.router)
app.include_router(system.router)
app.include_router(auth.router)
app.include_router(auth_refresh.router)
app.include_router(twofa.router)
app.include_router(bots.router)
app.include_router(logs.router)
app.include_router(dashboard.router)
app.include_router(signals.router)
app.include_router(insights.router)
app.include_router(subscriptions.router)
app.include_router(stripe_routes.router)
app.include_router(admin.router)
app.include_router(profile.router)
app.include_router(scores.router)
app.include_router(quotes.router)
app.include_router(ai.router)              # /api/chat + /api/stocks/{ticker}/ai-overview
app.include_router(ai_assistant.router)     # /api/ai/chat, /api/ai/overview, /api/ai/intelligence/*
app.include_router(rating_routes.router)    # /api/rating/{ticker}
app.include_router(data_routes.router)      # /api/data/* tool endpoints
