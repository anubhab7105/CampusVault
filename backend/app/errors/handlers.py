"""Global error handlers.

Contract: every failure leaves the process as the canonical error envelope
with a stable code, the right status code, and *no stack trace or internals*.
Unknown exceptions are logged server-side (`app.logger.exception`) and
masked as INTERNAL_ERROR on the wire.
"""

from __future__ import annotations

import marshmallow
import sqlalchemy.exc
import werkzeug.exceptions
from flask import Flask
from flask_limiter.errors import RateLimitExceeded
from jwt import PyJWTError  # type: ignore[import-not-found]

from app.errors.exceptions import AppError
from app.utils.responses import error_response


def _register_framework_handlers(app: Flask) -> None:
    """Map framework/library errors onto the envelope."""

    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limited(err: RateLimitExceeded) -> tuple:
        return error_response(
            "RATE_LIMITED",
            "Too many requests. Please slow down.",
            status_code=429,
        )

    @app.errorhandler(AppError)
    def handle_app_error(err: AppError) -> tuple:
        if err.log_error:
            app.logger.error("app_error code=%s message=%s", err.code, err.message)
        return error_response(
            err.code,
            err.message,
            status_code=err.status_code,
            details=err.details,
        )

    @app.errorhandler(marshmallow.ValidationError)
    def handle_marshmallow_validation(err: marshmallow.ValidationError) -> tuple:
        return error_response(
            "VALIDATION_ERROR",
            "The submitted payload is invalid.",
            status_code=400,
            details=err.messages if isinstance(err.messages, dict) else None,
        )

    @app.errorhandler(werkzeug.exceptions.HTTPException)
    def handle_http_exception(err: werkzeug.exceptions.HTTPException) -> tuple:
        # werkzeug HTTP errors (404/405/413/…) normalized into the envelope.
        return error_response(
            err.name.upper().replace(" ", "_"),
            err.description or "Request failed.",
            status_code=err.code or 500,
        )

    @app.errorhandler(sqlalchemy.exc.NoResultFound)
    def handle_no_result(_err: sqlalchemy.exc.NoResultFound) -> tuple:
        return error_response("NOT_FOUND", "Resource not found.", status_code=404)

    @app.errorhandler(sqlalchemy.exc.IntegrityError)
    def handle_integrity(err: sqlalchemy.exc.IntegrityError) -> tuple:
        app.logger.warning("integrity_error %s", type(err.orig).__name__)
        return (
            error_response(
                "CONFLICT", "The request conflicts with existing state.", status_code=409
            ),
            409,
        )

    @app.errorhandler(PyJWTError)
    def handle_jwt_error(err: PyJWTError) -> tuple:
        app.logger.warning("jwt_error %s", type(err).__name__)
        return error_response("UNAUTHORIZED", "Invalid or expired token.", status_code=401)

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception) -> tuple:
        # Log full traceback server-side; mask everything on the wire.
        app.logger.exception("unhandled_error type=%s", type(err).__name__)
        return error_response(
            "INTERNAL_ERROR", "An unexpected error occurred.", status_code=500
        )


def _register_jwt_handlers(app: Flask) -> None:
    """flask-jwt-extended error surface normalized to the envelope."""

    @jwt.expired_token_loader
    def expired(_hdr: str, _payload: dict) -> tuple:
        return error_response("UNAUTHORIZED", "Token has expired.", status_code=401)

    @jwt.invalid_token_loader
    def invalid(_reason: str) -> tuple:
        return error_response("UNAUTHORIZED", "Invalid token.", status_code=401)

    @jwt.unauthorized_loader
    def missing(_reason: str) -> tuple:
        return error_response("UNAUTHORIZED", "Authentication required.", status_code=401)

    @jwt.needs_fresh_token_loader
    def needs_fresh(_hdr: str, _payload: dict) -> tuple:
        return error_response("UNAUTHORIZED", "Fresh token required.", status_code=401)

    @jwt.revoked_token_loader
    def revoked(_hdr: str, _payload: dict) -> tuple:
        return error_response("UNAUTHORIZED", "Token has been revoked.", status_code=401)


def register_error_handlers(app: Flask) -> None:
    _register_framework_handlers(app)
    _register_jwt_handlers(app)
