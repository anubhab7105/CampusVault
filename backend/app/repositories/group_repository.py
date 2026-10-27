"""Group persistence: membership + hierarchy-bound groups."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from app.extensions import db
from app.models import Group, UserGroup
from app.repositories.base_repository import BaseRepository


class GroupRepository(BaseRepository[Group]):
    model = Group

    def is_member(self, group_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = (
            sa.select(UserGroup.group_id)
            .where(UserGroup.group_id == group_id, UserGroup.user_id == user_id)
            .limit(1)
        )
        return db.session.scalar(stmt) is not None

    def add_member(
        self, group_id: uuid.UUID, user_id: uuid.UUID, added_by: uuid.UUID | None
    ) -> UserGroup:
        link = UserGroup(group_id=group_id, user_id=user_id, added_by=added_by)
        db.session.add(link)
        return link

    def remove_member(self, group_id: uuid.UUID, user_id: uuid.UUID) -> int:
        stmt = sa.delete(UserGroup).where(
            UserGroup.group_id == group_id, UserGroup.user_id == user_id
        )
        result = db.session.execute(stmt)
        return int(result.rowcount or 0)

    def list_for_user(self, user_id: uuid.UUID) -> Sequence[Group]:
        stmt = (
            sa.select(Group)
            .join(UserGroup, UserGroup.group_id == Group.id)
            .where(UserGroup.user_id == user_id, UserGroup.deleted_at.is_(None))
            .order_by(Group.name)
        )
        return db.session.scalars(stmt).all()

    def list_group_members(self, group_id: uuid.UUID) -> Sequence[uuid.UUID]:
        stmt = sa.select(UserGroup.user_id).where(UserGroup.group_id == group_id)
        return list(db.session.scalars(stmt))
