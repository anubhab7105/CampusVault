"""
Chat domain service. Implements the service logic specified in
API_SPEC_CHAT.md. Per that spec: "the socket handlers and the REST history
endpoint both go through the same service-layer function to avoid divergent
logic" — this is that shared layer. Both app/blueprints/chat.py and
app/sockets/chat_sockets.py call into this, never duplicate its logic.
"""
import logging
import uuid

from sqlalchemy.orm import Session

from app.models.chat import ContentType, GroupType, ReceiptStatus
from app.repositories.auth_repository import AuthRepository
from app.repositories.chat_repository import ChatRepository
from app.utils.exceptions import ForbiddenError, NotFoundError, ValidationError

logger = logging.getLogger("campusvault.chat")


class ChatService:
    def __init__(self, db: Session, socketio=None):
        self.db = db
        self.repo = ChatRepository(db)
        self.auth_repo = AuthRepository(db)
        # Optional/injectable, mirrors NotificationsService — real callers
        # pass the app's socketio instance; tests can omit it.
        self.socketio = socketio

    # ---------- Authorization (shared by REST + sockets) ----------

    def assert_participant(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """The same check both the socket room-join handler and the REST
        history endpoint use, per API_SPEC_CHAT.md."""
        conversation = self.repo.get_conversation_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError("Conversation not found.", code="CONVERSATION_NOT_FOUND")
        if not self.repo.is_participant(conversation_id, user_id):
            raise ForbiddenError("Not a participant in this conversation.", code="FORBIDDEN")

    # ---------- Conversations ----------

    def list_conversations(self, user_id: uuid.UUID) -> list[dict]:
        conversations = self.repo.list_conversations_for_user(user_id)
        results = []
        for conv in conversations:
            last_message = self.repo.get_last_message(conv.id)
            unread = self.repo.get_unread_count(conv.id, user_id)
            entry = {
                "id": conv.id,
                "type": conv.type.value,
                "last_message": last_message,
                "unread_count": unread,
            }
            if conv.type.value == "dm":
                other_id = self.repo.get_other_dm_participant(conv.id, user_id)
                entry["other_participant_id"] = other_id
            else:
                entry["group_id"] = conv.group_id
            results.append(entry)
        return results

    def start_dm(self, user_id: uuid.UUID, other_user_id: uuid.UUID) -> dict:
        if user_id == other_user_id:
            raise ValidationError("Cannot start a DM with yourself.", code="CANNOT_DM_SELF")
        if self.auth_repo.get_user_by_id(other_user_id) is None:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")

        existing = self.repo.find_existing_dm(user_id, other_user_id)
        if existing is not None:
            self.db.commit()
            return {"id": existing.id, "type": "dm", "created": False}

        conversation = self.repo.create_dm_conversation(user_id, other_user_id)
        self.db.commit()
        return {"id": conversation.id, "type": "dm", "created": True}

    # ---------- Message history (REST) ----------

    def get_message_history(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, before: uuid.UUID | None, limit: int = 50
    ) -> dict:
        self.assert_participant(conversation_id, user_id)
        messages = self.repo.list_messages_before(conversation_id, before, limit + 1)
        has_more = len(messages) > limit
        page = messages[:limit]

        items = []
        for m in page:
            items.append({
                "id": m.id,
                "sender_id": m.sender_id,
                "content": None if m.deleted_at else m.content,
                "content_type": m.content_type,
                "edited_at": m.edited_at,
                "deleted": m.deleted_at is not None,
                "created_at": m.created_at,
                "receipt_summary": self.repo.get_receipt_counts(m.id),
            })

        return {
            "items": items,
            "has_more": has_more,
            "next_cursor": page[-1].id if page and has_more else None,
        }

    # ---------- Messages (shared by REST-adjacent flows and Socket.IO handlers) ----------

    def send_message(
        self, conversation_id: uuid.UUID, sender_id: uuid.UUID, content: str, content_type: ContentType
    ) -> dict:
        self.assert_participant(conversation_id, sender_id)
        message = self.repo.create_message(conversation_id, sender_id, content, content_type)
        self.db.commit()

        self._notify_offline_participants(conversation_id, sender_id, content)

        return self._message_to_dict(message)

    def _notify_offline_participants(self, conversation_id: uuid.UUID, sender_id: uuid.UUID, content: str) -> None:
        """
        Resolves the dependency documented in API_SPEC_CHAT.md /
        API_SPEC_NOTIFICATIONS.md: a message.new for an offline participant
        creates a Notifications row via a direct in-process service call —
        not a REST call, not knowledge of Chat internals leaking into
        Notifications. Failures here must never break message sending.
        """
        from app.services.notifications_service import NotificationsService
        from app.utils import presence

        try:
            conversation = self.repo.get_conversation_by_id(conversation_id)
            if conversation is None:
                return
            participant_ids = self.repo.list_participant_ids(conversation_id)
            sender = self.auth_repo.get_user_by_id(sender_id)
            sender_name = sender.full_name if sender else "Someone"

            notifications_service = NotificationsService(self.db, socketio=self.socketio)
            for user_id in participant_ids:
                if user_id == sender_id:
                    continue
                if presence.is_online(user_id):
                    continue  # they'll see it live via message.new in the socket room
                preview = content[:140]
                notifications_service.create_for_user(
                    user_id=user_id,
                    type_="message.new",
                    title=f"New message from {sender_name}",
                    body=preview,
                    data={"conversation_id": str(conversation_id)},
                )
        except Exception:
            logger.exception("Failed to notify offline participants for conversation %s", conversation_id)

    def edit_message(self, message_id: uuid.UUID, editor_id: uuid.UUID, content: str) -> dict:
        message = self.repo.get_message_by_id(message_id)
        if message is None:
            raise NotFoundError("Message not found.", code="MESSAGE_NOT_FOUND")
        if message.sender_id != editor_id:
            raise ForbiddenError("Cannot edit another user's message.", code="FORBIDDEN")
        if message.deleted_at is not None:
            raise ValidationError("Cannot edit a deleted message.", code="MESSAGE_DELETED")

        message = self.repo.edit_message(message, content)
        self.db.commit()
        return self._message_to_dict(message)

    def delete_message(self, message_id: uuid.UUID, deleter_id: uuid.UUID) -> dict:
        message = self.repo.get_message_by_id(message_id)
        if message is None:
            raise NotFoundError("Message not found.", code="MESSAGE_NOT_FOUND")
        if message.sender_id != deleter_id:
            raise ForbiddenError("Cannot delete another user's message.", code="FORBIDDEN")

        message = self.repo.soft_delete_message(message)
        self.db.commit()
        return self._message_to_dict(message)

    def _message_to_dict(self, message) -> dict:
        return {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "sender_id": message.sender_id,
            "content": None if message.deleted_at else message.content,
            "content_type": message.content_type,
            "edited_at": message.edited_at,
            "deleted": message.deleted_at is not None,
            "created_at": message.created_at,
        }

    # ---------- Receipts ----------

    def mark_delivered(self, message_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Per OPEN_DECISIONS.md: delivery_status fires automatically when a
        connected client receives message.new — this is that automatic path,
        called from the socket layer, not exposed via REST.
        """
        if self.repo.get_receipt(message_id, user_id, ReceiptStatus.DELIVERED) is not None:
            return  # idempotent — already recorded
        self.repo.create_receipt(message_id, user_id, ReceiptStatus.DELIVERED)
        self.db.commit()

    def mark_read(self, message_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        message = self.repo.get_message_by_id(message_id)
        if message is None:
            raise NotFoundError("Message not found.", code="MESSAGE_NOT_FOUND")

        if self.repo.get_receipt(message_id, user_id, ReceiptStatus.READ) is None:
            self.repo.create_receipt(message_id, user_id, ReceiptStatus.READ)
        self.db.commit()
        return self.repo.get_receipt_counts(message_id)

    # ---------- Groups (custom) ----------

    def list_groups(self, user_id: uuid.UUID, group_type: GroupType | None = None) -> list:
        return self.repo.list_groups_for_user(user_id, group_type)

    def create_group(self, name: str, description: str | None, created_by: uuid.UUID) -> dict:
        group, conversation = self.repo.create_custom_group_with_conversation(name, description, created_by)
        self.db.commit()
        return {"group": group, "conversation_id": conversation.id}

    def update_group(self, group_id: uuid.UUID, actor_id: uuid.UUID, name: str | None, description: str | None):
        group = self.repo.get_group_by_id(group_id)
        if group is None:
            raise NotFoundError("Group not found.", code="GROUP_NOT_FOUND")
        self._assert_group_admin(group_id, actor_id)
        group = self.repo.update_group(group, name, description)
        self.db.commit()
        return group

    def delete_group(self, group_id: uuid.UUID, actor_id: uuid.UUID) -> None:
        group = self.repo.get_group_by_id(group_id)
        if group is None:
            raise NotFoundError("Group not found.", code="GROUP_NOT_FOUND")
        if group.type == GroupType.SECTION:
            raise ValidationError("Section groups cannot be deleted directly.", code="CANNOT_DELETE_SECTION_GROUP")
        self._assert_group_admin(group_id, actor_id)
        self.repo.soft_delete_group(group)
        self.db.commit()

    def _assert_group_admin(self, group_id: uuid.UUID, user_id: uuid.UUID) -> None:
        from app.models.chat import GroupMemberRole
        member = self.repo.get_group_member(group_id, user_id)
        if member is None or member.role_in_group != GroupMemberRole.ADMIN:
            raise ForbiddenError("Must be a group admin for this action.", code="FORBIDDEN")

    def add_group_member(self, group_id: uuid.UUID, actor_id: uuid.UUID, user_id: uuid.UUID) -> None:
        group = self.repo.get_group_by_id(group_id)
        if group is None:
            raise NotFoundError("Group not found.", code="GROUP_NOT_FOUND")
        if group.type == GroupType.SECTION:
            raise ValidationError("Section group membership is managed via the Academic domain.", code="CANNOT_MODIFY_SECTION_GROUP")
        self._assert_group_admin(group_id, actor_id)
        if self.repo.get_group_member(group_id, user_id) is not None:
            raise ValidationError("User is already a member.", code="ALREADY_MEMBER")

        self.repo.add_group_member(group_id, user_id)
        conversation = self.repo.get_conversation_by_group_id(group_id)
        if conversation is not None:
            self.repo.add_conversation_participant(conversation.id, user_id)
        self.db.commit()

    def remove_group_member(self, group_id: uuid.UUID, actor_id: uuid.UUID, user_id: uuid.UUID) -> None:
        group = self.repo.get_group_by_id(group_id)
        if group is None:
            raise NotFoundError("Group not found.", code="GROUP_NOT_FOUND")
        if group.type == GroupType.SECTION:
            raise ValidationError("Section group membership is managed via the Academic domain.", code="CANNOT_MODIFY_SECTION_GROUP")
        self._assert_group_admin(group_id, actor_id)

        self.repo.remove_group_member(group_id, user_id)
        conversation = self.repo.get_conversation_by_group_id(group_id)
        if conversation is not None:
            self.repo.remove_conversation_participant(conversation.id, user_id)
        self.db.commit()
