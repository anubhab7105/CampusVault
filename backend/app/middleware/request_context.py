"""Request identity + timing context.

Every request (including unauthenticated ones) gets a ``request_id``. The
value is reused from ``X-Request-ID`` when the caller supplies a plausible
one (bounded length, printable) so distributed tracing can join logs across
Nginx, the backend, and Celery workers.
"""

from __future__ import annotations

import secrets
import string
import time

from flask import Flask, g, request

REQUEST_ID_ALPHABET = string.ascii_lowercase + string.digits
REQUEST_ID_MAX_LENGTH = 64


def _sanitize_request_id(value: str | None) -> str:
    if value and 0 < len(value) <= REQUEST_ID_MAX_LENGTH:
        return "".join(
            ch if (ch.isalnum() or ch in "-_.") else "_" for ch in value
        )
    return secrets.token_hex(8)


def register_request_context(app: Flask) -> None:
    @app.before_request
    def _begin() -> None:
        g.request_started_at = time.perf_counter()
        g.request_id = _sanitize_request_id(request.headers.get("X-Request-ID"))


def current_request_id() -> str | None:
    try:
        return g.request_id  # type: ignore[attr-defined]
    except (AttributeError, RuntimeError):
        return None


def elapsed_ms() -> float:
    try:
        return (time.perf_counter() - g.request_started_at) * 1000.0  # type: ignore[attr-defined]
    except (AttributeError, KeyError):
        return 0.0
