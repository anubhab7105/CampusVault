"""Domain exception hierarchy.

Every exception maps 1:1 to an HTTP status and a stable error ``code`` that
the frontend can switch on (docs/08_API_GUIDE.md). Services raise these;
blueprints never translate HTTP codes by hand.
"""

from __future__ import annotations

from typing import Any

from app.constants import (
    CONFLICT,
    FORBIDDEN,
    INTERNAL_ERROR,
    NOT_FOUND,
    RATE_LIMITED,
    SERVICE_UNAVAILABLE,
    UNAUTHORIZED,
    VALIDATION_ERROR,
)


class AppError(Exception):
    """Base class for all expected, user-facing errors."""

    status_code: int = 500
    code: str = INTERNAL_ERROR
    default_message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
        log_error: bool = True,
    ) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.details = details
        self.log_error = log_error


class ValidationError(AppError):
    status_code = 400
    code = VALIDATION_ERROR
    default_message = "The submitted payload is invalid."


class UnauthorizedError(AppError):
    status_code = 401
    code = UNAUTHORIZED
    default_message = "Authentication required."


class ForbiddenError(AppError):
    status_code = 403
    code = FORBIDDEN
    default_message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = 404
    code = NOT_FOUND
    default_message = "Resource not found."


class ConflictError(AppError):
    status_code = 409
    code = CONFLICT
    default_message = "The request conflicts with existing state."


class RateLimitedError(AppError):
    status_code = 429
    code = RATE_LIMITED
    default_message = "Too many requests. Please slow down."


class ServiceUnavailableError(AppError):
    status_code = 503
    code = SERVICE_UNAVAILABLE
    default_message = "The service is temporarily unavailable."
