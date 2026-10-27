"""RBAC persistence: roles, permissions, assignments."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from app.extensions import db
from app.models import Permission, Role, RolePermission, UserRole
from app.repositories.base_repository import BaseRepository


class RoleRepository(BaseRepository[Role]):
    model = Role

    def get_system_role_by_name(self, name: str) -> Role | None:
        stmt = sa.select(Role).where(Role.name == name, Role.is_system.is_(True))
        return db.session.scalar(stmt)

    def get_by_name(self, name: str) -> Role | None:
        stmt = sa.select(Role).where(Role.name == name)
        return db.session.scalar(stmt)

    def get_user_roles(self, user_id: uuid.UUID) -> Sequence[Role]:
        """Every role assigned to the user."""
        stmt = (
            sa.select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.name)
        )
        return db.session.scalars(stmt).all()

    def assign_role(self, user_id: uuid.UUID, role_id: uuid.UUID, assigned_by: uuid.UUID | None) -> UserRole:
        link = UserRole(user_id=user_id, role_id=role_id, assigned_by=assigned_by)
        db.session.add(link)
        return link

    def remove_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> int:
        stmt = sa.delete(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        result = db.session.execute(stmt)
        return int(result.rowcount or 0)


class PermissionRepository(BaseRepository[Permission]):
    model = Permission

    def get_by_code(self, code: str) -> Permission | None:
        stmt = sa.select(Permission).where(Permission.code == code)
        return db.session.scalar(stmt)

    def get_role_permission_codes(self, role_id: uuid.UUID) -> Sequence[str]:
        stmt = (
            sa.select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
        )
        return db.session.scalars(stmt).all()

    def get_role_permission_codes_bulk(self, role_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
        """Permission map for many roles in one round-trip."""
        if not role_ids:
            return {}
        stmt = (
            sa.select(RolePermission.role_id, Permission.code)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(RolePermission.role_id.in_(role_ids))
        )
        mapping: dict[uuid.UUID, list[str]] = {}
        for role_id, code in db.session.execute(stmt):
            mapping.setdefault(role_id, []).append(code)
        return mapping

    def grant_to_role(self, role_id: uuid.UUID, permission_id: uuid.UUID) -> RolePermission:
        link = RolePermission(role_id=role_id, permission_id=permission_id)
        db.session.add(link)
        return link

    def revoke_from_role(self, role_id: uuid.UUID, permission_id: uuid.UUID) -> int:
        stmt = sa.delete(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
        result = db.session.execute(stmt)
        return int(result.rowcount or 0)
