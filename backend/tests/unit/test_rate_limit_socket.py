"""Socket.IO rate-limit (throttle) tests.

Tests the ``socket_throttle`` decorator directly using a fake Redis so the
tests do not depend on a running Redis server.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


class FakeRedis:
    """Minimal in-memory Redis stand-in for throttle tests."""

    def __init__(self) -> None:
        self._store: dict[str, int] = {}
        self._ttls: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self._store[key] = self._store.get(key, 0) + 1
        return self._store[key]

    def expire(self, key: str, ttl: int) -> None:
        self._ttls[key] = ttl

    def delete(self, *keys: str) -> None:
        for key in keys:
            self._store.pop(key, None)
            self._ttls.pop(key, None)


@pytest.fixture
def fake_redis():
    return FakeRedis()


class TestSocketThrottle:
    def test_socket_throttle_normal_traffic(self, app, fake_redis):
        from app.errors.exceptions import ForbiddenError
        from app.utils.rate_limit import RATELIMIT_SOCKET_MESSAGE, socket_throttle

        calls = []

        @socket_throttle(RATELIMIT_SOCKET_MESSAGE)  # 30 / 30 seconds
        def handler(payload=None):
            calls.append(payload)
            return "ok"

        with app.test_request_context("/"):
            from flask import request
            request.sid = "sid-1"

            with patch(
                "app.utils.redis_utils.get_redis", return_value=fake_redis
            ), patch(
                "app.services.connections.user_id_for_session",
                return_value="user-1",
            ):
                for i in range(30):
                    result = handler(payload={"i": i})
                    assert result == "ok"
                # 31st exceeds the limit.
                with pytest.raises(ForbiddenError):
                    handler(payload={"i": 30})

    def test_socket_throttle_users_independent(self, app, fake_redis):
        from app.errors.exceptions import ForbiddenError
        from app.utils.rate_limit import RATELIMIT_SOCKET_JOIN, socket_throttle

        @socket_throttle(RATELIMIT_SOCKET_JOIN)  # 60 / minute
        def handler(payload=None):
            return "ok"

        with app.test_request_context("/"):
            from flask import request
            with patch(
                "app.utils.redis_utils.get_redis", return_value=fake_redis
            ):
                # User 1 exhausts their limit.
                with patch(
                    "app.services.connections.user_id_for_session",
                    return_value="user-1",
                ):
                    request.sid = "sid-1"
                    for _ in range(60):
                        handler()
                    with pytest.raises(ForbiddenError):
                        handler()

                # User 2 is unaffected (different Redis key).
                with patch(
                    "app.services.connections.user_id_for_session",
                    return_value="user-2",
                ):
                    request.sid = "sid-2"
                    result = handler()
                    assert result == "ok"

    def test_socket_throttle_unauthenticated_passthrough(self, app, fake_redis):
        from app.utils.rate_limit import RATELIMIT_SOCKET_READ, socket_throttle

        @socket_throttle(RATELIMIT_SOCKET_READ)
        def handler(payload=None):
            return "ok"

        with app.test_request_context("/"):
            from flask import request
            request.sid = "sid-anon"

            with patch(
                "app.utils.redis_utils.get_redis", return_value=fake_redis
            ), patch(
                "app.services.connections.user_id_for_session",
                return_value=None,  # not authenticated
            ):
                # Not throttled — passes through.
                assert handler() == "ok"
