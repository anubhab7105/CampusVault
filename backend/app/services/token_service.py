"""Token issuing/rotation/revocation.

Contract (docs/06_SECURITY_GUIDE.md):
- access token: short-lived JWT, subject = user UUID, claims carry the role
  name + effective permission list so RBAC checks need no DB round-trip
- refresh token: long-lived, rotated on use; used refresh tokens are
  jti-blocklisted in Redis until natural expiry, so stolen tokens die fast
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    verify_jwt_in_request,
)

from app.errors.exceptions import UnauthorizedError
from app.middleware.auth import PERMISSIONS_CLAIM, ROLE_CLAIM
from app.utils.redis_utils import get_redis

BLOCKLIST_PREFIX = "jwt:blocklist:"


class TokenService:
    """Pure token operations; identity loading lives in AuthService."""

    @staticmethod
    def issue_for_user(user_id: uuid.UUID, role: str, permissions: list[str]) -> dict:
        identity = str(user_id)
        claims = {ROLE_CLAIM: role, PERMISSIONS_CLAIM: list(permissions)}
        return {
            "access_token": create_access_token(identity=identity, additional_claims=claims),
            "refresh_token": create_refresh_token(identity=identity, additional_claims=claims),
        }

    @staticmethod
    def rotate() -> dict:
        """Refresh-token rotation: verify, blocklist the old, issue a new pair.

        Role/permission claims are re-derived from the database at rotation
        time, so permission changes take effect without waiting for expiry.
        """
        verify_jwt_in_request(refresh=True)
        user_id = get_jwt_identity()
        if not user_id:
            raise UnauthorizedError("Refresh token is invalid.")

        claims = get_jwt()
        ttl = max(int(claims["exp"] - datetime.now(tz=UTC).timestamp()), 1)
        TokenService._blocklist(claims["jti"], ttl)

        from app.services.role_service import role_service

        role, permissions = role_service.load_user_role_bundle(uuid.UUID(str(user_id)))
        return TokenService.issue_for_user(uuid.UUID(str(user_id)), role, permissions)

    @staticmethod
    def revoke_current_refresh() -> None:
        claims = get_jwt()
        if claims.get("type") != "refresh":
            raise UnauthorizedError("Refresh token required.")
        ttl = max(int(claims["exp"] - datetime.now(tz=UTC).timestamp()), 1)
        TokenService._blocklist(claims["jti"], ttl)

    @staticmethod
    def _blocklist(jti: str, ttl_seconds: int) -> None:
        get_redis().setex(f"{BLOCKLIST_PREFIX}{jti}", ttl_seconds, "1")
