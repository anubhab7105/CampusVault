"""Chat socket events — authorized, validated, spam-guarded.

Every handler:
1. assumes the connect handler authenticated the session (sid→user in Redis)
2. authorizes the action against the database (rooms are never trusted)
3. validates payloads with the same marshmallow schemas as REST
4. performs the service call, then emits to rooms (never to "everyone")

Errors never kill the session: failures reply on `socket_error`.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC
from functools import wraps

from flask import request
from flask_socketio import emit

from app.errors.exceptions import AppError, ForbiddenError
from app.extensions import socketio
from app.schemas.message_schema import SendGroupMessageSchema
from app.services.audit_service import audit_service
from app.services.chat_service import chat_service
from app.services.connections import user_id_for_session
from app.services.group_service import group_service
from app.sockets.rooms import dm_room, group_room, join_group_room, leave_group_room
from app.utils.validation import build_validation_error


def socket_errors(view: Callable) -> Callable:
    """Uniform error surface for every socket event."""

    @wraps(view)
    def wrapper(payload=None, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            return view(payload, *args, **kwargs)
        except AppError as err:
            emit(
                "socket_error",
                {"success": False, "error": {"code": err.code, "message": err.message}},
                to=request.sid,
            )

    return wrapper


def _require_user() -> str:
    user_id = user_id_for_session(request.sid)
    if not user_id:
        raise ForbiddenError("Socket session is not authenticated.")
    return user_id


def _payload_dict(payload) -> dict:  # type: ignore[no-untyped-def]
    return payload if isinstance(payload, dict) else {}


@socketio.on("join_group")
@socket_errors
def on_join_group(payload=None) -> None:  # type: ignore[no-untyped-def]
    user_id = _require_user()
    data = _payload_dict(payload)
    group_id_raw = str(data.get("group_id") or "")
    room_group_id = join_group_room(request.sid, user_id, group_id_raw)
    emit(
        "join_group",
        {"success": True, "message": f"Joined group_{room_group_id}.", "data": {}},
        to=request.sid,
    )


@socketio.on("leave_group")
@socket_errors
def on_leave_group(payload=None) -> None:  # type: ignore[no-untyped-def]
    _require_user()
    data = _payload_dict(payload)
    leave_group_room(request.sid, str(data.get("group_id") or ""))
    emit("leave_group", {"success": True, "message": "Left room.", "data": {}}, to=request.sid)


@socketio.on("send_group_message")
@socket_errors
def on_send_group_message(payload=None) -> None:  # type: ignore[no-untyped-def]
    user_id = _require_user()
    data = _payload_dict(payload)
    _check_spam(user_id)

    from marshmallow import ValidationError as MarshmallowValidationError

    try:
        validated = SendGroupMessageSchema().load(data)
    except MarshmallowValidationError as exc:
        raise build_validation_error(exc.messages) from exc

    conversation = chat_service.conversations.get_by_id(validated["conversation_id"])
    if conversation is None:
        raise ForbiddenError("Conversation not found.")

    if conversation.conversation_type == "group" and conversation.group_id:
        group_service.assert_membership(
            uuid.UUID(str(conversation.group_id)), uuid.UUID(user_id)
        )
    chat_service.assert_participant(validated["conversation_id"], uuid.UUID(user_id))

    message = chat_service.send_group_message(
        conversation_id=validated["conversation_id"],
        sender_id=uuid.UUID(user_id),
        content=validated["content"],
        reply_to_id=validated["reply_to_id"],
    )
    room = (
        group_room(uuid.UUID(str(conversation.group_id)))
        if conversation.group_id
        else dm_room(conversation.id)
    )
    socketio.send(
        {
            "success": True,
            "message": "Message delivered.",
            "data": {
                "message": {
                    "id": str(message.id),
                    "conversation_id": validated["conversation_id"],
                    "content": message.content,
                    "sender_id": user_id,
                }
            },
        },
        to=room,
    )
    emit(
        "delivery_status",
        {"success": True, "message": "Accepted.", "data": {"message_id": str(message.id)}},
        to=request.sid,
    )


@socketio.on("edit_group_message")
@socket_errors
def on_edit_group_message(payload=None) -> None:  # type: ignore[no-untyped-def]
    user_id = _require_user()
    data = _payload_dict(payload)
    message_id = str(data.get("message_id") or "")
    content = str(data.get("content") or "")
    if not message_id or not content:
        raise build_validation_error(
            {"message_id": ["message_id and content are required."]}
        )
    chat_service.edit_group_message(
        message_id=uuid.UUID(message_id), editor_id=uuid.UUID(user_id), content=content
    )
    emit(
        "edit_group_message",
        {"success": True, "message": "Message updated.", "data": {"message_id": message_id}},
        to=request.sid,
    )


@socketio.on("delete_group_message")
@socket_errors
def on_delete_group_message(payload=None) -> None:  # type: ignore[no-untyped-def]
    user_id = _require_user()
    data = _payload_dict(payload)
    message_id = str(data.get("message_id") or "")
    if not message_id:
        raise build_validation_error({"message_id": ["message_id is required."]})
    chat_service.delete_group_message(
        message_id=uuid.UUID(message_id), requester_id=uuid.UUID(user_id)
    )
    audit_service.record(
        action="chat.message.delete",
        entity_type="message",
        entity_id=uuid.UUID(message_id),
    )
    emit(
        "delete_group_message",
        {"success": True, "message": "Message deleted.", "data": {"message_id": message_id}},
        to=request.sid,
    )


@socketio.on("typing")
@socket_errors
def on_typing(payload=None) -> None:  # type: ignore[no-untyped-def]
    user_id = _require_user()
    data = _payload_dict(payload)
    conversation_id = str(data.get("conversation_id") or "")
    if not conversation_id:
        return
    chat_service.assert_participant(uuid.UUID(conversation_id), uuid.UUID(user_id))
    emit(
        "typing",
        {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "typing": bool(data.get("typing", True)),
        },
        include_self=False,
    )


@socketio.on("read_receipt")
@socket_errors
def on_read_receipt(payload=None) -> None:  # type: ignore[no-untyped-def]
    user_id = _require_user()
    data = _payload_dict(payload)
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
@socket_errors
def on_delivery_status(payload=None) -> None:  # type: ignore[no-untyped-def]
    user_id = _require_user()
    data = _payload_dict(payload)
    message_id = str(data.get("message_id") or "")
    if not message_id:
        return
    message = chat_service.messages.get_by_id(uuid.UUID(message_id))
    if message is not None and str(message.sender_id) == user_id:
        from datetime import datetime

        chat_service.messages.mark_delivered(message.id, datetime.now(tz=UTC))
        from app.extensions import db

        db.session.commit()


def _check_spam(user_id: str) -> None:
    """Token bucket: 30 messages / 30 s. Excess increments a strike counter."""
    from app.utils.redis_utils import get_redis

    MESSAGE_BUDGET = 30
    MESSAGE_WINDOW_SECONDS = 30

    redis = get_redis()
    key = f"chat:rate:{user_id}:{MESSAGE_WINDOW_SECONDS}s"
    count = redis.incr(key)
    if count == 1:
        redis.expire(key, MESSAGE_WINDOW_SECONDS)
    if count > MESSAGE_BUDGET:
        strike_key = f"chat:strikes:{user_id}"
        redis.incr(strike_key)
        redis.expire(strike_key, 300)
        raise ForbiddenError("Sending too fast. Please slow down.")
