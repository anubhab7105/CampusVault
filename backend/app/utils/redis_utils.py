"""Redis client factory — one shared, lazily-created client per process/URL."""

from __future__ import annotations

import redis
from flask import current_app

# URL-keyed cache; assignment (not `global`) so lint stays clean.
_client_cache: dict[str, redis.Redis] = {}


def get_redis() -> redis.Redis:
    """Shared Redis client bound to the current app config.

    Used by the JWT blocklist, OTP storage, presence tracking and socket
    caches. Flask-Limiter manages its own connection from `RATELIMIT_STORAGE_URI`.
    """
    url = current_app.config["REDIS_URL"]
    client = _client_cache.get(url)
    if client is None:
        client = redis.Redis.from_url(url, decode_responses=True)
        _client_cache[url] = client
    return client
