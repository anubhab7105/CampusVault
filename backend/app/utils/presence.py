"""
Shared presence tracking, per OPEN_DECISIONS.md section 5: Redis key scheme
`presence:user:{user_id}`, written on socket connect/disconnect with TTL
refresh. Used by both app/sockets/chat_sockets.py (to know whether to emit
live) and app/services/notifications_service.py (to know whether to push a
socket event or rely on the durable REST/DB queue) — this is the shared
helper API_SPEC_NOTIFICATIONS.md flagged as needed to avoid duplicating the
logic in both places.
"""
import os
import uuid

import redis

_PRESENCE_TTL_SECONDS = 60  # refreshed on each heartbeat/event; expires if a client vanishes without disconnect firing
_KEY_PREFIX = "presence:user:"

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True
        )
    return _redis_client


def _key(user_id: uuid.UUID) -> str:
    return f"{_KEY_PREFIX}{user_id}"


def mark_online(user_id: uuid.UUID, client: redis.Redis | None = None) -> None:
    r = client or get_redis_client()
    r.set(_key(user_id), "1", ex=_PRESENCE_TTL_SECONDS)


def mark_offline(user_id: uuid.UUID, client: redis.Redis | None = None) -> None:
    r = client or get_redis_client()
    r.delete(_key(user_id))


def is_online(user_id: uuid.UUID, client: redis.Redis | None = None) -> bool:
    r = client or get_redis_client()
    return r.exists(_key(user_id)) == 1


def refresh(user_id: uuid.UUID, client: redis.Redis | None = None) -> None:
    """Call periodically (e.g. on any inbound socket event) to extend the TTL for an active session."""
    r = client or get_redis_client()
    r.expire(_key(user_id), _PRESENCE_TTL_SECONDS)
