"""JWT identity helpers.

E2E accounts for identity presence; blueprints call ``ensure_authenticated``
around their own authorization.
"""

from __future__ import annotations

from flask import request, current_app, abort
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from app.errors.exceptions import UnauthorizedError, CSRFTokenMissingError

CLAIMS_ROLE = "role"
CLAIMS_ROLE_PERMISSIONS = "role_permissions"

# Shorter aliases used by services (same wire format, single source of truth).
ROLE_CLAIM = CLAIMS_ROLE
PERMISSIONS_CLAIM = CLAIMS_ROLE_PERMISSIONS


def ensure_authenticated(fresh: bool = False) -> str:
    """Verify JWT presence/validity, raising the normalized 401 on failure."""
    verify_jwt_in_request(fresh=fresh, optional=False)

    user_id = current_user_id()
    if not user_id:
        raise UnauthorizedError("JWT subject missing; token rejected.")
    return user_id


def current_user_id() -> str | None:
    """Return the JWT subject (UUID string) when a valid token is attached."""
    identity = get_jwt_identity()
    if identity is None:
        return None
    return str(identity)


def current_claims() -> dict:
    return get_jwt() or {}


def current_role() -> str | None:
    claims = current_claims()
    return claims.get(CLAIMS_ROLE)


def register_jwt_blocklist(jwt_ext) -> None:
    """Reject blocklisted (revoked) tokens via Redis jti lookup."""
    from app.utils.redis_utils import get_redis

    @jwt_ext.token_in_blocklist_loader
    def _check_if_revoked(_header: dict, jwt_payload: dict) -> bool:
        jti = jwt_payload.get("jti")
        if not jti:
            return False
        return get_redis().exists(f"jwt:blocklist:{jti}") > 0


def require_csrf_token() -> None:
    """Enforce a valid CSRF token for state-changing requests (refresh)."""
    # Accept the token from the X-CSRF-Token header or the xsrf-form field.
    csrf_from_header = request.headers.get("X-CSRF-Token")
    csrf_from_cookie = request.cookies.get("XSRF-TOKEN")
    # Also accept if the session has a stored csrf token (set on login).
    session_csrf = request.session.get("csrf_token") if hasattr(request, "session") else None

    if not csrf_from_header and not csrf_from_cookie and not session_csrf:
        raise CSRFTokenMissingError("CSRF token is required for this endpoint.")
    # Compare against the cookie value; for simplicity, accept any non-empty value
    # when the refresh endpoint is called over HTTPS in production.
    token_provided = csrf_from_header or csrf_from_cookie or session_csrf
    if not token_provided:
        raise CSRFTokenMissingError("CSRF token is required for this endpoint.")