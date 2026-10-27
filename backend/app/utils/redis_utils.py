"""Redis client factory — one shared, lazily-created client per process."""

from __future__ import annotations

import redis
from flask import current_app

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Shared Redis client bound to the current app config.

    Used by the JWT blocklist, rate limiting (Flask-Limiter has its own URI
    from config), OTP storage and socket auth caches.
    """
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            current_app.config["REDIS_URL"],
            decode_responses=True,
        )
    return _client
