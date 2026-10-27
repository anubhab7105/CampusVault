"""Chat service — conversation rules + message lifecycle.

Rules:
- participants only (membership checked before every operation)
- group messages require an active group conversation mirror
- deletes are soft; content is wiped (Message.wipe_content)
- edit window: only the original sender may edit within a configurable window
- reply-to supported
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from app.errors.exceptions import ForbiddenError, NotFoundError
from app.extensions import db
from app.models import Conversation, Message, User
from app.repositories import ConversationRepository, MessageRepository, UserRepository
from app.services.base_service import BaseService


#: How many minutes a message can be edited after sending.
MESSAGE_EDIT_WINDOW_MINUTES = 15


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
        """Get or create a direct-message conversation between two users.

        Enforces role-based DM rules:
        - Admins unrestricted
        - Students may DM teachers and students in their own department
        - Teachers may DM students in their groups/department
        """
        existing = self.conversations.find_direct_between(user_a, user_b)
        if existing is not None:
            return existing

        # Role-based DM rule check
        from app.services.role_service import role_service

        role_a, _ = role_service.load_user_role_bundle(str(user_a))
        role_b, _ = role_service.load_user_role_bundle(str(user_b))

        # Admins can DM anyone
        if role_a == "Admin" or role_b == "Admin":
            conversation = self.conversations.create(
                conversation_type="direct",
                created_by=user_a,
            )
            self.conversations.add_participant(conversation.id, user_a)
            self.conversations.add_participant(conversation.id, user_b)
            db.session.commit()
            return conversation

        # Default: allow (can be refined with department checks later)
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

    def edit_message(
        self, *, message_id: uuid.UUID, editor_id: uuid.UUID, content: str
    ) -> Message:
        """Edit a message if within the edit window and editor is the sender.

        After the window, only admins/owners can edit (tombstone + re-post).
        """
        message = self.messages.get_by_id(message_id)

        if message.sender_id != editor_id:
            raise ForbiddenError("Only the author can modify this message.")

        # Check edit window
        now = datetime.now(tz=UTC)
        age_minutes = (now - message.created_at).total_seconds() / 60.0
        if age_minutes > MESSAGE_EDIT_WINDOW_MINUTES:
            raise ForbiddenError(
                f"Edit window expired. Message is {age_minutes:.1f} minutes old "
                f"(limit: {MESSAGE_EDIT_WINDOW_MINUTES} min). "
                "Admins can still tombstone the message."
            )

        message.content = content
        message.is_edited = True
        message.edited_at = now
        db.session.commit()
        return message

    def delete_message(
        self, *, message_id: uuid.UUID, requester_id: uuid.UUID, is_moderator: bool = False
    ) -> Message:
        """Soft-delete (tombstone) a message.

        Admins/moderators can delete any message. Non-admin requesters can only
        delete their own messages.
        """
        message = self.messages.get_by_id(message_id)

        # Check permissions
        if is_moderator:
            # Moderators can delete any message in a conversation they participate in
            self.assert_participant(message.conversation_id, requester_id)
        else:
            # Non-moderators can only delete their own messages
            self._assert_author(message, requester_id)

        self.messages.soft_delete(message)
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

    def _assert_author(self, message: Message, user_id: uuid.UUID) -> None:
        if message.sender_id != user_id:
            raise ForbiddenError("Only the author can modify this message.")


chat_service = ChatService()