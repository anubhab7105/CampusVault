"""Group service — membership rules and hierarchy binding."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.errors.exceptions import ForbiddenError, NotFoundError
from app.extensions import db
from app.models import Group
from app.repositories import ConversationRepository, GroupRepository
from app.services.base_service import BaseService


class GroupService(BaseService):
    def __init__(self) -> None:
        self.groups = GroupRepository()
        self.conversations = ConversationRepository()

    def create_group(
        self,
        *,
        owner_id: uuid.UUID,
        name: str,
        description: str = "",
        group_type: str = "subject_group",
        subject_id: uuid.UUID | None = None,
        section_id: uuid.UUID | None = None,
    ) -> Group:
        """Create the group AND its mirrored chat conversation in one commit."""
        group = self.groups.create(
            owner_id=owner_id,
            name=name,
            description=description,
            group_type=group_type,
            subject_id=subject_id,
            section_id=section_id,
        )
        conversation = self.conversations.create(
            conversation_type="group",
            group_id=group.id,
            created_by=owner_id,
        )
        self.conversations.add_participant(conversation.id, owner_id, is_admin=True)
        self.groups.add_member(group.id, owner_id, added_by=owner_id)
        db.session.commit()
        return group

    def get_active_group(self, group_id: uuid.UUID) -> Group:
        group = self.groups.get_active_by_id(group_id)
        if group is None:
            raise NotFoundError("Group not found.")
        return group

    def assert_membership(self, group_id: uuid.UUID, user_id: uuid.UUID) -> None:
        if not self.groups.is_member(group_id, user_id):
            raise ForbiddenError("You are not a member of this group.")

    def list_for_user(self, user_id: uuid.UUID) -> Sequence[Group]:
        return self.groups.list_for_user(user_id)


group_service = GroupService()
