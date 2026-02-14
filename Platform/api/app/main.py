# Platform/api/app/main.py

import os
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, twofa, bots, logs, system, dashboard, signals, insights
from app.routes import subscriptions, admin
from app.db.init_db import init_db


def _parse_cors_origins() -> List[str]:
    """
    Reads CORS_ORIGINS from env (comma-separated), falls back to safe defaults.
    Example env:
      CORS_ORIGINS=https://www.apterfinancial.com,https://apterfinancial.com,https://apter-web.onrender.com,http://localhost:3000
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
    title="BotTrader Control Plane",
    version="0.1.0",
    openapi_version="3.1.0",
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


allowed_origins = _parse_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(system.router)
app.include_router(auth.router)
app.include_router(twofa.router)
app.include_router(bots.router)
app.include_router(logs.router)
app.include_router(dashboard.router)
app.include_router(signals.router)
app.include_router(insights.router)
app.include_router(subscriptions.router)
app.include_router(admin.router)  # TODO: remove after one-time backfill
