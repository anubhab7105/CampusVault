"""Presence tracking in Redis: online users, sid↔user mapping, room bookkeeping.

Backed by Redis (shared across gunicorn workers), which also feeds the
offline-notification decision (`is_online`).
"""

from __future__ import annotations

from app.utils.redis_utils import get_redis

PREFIX_USERS = "presence:users"
PREFIX_SID = "presence:sid"
TTL_SESSIONS = 60 * 60 * 24  # stale sid cleanup after a day


def register_connection(user_id: str, sid: str) -> None:
    redis = get_redis()
    redis.sadd(f"{PREFIX_USERS}:{user_id}", sid)
    redis.set(f"{PREFIX_SID}:{sid}", user_id, ex=TTL_SESSIONS)


def unregister_connection(sid: str) -> None:
    redis = get_redis()
    user_id = user_id_for_session(sid)
    if user_id:
        redis.srem(f"{PREFIX_USERS}:{user_id}", sid)
    redis.delete(f"{PREFIX_SID}:{sid}")


def user_id_for_session(sid: str) -> str | None:
    return get_redis().get(f"{PREFIX_SID}:{sid}")


def is_online(user_id: str) -> bool:
    return bool(get_redis().exists(f"{PREFIX_USERS}:{user_id}"))
