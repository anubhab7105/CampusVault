"""
Chat domain repository. Per 04_BACKEND_GUIDE.md: "Database access goes
through repositories." Covers conversations, groups, messages, and receipts
per API_SPEC_CHAT.md. Started minimal to support Academic's Section<->Group
coupling; now expanded to full scope for Chat's own backend implementation.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.chat import (
    Conversation,
    ConversationParticipant,
    ConversationType,
    ContentType,
    Group,
    GroupMember,
    GroupMemberRole,
    GroupType,
    Message,
    MessageReceipt,
    ReceiptStatus,
)


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------- Section <-> Group coupling (used by Academic domain) ----------

    def get_group_by_section_id(self, section_id: uuid.UUID) -> Group | None:
        return self.db.scalar(
            select(Group).where(Group.section_id == section_id, Group.deleted_at.is_(None))
        )

    def create_section_group_with_conversation(
        self, section_id: uuid.UUID, name: str, created_by: uuid.UUID
    ) -> tuple[Group, Conversation]:
        """Creates the Group + its Conversation together, per the documented coupling."""
        group = Group(name=name, type=GroupType.SECTION, section_id=section_id, created_by=created_by)
        self.db.add(group)
        self.db.flush()

        conversation = Conversation(type=ConversationType.GROUP, group_id=group.id)
        self.db.add(conversation)
        self.db.flush()

        return group, conversation

    # ---------- Groups (custom) ----------

    def get_group_by_id(self, group_id: uuid.UUID) -> Group | None:
        return self.db.scalar(select(Group).where(Group.id == group_id, Group.deleted_at.is_(None)))

    def list_groups_for_user(self, user_id: uuid.UUID, group_type: GroupType | None = None) -> list[Group]:
        stmt = (
            select(Group)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .where(GroupMember.user_id == user_id, Group.deleted_at.is_(None))
        )
        if group_type is not None:
            stmt = stmt.where(Group.type == group_type)
        return list(self.db.scalars(stmt.order_by(Group.name)))

    def create_custom_group_with_conversation(
        self, name: str, description: str | None, created_by: uuid.UUID
    ) -> tuple[Group, Conversation]:
        group = Group(name=name, description=description, type=GroupType.CUSTOM, created_by=created_by)
        self.db.add(group)
        self.db.flush()

        conversation = Conversation(type=ConversationType.GROUP, group_id=group.id)
        self.db.add(conversation)
        self.db.flush()

        # Creator is always an admin member of a group they create.
        self.add_group_member(group.id, created_by, role=GroupMemberRole.ADMIN)
        self.add_conversation_participant(conversation.id, created_by)

        return group, conversation

    def update_group(self, group: Group, name: str | None, description: str | None) -> Group:
        if name is not None:
            group.name = name
        if description is not None:
            group.description = description
        self.db.flush()
        return group

    def soft_delete_group(self, group: Group) -> None:
        group.deleted_at = datetime.now(timezone.utc)
        self.db.flush()

    def get_conversation_by_group_id(self, group_id: uuid.UUID) -> Conversation | None:
        return self.db.scalar(select(Conversation).where(Conversation.group_id == group_id))

    # ---------- Group membership ----------

    def get_group_member(self, group_id: uuid.UUID, user_id: uuid.UUID) -> GroupMember | None:
        return self.db.scalar(
            select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        )

    def list_group_members(self, group_id: uuid.UUID) -> list[GroupMember]:
        return list(self.db.scalars(select(GroupMember).where(GroupMember.group_id == group_id)))

    def add_group_member(
        self, group_id: uuid.UUID, user_id: uuid.UUID, role: GroupMemberRole = GroupMemberRole.MEMBER
    ) -> GroupMember:
        member = GroupMember(
            group_id=group_id, user_id=user_id, role_in_group=role, joined_at=datetime.now(timezone.utc)
        )
        self.db.add(member)
        self.db.flush()
        return member

    def remove_group_member(self, group_id: uuid.UUID, user_id: uuid.UUID) -> None:
        member = self.get_group_member(group_id, user_id)
        if member is not None:
            self.db.delete(member)
            self.db.flush()

    # ---------- Conversation participants ----------

    def is_participant(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return self.db.scalar(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
        ) is not None

    def add_conversation_participant(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> ConversationParticipant:
        participant = ConversationParticipant(
            conversation_id=conversation_id, user_id=user_id, joined_at=datetime.now(timezone.utc)
        )
        self.db.add(participant)
        self.db.flush()
        return participant

    def remove_conversation_participant(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        participant = self.db.scalar(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
        )
        if participant is not None:
            self.db.delete(participant)
            self.db.flush()

    # ---------- Conversations ----------

    def get_conversation_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        return self.db.scalar(select(Conversation).where(Conversation.id == conversation_id))

    def find_existing_dm(self, user_a: uuid.UUID, user_b: uuid.UUID) -> Conversation | None:
        """Finds a DM conversation containing exactly both given users."""
        from sqlalchemy.orm import aliased

        cp1 = aliased(ConversationParticipant)
        cp2 = aliased(ConversationParticipant)
        stmt = (
            select(Conversation)
            .join(cp1, and_(cp1.conversation_id == Conversation.id, cp1.user_id == user_a))
            .join(cp2, and_(cp2.conversation_id == Conversation.id, cp2.user_id == user_b))
            .where(Conversation.type == ConversationType.DM)
        )
        return self.db.scalar(stmt)

    def create_dm_conversation(self, user_a: uuid.UUID, user_b: uuid.UUID) -> Conversation:
        conversation = Conversation(type=ConversationType.DM)
        self.db.add(conversation)
        self.db.flush()
        self.add_conversation_participant(conversation.id, user_a)
        self.add_conversation_participant(conversation.id, user_b)
        return conversation

    def list_conversations_for_user(self, user_id: uuid.UUID) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .join(ConversationParticipant, ConversationParticipant.conversation_id == Conversation.id)
            .where(ConversationParticipant.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(self.db.scalars(stmt))

    def get_last_message(self, conversation_id: uuid.UUID) -> Message | None:
        return self.db.scalar(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )

    def get_unread_count(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> int:
        """Messages in this conversation, not sent by user_id, with no 'read' receipt from user_id."""
        read_message_ids = select(MessageReceipt.message_id).where(
            MessageReceipt.user_id == user_id, MessageReceipt.status == ReceiptStatus.READ
        )
        return self.db.scalar(
            select(func.count(Message.id)).where(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.deleted_at.is_(None),
                Message.id.not_in(read_message_ids),
            )
        ) or 0

    def get_other_dm_participant(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> uuid.UUID | None:
        return self.db.scalar(
            select(ConversationParticipant.user_id).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id != user_id,
            )
        )

    # ---------- Messages ----------

    def create_message(
        self, conversation_id: uuid.UUID, sender_id: uuid.UUID, content: str, content_type: ContentType
    ) -> Message:
        message = Message(
            conversation_id=conversation_id, sender_id=sender_id, content=content, content_type=content_type
        )
        self.db.add(message)

        # Touch the conversation so list_conversations_for_user's ordering
        # (by Conversation.updated_at) reflects actual last-message time —
        # without this, sending a message wouldn't move the conversation up.
        conversation = self.get_conversation_by_id(conversation_id)
        if conversation is not None:
            conversation.updated_at = datetime.now(timezone.utc)

        self.db.flush()
        return message

    def get_message_by_id(self, message_id: uuid.UUID) -> Message | None:
        return self.db.scalar(select(Message).where(Message.id == message_id))

    def edit_message(self, message: Message, content: str) -> Message:
        message.content = content
        message.edited_at = datetime.now(timezone.utc)
        self.db.flush()
        return message

    def soft_delete_message(self, message: Message) -> Message:
        message.deleted_at = datetime.now(timezone.utc)
        self.db.flush()
        return message

    def list_messages_before(self, conversation_id: uuid.UUID, before_id: uuid.UUID | None, limit: int) -> list[Message]:
        """
        Cursor-paginated, newest first. Orders and filters by (created_at, id)
        as a composite key, not created_at alone — timestamps can tie (e.g.
        Postgres's now() is transaction-scoped, so rows written in the same
        transaction can share an identical created_at), and a strict
        created_at-only comparison silently drops or duplicates rows when
        that happens. id is a UUID, not sequential, but it only needs to be
        a stable, unique tiebreaker for otherwise-equal timestamps.
        """
        stmt = select(Message).where(Message.conversation_id == conversation_id)
        if before_id is not None:
            before_message = self.get_message_by_id(before_id)
            if before_message is not None:
                stmt = stmt.where(
                    or_(
                        Message.created_at < before_message.created_at,
                        and_(
                            Message.created_at == before_message.created_at,
                            Message.id < before_message.id,
                        ),
                    )
                )
        return list(self.db.scalars(stmt.order_by(Message.created_at.desc(), Message.id.desc()).limit(limit)))

    # ---------- Message receipts ----------

    def get_receipt(self, message_id: uuid.UUID, user_id: uuid.UUID, status: ReceiptStatus) -> MessageReceipt | None:
        return self.db.scalar(
            select(MessageReceipt).where(
                MessageReceipt.message_id == message_id,
                MessageReceipt.user_id == user_id,
                MessageReceipt.status == status,
            )
        )

    def create_receipt(self, message_id: uuid.UUID, user_id: uuid.UUID, status: ReceiptStatus) -> MessageReceipt:
        receipt = MessageReceipt(
            message_id=message_id, user_id=user_id, status=status, status_at=datetime.now(timezone.utc)
        )
        self.db.add(receipt)
        self.db.flush()
        return receipt

    def get_receipt_counts(self, message_id: uuid.UUID) -> dict:
        delivered = self.db.scalar(
            select(func.count(MessageReceipt.id)).where(
                MessageReceipt.message_id == message_id, MessageReceipt.status == ReceiptStatus.DELIVERED
            )
        ) or 0
        read = self.db.scalar(
            select(func.count(MessageReceipt.id)).where(
                MessageReceipt.message_id == message_id, MessageReceipt.status == ReceiptStatus.READ
            )
        ) or 0
        return {"delivered_count": delivered, "read_count": read}
