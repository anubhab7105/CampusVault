"""users + user_roles.

Soft delete: yes (account deactivation keeps FKs and audit history intact).
Associations are traversed through their tables; no cross-domain ORM
relationships beyond what repositories need, to avoid import cycles.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import func

from app.constants import AUTH_PROVIDER_OTP
from app.extensions import db
from app.models.base import BaseModel, SoftDeleteMixin, UUIDType


class User(BaseModel, SoftDeleteMixin):
    __tablename__ = "users"

    email = sa.Column(sa.String(255), nullable=False, unique=True, index=True)
    full_name = sa.Column(sa.String(120), nullable=False)
    avatar_url = sa.Column(sa.String(512), nullable=True)

    auth_provider = sa.Column(sa.String(20), nullable=False, default=AUTH_PROVIDER_OTP)
    google_sub = sa.Column(sa.String(64), nullable=True, unique=True, index=True)
    email_verified_at = sa.Column(sa.DateTime(timezone=True), nullable=True)

    department_id = sa.Column(
        UUIDType,
        sa.ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_active = sa.Column(sa.Boolean, nullable=False, default=True, server_default=sa.text("true"))
    last_login_at = sa.Column(sa.DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<User id={self.id} email={self.email!r}>"


class UserRole(db.Model):
    """Association: user ↔ role, with assignment audit trail."""

    __tablename__ = "user_roles"

    user_id = sa.Column(
        UUIDType,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id = sa.Column(
        UUIDType,
        sa.ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    assigned_by = sa.Column(
        UUIDType,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = sa.Column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    role = db.relationship("Role", viewonly=True)

    __table_args__ = (sa.Index("ix_user_roles_role_id", "role_id"),)
