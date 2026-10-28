"""Group service — membership rules and hierarchy binding."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.errors.exceptions import ForbiddenError, NotFoundError
from app.extensions import db
from app.models import Group, UserGroup
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

    def can_manage_members(self, group_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Owner and moderators can manage members."""
        group = self.get_active_group(group_id)
        if group.owner_id == user_id:
            return True
        # Check if user is a moderator
        is_mod = self.groups.is_moderator(group_id, user_id)
        return is_mod

    def can_transfer_ownership(self, group_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Only the current owner can transfer ownership; any member can receive."""
        group = self.get_active_group(group_id)
        return group.owner_id == user_id

    def transfer_ownership(self, group_id: uuid.UUID, new_owner_id: uuid.UUID, current_owner_id: uuid.UUID) -> Group:
        """Transfer group ownership to a new user."""
        group = self.get_active_group(group_id)
        if group.owner_id != current_owner_id:
            raise ForbiddenError("Only the current owner can transfer ownership.")

        # Update the group owner
        group.owner_id = new_owner_id
        db.session.flush()

        # Update the conversation participant role
        conversation = self.conversations.get_by_group(group_id)
        if conversation is not None:
            participant = self.conversations.get_participant(conversation.id, new_owner_id)
            if participant is None:
                self.conversations.add_participant(conversation.id, new_owner_id, is_admin=True)
            else:
                participant.is_admin = True
                db.session.flush()

            # Remove old owner from admin status (keep as member)
            old_participant = self.conversations.get_participant(conversation.id, current_owner_id)
            if old_participant is not None:
                old_participant.is_admin = False
                db.session.flush()

        db.session.commit()
        return group

    def leave_group(self, group_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Remove a user from the group. Last owner cannot leave without transferring ownership."""
        group = self.get_active_group(group_id)

        # Check if this is the last owner
        if group.owner_id == user_id:
            # Check if there are other members besides the owner
            members = self.groups.list_members(group_id)
            other_members = [m for m in members if m.user_id != user_id]
            if not other_members:
                raise ForbiddenError(
                    "The last owner must transfer ownership before leaving. "
                    "Use transfer_ownership() first."
                )

        # Remove from group membership
        self.groups.remove_member(group_id, user_id)
        db.session.flush()

        # Remove from conversation participants
        conversation = self.conversations.get_by_group(group_id)
        if conversation is not None:
            self.conversations.remove_participant(conversation.id, user_id)

        db.session.commit()
        return True

    def add_member(
        self, group_id: uuid.UUID, new_member_id: uuid.UUID, added_by: uuid.UUID
    ) -> Group:
        """Invite a user to the group (owner-only). Updates both group + room membership."""
        group = self.get_active_group(group_id)
        if group.owner_id != added_by:
            raise ForbiddenError("Only the group owner can invite members.")

        # Add to user_groups table
        # Check if already a member
        if self.groups.is_member(group_id, new_member_id):
            raise ForbiddenError("User is already a member of this group.")

        membership = UserGroup(
            user_id=new_member_id,
            group_id=group.id,
            added_by=added_by,
        )
        db.session.add(membership)

        # Add to conversation participants
        conversation = self.conversations.get_by_group(group_id)
        if conversation is not None:
            # Ensure conversation has at least owner + new member as participants
            existing_participants = self.conversations.list_participants(conversation.id)
            if added_by not in existing_participants:
                self.conversations.add_participant(conversation.id, added_by, is_admin=True)
            self.conversations.add_participant(conversation.id, new_member_id)

        db.session.commit()
        return group

    def remove_member(self, group_id: uuid.UUID, user_id: uuid.UUID, removed_by: uuid.UUID) -> Group:
        """Remove a member from the group (owner or moderator). Cannot remove owner."""
        group = self.get_active_group(group_id)
        if group.owner_id == user_id:
            raise ForbiddenError("The group owner cannot be removed; transfer ownership first.")

        if not self.groups.is_moderator(group_id, removed_by) and group.owner_id != removed_by:
            raise ForbiddenError("Only moderators or the owner can remove members.")

        if group.owner_id == user_id:
            raise ForbiddenError("Cannot remove the group owner.")

        # Remove from user_groups table
        self.groups.db.session.query(UserGroup).filter(
            UserGroup.group_id == group.id,
            UserGroup.user_id == user_id,
        ).delete()

        # Remove from conversation participants
        conversation = self.conversations.get_by_group(group_id)
        if conversation is not None:
            self.conversations.remove_participant(conversation.id, user_id)

        db.session.commit()
        return group

group_service = GroupService()
