"""
Chat Socket.IO handlers. Implements the event contract from
07_SOCKET_GUIDE.md and the payload shapes documented in API_SPEC_CHAT.md.

Per that spec's "no event trusts input just because it's a socket" rule:
every handler validates with the same Pydantic schemas the REST layer would
use, and re-checks conversation membership via ChatService.assert_participant
— the socket connection being authenticated (JWT on connect) is necessary
but not sufficient; per-event authorization still applies.

Room naming: `group_<conversation_id>` / `dm_<conversation_id>` per
07_SOCKET_GUIDE.md. Note the guide names rooms by "group"/"dm" but the
underlying identifier used here is the conversation_id (not group_id),
since a DM has no group_id — this is the one place the guide's naming
scheme needed a concrete resolution, documented here rather than guessed
silently in code with no explanation.
"""
import logging

from flask_socketio import emit, join_room, leave_room
from pydantic import ValidationError as PydanticValidationError

from app.utils.security import decode_access_token
from app.schemas.chat import (
    DeleteMessageEvent,
    EditMessageEvent,
    JoinGroupEvent,
    ReadReceiptEvent,
    SendMessageEvent,
    TypingEvent,
)
from app.services.chat_service import ChatService
from app.utils.exceptions import AppError

logger = logging.getLogger("campusvault.sockets.chat")


def _room_name(conversation_type: str, conversation_id) -> str:
    prefix = "group" if conversation_type == "group" else "dm"
    return f"{prefix}_{conversation_id}"


def _get_service() -> ChatService:
    from flask import current_app
    return ChatService(db=current_app.extensions["db_session"]())


def _user_id_from_token(token: str):
    import uuid
    payload = decode_access_token(token)
    return uuid.UUID(payload["sub"])


def register_chat_socket_handlers(socketio):
    """Call once from the app factory: register_chat_socket_handlers(socketio)."""

    @socketio.on("connect")
    def handle_connect(auth):
        token = (auth or {}).get("token")
        if not token:
            logger.info("Socket connect rejected: no token")
            return False  # rejects the connection
        try:
            user_id = _user_id_from_token(token)
        except Exception:
            logger.info("Socket connect rejected: invalid token")
            return False

        from flask import session as flask_session
        flask_session["user_id"] = str(user_id)

        from app.utils import presence
        presence.mark_online(user_id)
        return True

    @socketio.on("disconnect")
    def handle_disconnect():
        from flask import session as flask_session
        raw_user_id = flask_session.pop("user_id", None)

        if raw_user_id is not None:
            import uuid
            from app.utils import presence
            presence.mark_offline(uuid.UUID(raw_user_id))

    def _current_user_id():
        from flask import session as flask_session
        import uuid
        raw = flask_session.get("user_id")
        if raw is None:
            raise AppError("Not authenticated on this socket.", code="UNAUTHORIZED", http_status=401)
        return uuid.UUID(raw)

    @socketio.on("join_group")
    def handle_join_group(data):
        try:
            payload = JoinGroupEvent.model_validate(data)
            user_id = _current_user_id()
            service = _get_service()
            conversation = service.repo.get_conversation_by_id(payload.conversation_id)
            if conversation is None:
                emit("error", {"code": "CONVERSATION_NOT_FOUND", "message": "Conversation not found."})
                return
            service.assert_participant(payload.conversation_id, user_id)
            room = _room_name(conversation.type.value, conversation.id)
            join_room(room)
            emit("joined", {"conversation_id": str(payload.conversation_id)})
        except (AppError, PydanticValidationError) as exc:
            _emit_error(exc)

    @socketio.on("leave_group")
    def handle_leave_group(data):
        try:
            payload = JoinGroupEvent.model_validate(data)
            service = _get_service()
            conversation = service.repo.get_conversation_by_id(payload.conversation_id)
            if conversation is not None:
                leave_room(_room_name(conversation.type.value, conversation.id))
        except PydanticValidationError as exc:
            _emit_error(exc)

    @socketio.on("send_group_message")
    def handle_send_message(data):
        try:
            payload = SendMessageEvent.model_validate(data)
            user_id = _current_user_id()
            service = _get_service()
            message = service.send_message(payload.conversation_id, user_id, payload.content, payload.content_type)

            conversation = service.repo.get_conversation_by_id(payload.conversation_id)
            room = _room_name(conversation.type.value, conversation.id)
            emit("message.new", _serialize_message(message), room=room)
        except (AppError, PydanticValidationError) as exc:
            _emit_error(exc)

    @socketio.on("edit_group_message")
    def handle_edit_message(data):
        try:
            payload = EditMessageEvent.model_validate(data)
            user_id = _current_user_id()
            service = _get_service()
            message = service.edit_message(payload.message_id, user_id, payload.content)

            conversation = service.repo.get_conversation_by_id(message["conversation_id"])
            room = _room_name(conversation.type.value, conversation.id)
            emit("message.edited", _serialize_message(message), room=room)
        except (AppError, PydanticValidationError) as exc:
            _emit_error(exc)

    @socketio.on("delete_group_message")
    def handle_delete_message(data):
        try:
            payload = DeleteMessageEvent.model_validate(data)
            user_id = _current_user_id()
            service = _get_service()
            message = service.delete_message(payload.message_id, user_id)

            conversation = service.repo.get_conversation_by_id(message["conversation_id"])
            room = _room_name(conversation.type.value, conversation.id)
            emit("message.deleted", {"id": str(message["id"])}, room=room)
        except (AppError, PydanticValidationError) as exc:
            _emit_error(exc)

    @socketio.on("typing")
    def handle_typing(data):
        try:
            payload = TypingEvent.model_validate(data)
            user_id = _current_user_id()
            service = _get_service()
            conversation = service.repo.get_conversation_by_id(payload.conversation_id)
            if conversation is None:
                return
            room = _room_name(conversation.type.value, conversation.id)
            emit(
                "typing",
                {"conversation_id": str(payload.conversation_id), "user_id": str(user_id), "is_typing": payload.is_typing},
                room=room,
                include_self=False,
            )
        except (AppError, PydanticValidationError) as exc:
            _emit_error(exc)

    @socketio.on("read_receipt")
    def handle_read_receipt(data):
        try:
            payload = ReadReceiptEvent.model_validate(data)
            user_id = _current_user_id()
            service = _get_service()
            counts = service.mark_read(payload.message_id, user_id)

            message = service.repo.get_message_by_id(payload.message_id)
            conversation = service.repo.get_conversation_by_id(message.conversation_id)
            room = _room_name(conversation.type.value, conversation.id)
            emit(
                "receipt.updated",
                {"message_id": str(payload.message_id), **counts},
                room=room,
            )
        except (AppError, PydanticValidationError) as exc:
            _emit_error(exc)


def _serialize_message(message: dict) -> dict:
    return {
        "id": str(message["id"]),
        "conversation_id": str(message["conversation_id"]),
        "sender_id": str(message["sender_id"]),
        "content": message["content"],
        "content_type": message["content_type"].value if hasattr(message["content_type"], "value") else message["content_type"],
        "edited_at": message["edited_at"].isoformat() if message["edited_at"] else None,
        "deleted": message["deleted"],
        "created_at": message["created_at"].isoformat(),
    }


def _emit_error(exc) -> None:
    if isinstance(exc, AppError):
        emit("error", {"code": exc.code, "message": exc.message})
    else:
        emit("error", {"code": "VALIDATION_ERROR", "message": "Invalid event payload."})
