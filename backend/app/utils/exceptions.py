"""
Centralized application exceptions, per 04_BACKEND_GUIDE.md: "Centralize
exception handling" and "Never expose stack traces."

Every domain raises one of these from the service layer; a single Flask
error handler (see app/middleware/error_handler.py) converts them to the
locked error envelope from 08_API_GUIDE.md. Blueprints never build error
JSON by hand.
"""


class AppError(Exception):
    """Base for all deliberate, expected application errors."""
    http_status: int = 400
    code: str = "APP_ERROR"

    def __init__(self, message: str, code: str | None = None, http_status: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if http_status:
            self.http_status = http_status


class ValidationError(AppError):
    http_status = 400
    code = "VALIDATION_ERROR"


class UnauthorizedError(AppError):
    http_status = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    http_status = 403
    code = "FORBIDDEN"


class NotFoundError(AppError):
    http_status = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    http_status = 409
    code = "CONFLICT"


class RateLimitedError(AppError):
    http_status = 429
    code = "RATE_LIMITED"
