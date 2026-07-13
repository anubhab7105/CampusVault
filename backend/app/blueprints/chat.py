"""
Chat blueprint. Per API_SPEC_CHAT.md: REST covers conversation listing,
message history, and group CRUD. Message send/edit/delete are Socket.IO
events (see app/sockets/chat_sockets.py), not exposed here.
"""
import uuid

from flask import Blueprint, g, request

from app.middleware.auth_middleware import require_auth
from app.models.chat import GroupType
from app.schemas.chat import GroupCreateRequest, GroupMemberAddRequest, GroupUpdateRequest, StartDMRequest
from app.services.chat_service import ChatService
from app.utils.responses import success

chat_bp = Blueprint("chat", __name__, url_prefix="/api/v1/chat")


def _get_service() -> ChatService:
    from flask import current_app
    return ChatService(db=current_app.extensions["db_session"]())


def _serialize_conversation(entry: dict) -> dict:
    last = entry.get("last_message")
    out = {
        "id": str(entry["id"]),
        "type": entry["type"],
        "unread_count": entry["unread_count"],
        "last_message": None if last is None else {
            "content": last.content,
            "sender_id": str(last.sender_id),
            "created_at": last.created_at.isoformat(),
        },
    }
    if "other_participant_id" in entry:
        out["other_participant_id"] = str(entry["other_participant_id"]) if entry["other_participant_id"] else None
    if "group_id" in entry:
        out["group_id"] = str(entry["group_id"]) if entry["group_id"] else None
    return out


def _serialize_message(m: dict) -> dict:
    return {
        "id": str(m["id"]),
        "sender_id": str(m["sender_id"]),
        "content": m["content"],
        "content_type": m["content_type"].value if hasattr(m["content_type"], "value") else m["content_type"],
        "edited_at": m["edited_at"].isoformat() if m["edited_at"] else None,
        "deleted": m["deleted"],
        "created_at": m["created_at"].isoformat(),
        **({"receipt_summary": m["receipt_summary"]} if "receipt_summary" in m else {}),
    }


@chat_bp.get("/conversations")
@require_auth
def list_conversations():
    service = _get_service()
    conversations = service.list_conversations(g.user_id)
    return success({"items": [_serialize_conversation(c) for c in conversations]})


@chat_bp.post("/conversations/dm")
@require_auth
def start_dm():
    payload = StartDMRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    result = service.start_dm(g.user_id, payload.user_id)
    return success({"id": str(result["id"]), "type": result["type"]}, status=201 if result["created"] else 200)


@chat_bp.get("/conversations/<uuid:conversation_id>/messages")
@require_auth
def get_message_history(conversation_id: uuid.UUID):
    before = request.args.get("before")
    limit = int(request.args.get("limit", 50))
    service = _get_service()
    result = service.get_message_history(
        conversation_id, g.user_id, uuid.UUID(before) if before else None, limit
    )
    return success({
        "items": [_serialize_message(m) for m in result["items"]],
        "has_more": result["has_more"],
        "next_cursor": str(result["next_cursor"]) if result["next_cursor"] else None,
    })


@chat_bp.get("/groups")
@require_auth
def list_groups():
    type_filter = request.args.get("type")
    service = _get_service()
    groups = service.list_groups(g.user_id, GroupType(type_filter) if type_filter else None)
    return success({"items": [{"id": str(g_.id), "name": g_.name, "type": g_.type.value} for g_ in groups]})


@chat_bp.post("/groups")
@require_auth
def create_group():
    payload = GroupCreateRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    result = service.create_group(payload.name, payload.description, created_by=g.user_id)
    return success({
        "id": str(result["group"].id),
        "name": result["group"].name,
        "conversation_id": str(result["conversation_id"]),
    }, status=201)


@chat_bp.patch("/groups/<uuid:group_id>")
@require_auth
def update_group(group_id: uuid.UUID):
    payload = GroupUpdateRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    group = service.update_group(group_id, g.user_id, payload.name, payload.description)
    return success({"id": str(group.id), "name": group.name, "description": group.description})


@chat_bp.delete("/groups/<uuid:group_id>")
@require_auth
def delete_group(group_id: uuid.UUID):
    service = _get_service()
    service.delete_group(group_id, g.user_id)
    return success({}, message="Group deleted.")


@chat_bp.get("/groups/<uuid:group_id>/members")
@require_auth
def list_group_members(group_id: uuid.UUID):
    service = _get_service()
    members = service.repo.list_group_members(group_id)
    return success({"items": [{"user_id": str(m.user_id), "role": m.role_in_group.value} for m in members]})


@chat_bp.post("/groups/<uuid:group_id>/members")
@require_auth
def add_group_member(group_id: uuid.UUID):
    payload = GroupMemberAddRequest.model_validate(request.get_json(force=True))
    service = _get_service()
    service.add_group_member(group_id, g.user_id, payload.user_id)
    return success({}, message="Member added.", status=201)


@chat_bp.delete("/groups/<uuid:group_id>/members/<uuid:user_id>")
@require_auth
def remove_group_member(group_id: uuid.UUID, user_id: uuid.UUID):
    service = _get_service()
    service.remove_group_member(group_id, g.user_id, user_id)
    return success({}, message="Member removed.")
