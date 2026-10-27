"""Middleware registration.

Order matters and mirrors the request flow documented in
docs/04_BACKEND_GUIDE.md: request context (IDs/timing) must exist before
logging runs, and security headers must attach to every response.
JWT enforcement itself is applied per-blueprint/endpoint (auth decorators),
because public endpoints (health, auth) must opt out explicitly.
"""

from __future__ import annotations

from flask import Flask

from app.middleware.request_context import register_request_context
from app.middleware.request_logging import register_request_logging
from app.middleware.security_headers import register_security_headers


def register_middleware(app: Flask) -> None:
    """Attach the standard before/after-request chain."""
    register_request_context(app)
    register_security_headers(app)
    register_request_logging(app)
