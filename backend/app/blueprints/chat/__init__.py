"""Chat blueprint — REST fallback for history + DM lifecycle.

Live sends/typing/edit/delete ride Socket.IO (docs/07_SOCKET_GUIDE.md); REST
covers pagination-heavy reads and fire-and-forget writes.
"""

from __future__ import annotations

import uuid

from flask import Blueprint, request

from app.middleware.auth import ensure_authenticated
from app.schemas.message_schema import MessageListQuerySchema, SendGroupMessageSchema
from app.services.chat_service import chat_service
from app.utils.responses import success_response
from app.utils.validation import ValidationError, get_json_body, load_schema

bp = Blueprint("chat", __name__, url_prefix="/api/v1/chat")

SERIALIZE_ATTRS = (
    "id",
    "conversation_id",
    "sender_id",
    "message_type",
    "content",
    "reply_to_id",
    "is_edited",
    "created_at",
)


def _serialize(message) -> dict:
    data = {attr: getattr(message, attr) for attr in SERIALIZE_ATTRS}
    data["id"] = str(data["id"])
    data["conversation_id"] = str(data["conversation_id"])
    data["sender_id"] = str(data["sender_id"]) if data["sender_id"] else None
    data["reply_to_id"] = str(data["reply_to_id"]) if data["reply_to_id"] else None
    data["created_at"] = data["created_at"].isoformat() if data["created_at"] else None
    return data


@bp.get("/conversations/<uuid:conversation_id>/messages")
def history(conversation_id: uuid.UUID):
    user_id = uuid.UUID(ensure_authenticated())
    query = load_schema(
        MessageListQuerySchema(),
        {"before_id": request.args.get("before_id"), "limit": request.args.get("limit")},
    )
    messages = chat_service.history(
        conversation_id,
        user_id,
        before_id=query["before_id"],
        limit=query["limit"],
    )
    return success_response(
        data={"items": [_serialize(m) for m in messages]}, message="History loaded."
    )


@bp.post("/conversations/<uuid:conversation_id>/messages")
def send_group_message(conversation_id: uuid.UUID):
    user_id = uuid.UUID(ensure_authenticated())
    body = load_schema(SendGroupMessageSchema(), get_json_body())
    if body.get("conversation_id") != conversation_id:
        raise ValidationError("conversation_id in path and body must match.")
    message = chat_service.send_group_message(
        conversation_id=conversation_id,
        sender_id=user_id,
        content=body["content"],
        reply_to_id=body["reply_to_id"],
    )
    return success_response(data=_serialize(message), status_code=201, message="Message sent.")


@bp.post("/conversations/dm/<uuid:peer_id>")
def open_dm(peer_id: uuid.UUID):
    user_id = uuid.UUID(ensure_authenticated())
    conversation = chat_service.get_dm_for(user_a=user_id, user_b=peer_id)
    return success_response(data={"id": str(conversation.id)}, message="Conversation ready.")


@bp.post("/conversations/<uuid:conversation_id>/read")
def mark_read(conversation_id: uuid.UUID):
    user_id = uuid.UUID(ensure_authenticated())
    chat_service.mark_read(conversation_id, user_id)
    return success_response(message="Read receipt recorded.")
