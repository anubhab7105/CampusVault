"""Chat service — conversation rules + message lifecycle.

Rules:
- participants only (membership checked before every operation)
- group messages require an active group conversation mirror
- deletes are soft; content is wiped (`Message.wipe_content`)
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from app.errors.exceptions import ForbiddenError, NotFoundError
from app.extensions import db
from app.models import Conversation, Message
from app.repositories import ConversationRepository, MessageRepository
from app.services.base_service import BaseService


class ChatService(BaseService):
    def __init__(self) -> None:
        self.conversations = ConversationRepository()
        self.messages = MessageRepository()

    # --- conversations ------------------------------------------------------- #

    def get_group_conversation(self, group_id: uuid.UUID) -> Conversation:
        conversation = self.conversations.get_by_group(group_id)
        if conversation is None or not conversation.is_active:
            raise NotFoundError("Group conversation not available.")
        return conversation

    def get_dm_for(self, user_a: uuid.UUID, user_b: uuid.UUID) -> Conversation:
        existing = self.conversations.find_direct_between(user_a, user_b)
        if existing is not None:
            return existing
        conversation = self.conversations.create(
            conversation_type="direct",
            created_by=user_a,
        )
        self.conversations.add_participant(conversation.id, user_a)
        self.conversations.add_participant(conversation.id, user_b)
        db.session.commit()
        return conversation

    def assert_participant(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        if not self.conversations.is_participant(conversation_id, user_id):
            raise ForbiddenError("You are not a participant of this conversation.")

    # --- messages ------------------------------------------------------------- #

    def send_group_message(
        self,
        *,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        content: str,
        reply_to_id: uuid.UUID | None = None,
        message_type: str = "text",
    ) -> Message:
        self.assert_participant(conversation_id, sender_id)
        message = self.messages.create(
            conversation_id=conversation_id,
            sender_id=sender_id,
            message_type=message_type,
            content=content,
            reply_to_id=reply_to_id,
        )
        self.conversations.set_last_message_at(conversation_id, message.created_at)
        db.session.commit()
        return message

    def edit_group_message(self, *, message_id: uuid.UUID, editor_id: uuid.UUID, content: str) -> Message:
        message = self._get_message(message_id)
        self._assert_author(message, editor_id)
        message.content = content
        message.is_edited = True
        message.edited_at = datetime.now(tz=UTC)
        db.session.commit()
        return message

    def delete_group_message(
        self, *, message_id: uuid.UUID, requester_id: uuid.UUID, is_moderator: bool = False
    ) -> Message:
        message = self._get_message(message_id)
        if not is_moderator:
            self._assert_author(message, requester_id)
        self.messages.soft_delete(message)
        message.wipe_content()
        db.session.commit()
        return message

    def history(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        before_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> Sequence[Message]:
        self.assert_participant(conversation_id, user_id)
        return self.messages.history(conversation_id, before_id=before_id, limit=limit)

    def mark_read(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.assert_participant(conversation_id, user_id)
        self.conversations.update_last_read(conversation_id, user_id, datetime.now(tz=UTC))
        db.session.commit()

    # --- internals --------------------------------------------------------------- #

    def _get_message(self, message_id: uuid.UUID) -> Message:
        message = self.messages.get_by_id(message_id)
        if message is None or message.deleted_at is not None:
            raise NotFoundError("Message not found.")
        return message

    @staticmethod
    def _assert_author(message: Message, user_id: uuid.UUID) -> None:
        if message.sender_id != user_id:
            raise ForbiddenError("Only the author can modify this message.")


chat_service = ChatService()
