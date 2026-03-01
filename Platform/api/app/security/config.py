# Platform/api/app/security/config.py
"""
Centralised security configuration.
All values are loaded from environment variables with safe production defaults.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ── Environment ──────────────────────────────────────────────────────────────
ENV = os.getenv("ENV", "development")
IS_PRODUCTION = ENV in ("production", "prod")

# ── CORS ─────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "https://apterfinancial.com,https://www.apterfinancial.com,https://app.apterfinancial.com",
)
ALLOWED_ORIGINS: list[str] = [o.strip().rstrip("/") for o in _raw_origins.split(",") if o.strip()]

# In non-production, also allow localhost for development
if not IS_PRODUCTION:
    _dev_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    for origin in _dev_origins:
        if origin not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(origin)

# ── Swagger / OpenAPI docs ───────────────────────────────────────────────────
# In production, docs are disabled unless explicitly enabled
_enable_docs_raw = os.getenv("ENABLE_DOCS", "")
if _enable_docs_raw:
    ENABLE_DOCS = _enable_docs_raw.lower() in ("true", "1", "yes")
else:
    ENABLE_DOCS = not IS_PRODUCTION

# ── Rate limiting (requests per minute) ──────────────────────────────────────
RATE_LIMIT_LOGIN = int(os.getenv("RATE_LIMIT_LOGIN", "5"))
RATE_LIMIT_REFRESH = int(os.getenv("RATE_LIMIT_REFRESH", "10"))
RATE_LIMIT_REGISTER = int(os.getenv("RATE_LIMIT_REGISTER", "3"))
RATE_LIMIT_FORGOT_PASSWORD = int(os.getenv("RATE_LIMIT_FORGOT_PASSWORD", "3"))

# ── Request body size limit ──────────────────────────────────────────────────
MAX_REQUEST_BODY_MB = int(os.getenv("MAX_REQUEST_BODY_MB", "2"))

# ── JWT ──────────────────────────────────────────────────────────────────────
JWT_ISSUER = os.getenv("JWT_ISSUER", "apterfinancial")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "apterfinancial-web")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "10"))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "14"))

# ── Lockout ──────────────────────────────────────────────────────────────────
LOCKOUT_THRESHOLD = int(os.getenv("LOCKOUT_THRESHOLD", "5"))
LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))

# ── Refresh Token Cookie ────────────────────────────────────────────────
REFRESH_COOKIE_NAME = "apter_refresh"
REFRESH_COOKIE_PATH = "/auth"

# ── Password Reset ──────────────────────────────────────────────────────
PASSWORD_RESET_TOKEN_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_MINUTES", "15"))
