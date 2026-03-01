# Platform/api/app/security/middleware.py
"""
Security middleware stack for Apter Financial API.

1. SecurityHeadersMiddleware — adds HSTS, X-Content-Type-Options,
   X-Frame-Options, Referrer-Policy, Permissions-Policy, X-Request-ID.
2. RequestSizeLimitMiddleware — rejects bodies exceeding configured max size.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.security.config import IS_PRODUCTION, MAX_REQUEST_BODY_MB


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach security headers to every response and generate a request ID."""

    async def dispatch(self, request: Request, call_next):
        # Generate request ID for tracing / audit correlation
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response: Response = await call_next(request)

        # ── Security headers ──
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["X-XSS-Protection"] = "0"  # Modern browsers; CSP is better

        if IS_PRODUCTION:
            # HSTS: 1 year, include subdomains, preload-ready
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # CSP — API returns JSON, not HTML. Restrictive default.
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject request bodies that exceed the configured maximum size."""

    def __init__(self, app, max_mb: int = MAX_REQUEST_BODY_MB):
        super().__init__(app)
        self.max_bytes = max_mb * 1024 * 1024

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body exceeds {MAX_REQUEST_BODY_MB}MB limit"},
            )
        return await call_next(request)
