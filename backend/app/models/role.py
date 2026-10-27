"""roles + permissions + role_permissions (RBAC foundation).

Roles and permissions are data, not code: admins can create custom roles and
grant arbitrary permission sets (extensibility requirement).
"""

from __future__ import annotations

import sqlalchemy as sa

from app.extensions import db
from app.models.base import BaseModel


class Role(BaseModel):
    __tablename__ = "roles"

    name = sa.Column(sa.String(64), nullable=False, unique=True, index=True)
    description = sa.Column(sa.String(255), nullable=True)
    # System roles cannot be deleted from the admin UI.
    is_system = sa.Column(
        sa.Boolean, nullable=False, default=False, server_default=sa.text("false")
    )

    permissions = db.relationship(
        "Permission",
        secondary="role_permissions",
        viewonly=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Role name={self.name!r}>"


class Permission(BaseModel):
    __tablename__ = "permissions"

    # ``module:action``, e.g. ``library:resource:create``.
    code = sa.Column(sa.String(64), nullable=False, unique=True, index=True)
    module = sa.Column(sa.String(64), nullable=False, index=True)
    description = sa.Column(sa.String(255), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Permission code={self.code!r}>"


class RolePermission(db.Model):
    __tablename__ = "role_permissions"

    role_id = sa.Column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id = sa.Column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    __table_args__ = (
        sa.Index("ix_role_permissions_permission_id", "permission_id"),
    )
