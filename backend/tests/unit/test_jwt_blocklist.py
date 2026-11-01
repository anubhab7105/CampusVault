"""Tests for the Redis-backed JWT blocklist configuration."""

from __future__ import annotations

from app.config import BaseConfig, ProductionConfig
from app.extensions import jwt
from app.middleware.auth import register_jwt_blocklist


def test_testing_config_skips_redis_blocklist_lookup(app):
    """Request tests must not require an external Redis process."""
    assert app.config["JWT_BLOCKLIST_ENABLED"] is False

    with app.app_context():
        assert jwt._token_in_blocklist_callback({}, {"jti": "test-jti"}) is False


def test_deployed_configs_keep_jwt_blocklist_enabled():
    """Revocation checks remain enabled by default outside test configuration."""
    assert BaseConfig.JWT_BLOCKLIST_ENABLED is True
    assert ProductionConfig.JWT_BLOCKLIST_ENABLED is True


def test_enabled_blocklist_still_rejects_revoked_tokens(app, monkeypatch):
    """The test override must not change the production callback behavior."""
    class FakeRedis:
        @staticmethod
        def exists(key: str) -> int:
            assert key == "jwt:blocklist:revoked-jti"
            return 1

    from app.utils import redis_utils

    original_get_redis = redis_utils.get_redis
    monkeypatch.setattr(redis_utils, "get_redis", lambda: FakeRedis())
    try:
        register_jwt_blocklist(jwt)
        app.config["JWT_BLOCKLIST_ENABLED"] = True

        with app.app_context():
            assert jwt._token_in_blocklist_callback({}, {"jti": "revoked-jti"}) is True
    finally:
        monkeypatch.setattr(redis_utils, "get_redis", original_get_redis)
        register_jwt_blocklist(jwt)
