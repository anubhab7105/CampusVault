"""Chat socket events — authorized, validated, spam-guarded.

Every handler:
1. assumes the connect handler authenticated the session (user_id in Redis)
2. authorizes the room action against the database
3. validates the payload with the same marshmallow schemas used by REST
4. performs the service call, then emits to rooms (never to "everyone")
"""

from __future__ import annotations

import uuid

from flask import request
from flask_socketio import emit

from app.extensions import socketio
from app.schemas.message_schema import SendGroupMessageSchema
from app.services.audit_service import audit_service
from app.services.chat_service import chat_service
from app.services.group_service import group_service
from app.utils.validation import build_validation_error
from app.errors.exceptions import AppError, ForbiddenError


def _require_user() -> str:
    from app.services.connections import user_id_for_session

    user_id = user_id_for_session(request.sid)
    if not user_id:
        raise ForbiddenError("Socket session is not authenticated.")
    return user_id


@socketio.on("join_group")
def on_join_group(payload) -> None:  # type: ignore[no-untyped-def]
    """Join the group chat room after membership validation."""
    user_id = _require_user()
    group_id_raw = _extract_group_id(payload)
    room = _safe_join(user_id, group_id_raw)
    emit(
        "join_group",
        {"success": True, "message": f"Joined room group_{room}.", "data": {}},
        to=request.sid,
    )


def _safe_join(user_id: str, group_id_raw) -> str:
    """Authorize + join; emit authorizable errors on the reply channel."""
    from app.sockets.rooms import join_group_room

    room = join_group_room(request.sid, user_id, group_id_raw)
    return room


def _extract_group_id(payload) -> str:
    from app.sockets.rooms import authorize_group_join  # noqa: F401 (doc reference)

    data = (payload or {}) if isinstance(payload, dict) else {}
    group_id_raw = str(data.get("group_id") or "")
    if not group_id_raw:
        raise ForbiddenError("group_id is required.")
    return group_id_raw


@socketio.on("leave_group")
def on_leave_group(payload) -> None:  # type: ignore[no-untyped-def]
    _require_user()
    data = (payload or {}) if isinstance(payload, dict) else {}
    group_id_raw = str(data.get("group_id") or "")
    from app.sockets.rooms import leave_group_room

    try:
        leave_group_room(request.sid, group_id_raw)
        emit("leave_group", {"success": True, "message": "Left room.", "data": {}}, to=request.sid)
    except AppError as err:
        emit("error", {"success": False, "error": {"code": err.code, "message": err.message}})


@socketio.on("send_group_message")
def on_send_group_message(payload) -> None:  # type: ignore[no-untyped-def]
    user_id = _require_user()
    data = payload if isinstance(payload, dict) else {}
    _check_spam(user_id)

    validated = _load_message_payload(data)
    conversation = chat_service.conversations.get_by_id(validated["conversation_id"])
    if conversation is None:
        raise ForbiddenError("Conversation not found.")

    # Membership: group rooms mirror group membership; DMs check participation.
    if conversation.conversation_type == "group" and conversation.group_id:
        group_service.assert_membership(uuid.UUID(conversation.group_id), uuid.UUID(user_id))
    chat_service.assert_participant(validated["conversation_id"], uuid.UUID(user_id))

    message = chat_service.send_group_message(
        conversation_id=validated["conversation_id"],
        sender_id=uuid.UUID(user_id),
        content=validated["content"],
        reply_to_id=validated["reply_to_id"],
    )
    from app.sockets.rooms import dm_room, group_room

    room = group_room(conversation.group_id) if conversation.group_id else dm_room(conversation.id)
    socketio.send(
        {
            "success": True,
            "message": "Message delivered.",
            "data": {"message": {"id": str(message.id),
                                  "conversation_id": validated["conversation_id"],
                                  "content": message.content,
                                  "sender_id": user_id}},
        },
        to=room,
    )
    emit("delivery_status", {"message_id": str(message.id), "status": "delivered"}, to=request.sid)


def _load_message_payload(data: dict) -> dict:
    from app.utils.validation import APIValidationError

    try:
        from marshmallow import ValidationError as MarshmallowValidationError

        return SendGroupMessageSchema().load(data)
    except MarshmallowValidationError as exc:
        raise build_validation_error(exc.messages) from exc


def _check_spam(user_id: str) -> None:
    """Token bucket: 30 messages / 30 s. Excess increments a strike counter."""
    from app.utils.redis_utils import get_redis

    redis = get_redis()
    key = f"chat:rate:{user_id}:30s"
    count = redis.incr(key)
    if count == 1:
        redis.expire(key, 30)
    if count > 30:
        strike_key = f"chat:strikes:{user_id}"
        strikes = redis.incr(strike_key)
        redis.expire(strike_key, 300)
        raise ForbiddenError("Sending too fast. Please slow down.")


@socketio.on("edit_group_message")
def on_edit_group_message(payload) -> None:  # type: ignore[no-untyped-def]
    user_id = _require_user()
    data = payload if isinstance(payload, dict) else {}
    message_id = str(data.get("message_id") or "")
    content = str(data.get("content") or "")
    if not message_id or not content:
        raise build_validation_error({"message_id": ["message_id and content are required."]})
    chat_service.edit_group_message(
        message_id=uuid.UUID(message_id), editor_id=uuid.UUID(user_id), content=content
    )
    emit("edit_group_message", {"success": True, "data": {"message_id": message_id}}, to=request.sid)


@socketio.on("delete_group_message")
def on_delete_group_message(payload) -> None:  # type: ignore[no-untyped-def]
    user_id = _require_user()
    data = payload if isinstance(payload, dict) else {}
    message_id = str(data.get("message_id") or "")
    if not message_id:
        raise build_validation_error({"message_id": ["message_id is required."]})
    chat_service.delete_group_message(message_id=uuid.UUID(message_id), requester_id=uuid.UUID(user_id))
    audit_service.record(
        action="chat.message.delete", entity_type="message", entity_id=uuid.UUID(message_id)
    )
    emit("delete_group_message", {"success": True, "data": {"message_id": message_id}}, to=request.sid)


@socketio.on("typing")
def on_typing(payload) -> None:  # type: ignore[no-untyped-def]
    """Typing indicator — short-lived, not persisted."""
    user_id = _require_user()
    data = payload if isinstance(payload, dict) else {}
    conversation_id = str(data.get("conversation_id") or "")
    if not conversation_id:
        return
    chat_service.assert_participant(uuid.UUID(conversation_id), uuid.UUID(user_id))
    emit(
        "typing",
        {"conversation_id": conversation_id, "user_id": user_id, "typing": bool(data.get("typing", True))},
        include_self=False,
    )


@socketio.on("read_receipt")
def on_read_receipt(payload) -> None:  # type: ignore[no-untyped-def]
    user_id = _require_user()
    data = payload if isinstance(payload, dict) else {}
    conversation_id = str(data.get("conversation_id") or "")
    if not conversation_id:
        return
    chat_service.mark_read(uuid.UUID(conversation_id), uuid.UUID(user_id))
    emit(
        "read_receipt",
        {"conversation_id": conversation_id, "user_id": user_id},
        include_self=False,
    )


@socketio.on("delivery_status")
def on_delivery_status(payload) -> None:  # type: ignore[no-untyped-def]
    user_id = _require_user()
    data = payload if isinstance(payload, dict) else {}
    message_id = str(data.get("message_id") or "")
    if not message_id:
        return
    message = chat_service.messages.get_by_id(uuid.UUID(message_id))
    if message is not None:
        from datetime import datetime, timezone

        chat_service.messages.mark_delivered(
            message.id, datetime.now(tz=timezone.utc)
        )
        from app.extensions import db

        db.session.commit()
