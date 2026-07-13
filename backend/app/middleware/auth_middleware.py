"""
Auth middleware. Validates the JWT access token on protected routes and
attaches the current user's identity to Flask's `g` for downstream use.

Per 04_BACKEND_GUIDE.md request flow: Client -> Middleware -> Blueprint ->
Validation -> Service -> Repository -> Database -> Response. This is the
Middleware step for anything requiring authentication.
"""
import uuid
from functools import wraps

import jwt
from flask import g, request

from app.utils.exceptions import ForbiddenError, UnauthorizedError
from app.utils.security import decode_access_token


def get_bearer_token() -> str | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header[len("Bearer "):].strip()


def require_auth(fn):
    """Decorator: rejects the request with 401 UNAUTHORIZED unless a valid access token is present."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = get_bearer_token()
        if not token:
            raise UnauthorizedError("Missing bearer token.")
        try:
            payload = decode_access_token(token)
        except jwt.ExpiredSignatureError:
            raise UnauthorizedError("Access token expired.")
        except jwt.InvalidTokenError:
            raise UnauthorizedError("Invalid access token.")

        g.user_id = uuid.UUID(payload["sub"])
        g.user_type = payload.get("user_type")
        g.roles = payload.get("roles", [])
        return fn(*args, **kwargs)
    return wrapper


def require_permission(permission_code: str):
    """
    Decorator factory per the RBAC middleware contract in API_SPEC_RBAC.md.

    Resolves the caller's effective permissions via RBACService (user ->
    roles -> permissions). This hits the DB on every call; API_SPEC_RBAC.md
    flags Redis caching as a follow-up once this is a proven hot path
    (10_PERFORMANCE_GUIDE.md: profile before optimizing — not done blindly
    here). Admins bypass the check by convention (user_type=admin).
    """
    def decorator(fn):
        @wraps(fn)
        @require_auth
        def wrapper(*args, **kwargs):
            if g.user_type == "admin":
                return fn(*args, **kwargs)

            from flask import current_app

            from app.services.rbac_service import RBACService

            rbac_service = RBACService(db=current_app.extensions["db_session"]())
            if not rbac_service.user_has_permission(g.user_id, permission_code):
                raise ForbiddenError(f"Missing required permission: {permission_code}")
            return fn(*args, **kwargs)
        return wrapper
    return decorator
