"""Conversation + participant persistence (group chats and DMs)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from app.extensions import db
from app.models import Conversation, ConversationParticipant, User
from app.repositories.base_repository import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    model = Conversation

    def get_by_group(self, group_id: uuid.UUID) -> Conversation | None:
        stmt = sa.select(Conversation).where(
            Conversation.group_id == group_id,
            Conversation.conversation_type == "group",
        )
        return db.session.scalar(stmt)

    def set_last_message_at(self, conversation_id: uuid.UUID, timestamp) -> None:
        stmt = (
            sa.update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_message_at=timestamp)
        )
        db.session.execute(stmt)

    def find_direct_between(
        self, user_a: uuid.UUID, user_b: uuid.UUID
    ) -> Conversation | None:
        """Single canonical DM conversation per unordered pair."""
        participants = ConversationParticipant
        stmt = (
            sa.select(Conversation)
            .join(participants, participants.conversation_id == Conversation.id)
            .where(
                Conversation.conversation_type == "direct",
                Conversation.is_active.is_(True),
                participants.user_id.in_([user_a, user_b]),
            )
            .group_by(Conversation.id)
            .having(sa.func.count(participants.user_id) == 2)
            .limit(1)
        )
        return db.session.scalar(stmt)

    def is_participant(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = (
            sa.select(ConversationParticipant.conversation_id)
            .where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
            .limit(1)
        )
        return db.session.scalar(stmt) is not None

    def add_participant(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, *, is_admin: bool = False
    ) -> ConversationParticipant:
        row = ConversationParticipant(
            conversation_id=conversation_id, user_id=user_id, is_admin=is_admin
        )
        db.session.add(row)
        return row

    def list_participants(self, conversation_id: uuid.UUID) -> Sequence[uuid.UUID]:
        stmt = sa.select(ConversationParticipant.user_id).where(
            ConversationParticipant.conversation_id == conversation_id
        )
        return list(db.session.scalars(stmt))

    def get_participant(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> ConversationParticipant | None:
        stmt = sa.select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user_id,
        )
        return db.session.scalar(stmt)

    def participant_usernames(self, conversation_id: uuid.UUID) -> dict[uuid.UUID, str]:
        stmt = (
            sa.select(User.id, User.full_name)
            .join(
                ConversationParticipant, ConversationParticipant.user_id == User.id
            )
            .where(ConversationParticipant.conversation_id == conversation_id)
        )
        return {user_id: name for user_id, name in db.session.execute(stmt)}

    def update_last_read(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, read_at
    ) -> int:
        stmt = (
            sa.update(ConversationParticipant)
            .where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
            .values(last_read_at=read_at)
        )
        result = db.session.execute(stmt)
        return int(result.rowcount or 0)
