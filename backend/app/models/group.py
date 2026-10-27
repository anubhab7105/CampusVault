"""groups + user_groups ("users belong to groups").

Groups anchor the chat and optional per-group resource scoping. A group can be
tied to a subject or a section (hierarchy-aware) or be free-form (club/team).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import func

from app.extensions import db
from app.models.base import BaseModel, SoftDeleteMixin, UUIDType


class Group(BaseModel, SoftDeleteMixin):
    __tablename__ = "groups"

    name = sa.Column(sa.String(120), nullable=False)
    description = sa.Column(sa.String(1000), nullable=True)
    group_type = sa.Column(sa.String(32), nullable=False, default="subject_group", index=True)

    owner_id = sa.Column(
        UUIDType,
        sa.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    subject_id = sa.Column(
        UUIDType,
        sa.ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    section_id = sa.Column(
        UUIDType,
        sa.ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_active = sa.Column(sa.Boolean, nullable=False, default=True, server_default=sa.text("true"))

    __table_args__ = (sa.Index("ix_groups_subject_created", "subject_id", "created_at"),)


class UserGroup(db.Model):
    __tablename__ = "user_groups"

    user_id = sa.Column(
        UUIDType,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    group_id = sa.Column(
        UUIDType,
        sa.ForeignKey("groups.id", ondelete="CASCADE"),
        primary_key=True,
    )
    joined_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=func.now())
    added_by = sa.Column(
        UUIDType,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    left_at = sa.Column(sa.DateTime(timezone=True), nullable=True)

    __table_args__ = (sa.Index("ix_user_groups_group", "group_id"),)
