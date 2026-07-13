"""
Centralized exception handling per 04_BACKEND_GUIDE.md: "Centralize
exception handling. Never expose stack traces."

Registered once on the Flask app factory (see app/__init__.py once built).
"""
import logging

from flask import Flask
from pydantic import ValidationError as PydanticValidationError

from app.utils.exceptions import AppError
from app.utils.responses import error

logger = logging.getLogger("campusvault")


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(exc: AppError):
        return error(exc.code, exc.message, exc.http_status)

    @app.errorhandler(PydanticValidationError)
    def handle_validation_error(exc: PydanticValidationError):
        # First error message only, kept generic — full field-level detail
        # goes to logs, not the client response (avoid leaking schema internals).
        first = exc.errors()[0]
        field = ".".join(str(p) for p in first["loc"])
        return error("VALIDATION_ERROR", f"Invalid value for '{field}'.", 400)

    @app.errorhandler(404)
    def handle_404(exc):
        return error("NOT_FOUND", "Resource not found.", 404)

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        # Never expose stack traces or internal messages to the client.
        logger.exception("Unhandled exception")
        return error("INTERNAL_ERROR", "An unexpected error occurred.", 500)
