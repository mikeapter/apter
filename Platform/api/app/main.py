# Platform/api/app/main.py

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes import auth, twofa, bots, logs, system, dashboard, signals, insights
from app.routes import subscriptions, admin, profile
from app.routes import stripe as stripe_routes
from app.routes import scores, quotes, ai, health, auth_refresh
from app.routes import ai_assistant
from app.routes import password_reset
from app.routes import data as data_routes
from app.routes import market as market_routes
from app.db.init_db import init_db
from app.services.finnhub.config import log_status as finnhub_log_status

from app.security.config import ALLOWED_ORIGINS, ENABLE_DOCS, IS_PRODUCTION
from app.security.middleware import RequestSizeLimitMiddleware, SecurityHeadersMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


# ── App factory ──────────────────────────────────────────────────────────────

def _create_app() -> FastAPI:
    """
    Create the FastAPI application.
    In production, Swagger/ReDoc docs are disabled unless ENABLE_DOCS=true.
    """
    kwargs = dict(
        title="Apter Financial API",
        version="0.2.0",
        openapi_version="3.1.0",
    )

    if not ENABLE_DOCS:
        kwargs["docs_url"] = None
        kwargs["redoc_url"] = None
        kwargs["openapi_url"] = None

    return FastAPI(**kwargs)


app = _create_app()


@app.on_event("startup")
def _startup() -> None:
    init_db()
    finnhub_log_status()
    logger.info("Apter Financial API started — v0.2.0 (env=%s, docs=%s)", "prod" if IS_PRODUCTION else "dev", ENABLE_DOCS)


# ── Middleware (applied in reverse order — last added runs first) ─────────────

# 1. Security headers + request ID (outermost — runs first)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Request body size limit
app.add_middleware(RequestSizeLimitMiddleware)

# 3. CORS — strict allowlist, no wildcards in production
_cors_origins = ALLOWED_ORIGINS
if IS_PRODUCTION:
    # Ensure no wildcards sneak in
    _cors_origins = [o for o in _cors_origins if o != "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept"],
    expose_headers=["X-Request-ID"],
)

# ─── Mount static files for avatar uploads ───
uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# ─── Routers ───
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
app.include_router(ai_assistant.router)     # /api/ai/chat, /api/ai/overview, /api/ai/feedback
app.include_router(password_reset.router)  # /auth/forgot-password, /auth/reset-password
app.include_router(data_routes.router)      # /api/data/* tool endpoints
app.include_router(market_routes.router)    # /api/market/* Finnhub endpoints
