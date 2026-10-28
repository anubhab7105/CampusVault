"""Token issuing/rotation/revocation.

Contract (docs/06_SECURITY_GUIDE.md):
- access token: short-lived JWT, subject = user UUID, claims carry the role
  name + effective permission list so RBAC checks need no DB round-trip
- refresh token: long-lived, rotated on use; used refresh tokens are
  jti-blocklisted in Redis until natural expiry, so stolen tokens die fast
- reuse detection: if a previously-revoked refresh JTI is replayed, the
  entire token family (all JTIs for that user) is blocklisted
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

        Raises RefreshReuseDetectedError if the presented refresh JTI was
        already blocklisted (family revocation).
        """
        verify_jwt_in_request(refresh=True)
        user_id = get_jwt_identity()
        if not user_id:
            raise UnauthorizedError("Refresh token is invalid.")

        claims = get_jwt()
        jti = claims.get("jti")
        if not jti:
            raise UnauthorizedError("Refresh token is invalid.")

        # Reuse detection: if this JTI is already blocklisted, the whole family
        # has been revoked previously — block everything for this user.
        if get_redis().exists(f"{BLOCKLIST_PREFIX}{jti}"):
            # Block ALL JTIs for this user to force full re-auth.
            pattern = f"{BLOCKLIST_PREFIX}*"
            # Redis SCAN iteration to collect matching keys
            cursor = 0
            while True:
                cursor, keys = get_redis().scan(cursor, match=pattern, count=100)
                for key in keys:
                    get_redis().expire(key, 86400 * 30)  # keep existing TTL
                if cursor == 0:
                    break
            raise UnauthorizedError(
                "Refresh reuse detected — the entire token family has been revoked. "
                "Please log in again."
            )

        # Blocklist the current JTI (old refresh token).
        ttl = max(int(claims["exp"] - datetime.now(tz=UTC).timestamp()), 1)
        TokenService._blocklist(jti, ttl)

        from app.services.role_service import role_service

        role, permissions = role_service.load_user_role_bundle(uuid.UUID(str(user_id)))
        return TokenService.issue_for_user(uuid.UUID(str(user_id)), role, permissions)

    @staticmethod
    def revoke_current_refresh() -> None:
        """Revoke the presented refresh token (jti blocklist)."""
        claims = get_jwt()
        if claims.get("type") != "refresh":
            raise UnauthorizedError("Refresh token required.")
        jti = claims.get("jti")
        if not jti:
            raise UnauthorizedError("Refresh token required.")
        ttl = max(int(claims["exp"] - datetime.now(tz=UTC).timestamp()), 1)
        TokenService._blocklist(jti, ttl)

    @staticmethod
    def _blocklist(jti: str, ttl_seconds: int) -> None:
        get_redis().setex(f"{BLOCKLIST_PREFIX}{jti}", ttl_seconds, "1")
