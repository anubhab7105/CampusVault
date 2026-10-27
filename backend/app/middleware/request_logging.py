"""Structured request logging.

Mandated fields per request (docs/04_BACKEND_GUIDE.md):
  request_id, user_id, endpoint, duration, status_code.
The line is single-line JSON, ingestible by any log collector.
"""

from __future__ import annotations

import logging

from flask import Flask, Response, request
from flask_jwt_extended import get_jwt_identity

from app.middleware.request_context import current_request_id, elapsed_ms
from app.utils.logging_utils import log_json


def register_request_logging(app: Flask) -> None:
    @app.after_request
    def _log_request(response: Response) -> Response:
        # Prefer the concrete route rule so template paths (never raw URLs) are logged.
        path = request.environ.get("PATH_INFO", "")
        if request.url_rule is not None:
            path = request.url_rule.rule

        user_id = None
        if request.path.startswith("/api"):
            try:
                user_id = get_jwt_identity()
            except RuntimeError:
                user_id = None

        log_json(
            logging.INFO,
            "http_request",
            request_id=current_request_id(),
            user_id=user_id,
            endpoint=path,
            method=request.method,
            duration_ms=round(elapsed_ms(), 2),
            status_code=response.status_code,
        )
        return response
