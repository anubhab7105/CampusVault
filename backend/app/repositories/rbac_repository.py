"""
RBAC repository. Per 04_BACKEND_GUIDE.md: "Database access goes through
repositories." Covers roles, permissions, role_permissions, and user_roles
per API_SPEC_RBAC.md.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.rbac import Permission, Role, RolePermission, UserRole


class RBACRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------- Roles ----------

    def list_roles(self) -> list[Role]:
        return list(self.db.scalars(select(Role).order_by(Role.name)))

    def get_role_by_id(self, role_id: uuid.UUID) -> Role | None:
        return self.db.scalar(select(Role).where(Role.id == role_id))

    def get_role_by_name(self, name: str) -> Role | None:
        return self.db.scalar(select(Role).where(Role.name == name))

    def create_role(self, name: str, description: str | None) -> Role:
        role = Role(name=name, description=description)
        self.db.add(role)
        self.db.flush()
        return role

    def update_role(self, role: Role, name: str | None, description: str | None) -> Role:
        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        self.db.flush()
        return role

    def delete_role(self, role: Role) -> None:
        self.db.delete(role)
        self.db.flush()

    def role_in_use(self, role_id: uuid.UUID) -> bool:
        return self.db.scalar(select(UserRole).where(UserRole.role_id == role_id)) is not None

    # ---------- Permissions ----------

    def list_permissions(self) -> list[Permission]:
        return list(self.db.scalars(select(Permission).order_by(Permission.code)))

    def get_permissions_by_codes(self, codes: list[str]) -> list[Permission]:
        return list(self.db.scalars(select(Permission).where(Permission.code.in_(codes))))

    # ---------- Role <-> Permission ----------

    def get_permission_codes_for_role(self, role_id: uuid.UUID) -> list[str]:
        rows = self.db.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
        )
        return list(rows)

    def replace_role_permissions(self, role_id: uuid.UUID, permission_ids: list[uuid.UUID]) -> None:
        self.db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
        for pid in permission_ids:
            self.db.add(RolePermission(role_id=role_id, permission_id=pid))
        self.db.flush()

    # ---------- User <-> Role ----------

    def get_role_names_for_user(self, user_id: uuid.UUID) -> list[str]:
        rows = self.db.scalars(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return list(rows)

    def get_permission_codes_for_user(self, user_id: uuid.UUID) -> set[str]:
        """
        Resolves a user's full effective permission set: user -> roles -> permissions.
        This is the real lookup the auth middleware's require_permission TODO pointed to.
        """
        rows = self.db.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user_id)
        )
        return set(rows)

    def get_role_ids_by_names(self, names: list[str]) -> list[Role]:
        return list(self.db.scalars(select(Role).where(Role.name.in_(names))))

    def replace_user_roles(self, user_id: uuid.UUID, role_ids: list[uuid.UUID]) -> None:
        self.db.execute(delete(UserRole).where(UserRole.user_id == user_id))
        now = datetime.now(timezone.utc)
        for rid in role_ids:
            self.db.add(UserRole(user_id=user_id, role_id=rid, assigned_at=now))
        self.db.flush()
