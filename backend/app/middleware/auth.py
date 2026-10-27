"""JWT identity helpers.

E2E accounts for identity presence; blueprints call ``ensure_authenticated``
around their own authorization.
"""

from __future__ import annotations

from flask import g
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from app.errors.exceptions import UnauthorizedError

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

