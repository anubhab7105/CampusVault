"""RBAC service: role assignment and effective permission resolution."""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from app.constants import ROLE_ADMIN, SYSTEM_ROLES
from app.extensions import db
from app.models import Role, Permission, UserRole
from app.repositories import PermissionRepository, RoleRepository, UserRepository


class RoleService:
    """Business rules for roles/permissions (data-not-code RBAC)."""

    def __init__(self) -> None:
        self.roles = RoleRepository()
        self.permissions = PermissionRepository()
        self.users = UserRepository()

    # --- lookups ------------------------------------------------------------ #

    def load_user_role_bundle(self, user_id: uuid.UUID) -> tuple[str, list[str]]:
        """(role_name, [permission codes]) for JWT claims."""
        roles = self.roles.get_user_roles(user_id)
        if not roles:
            return "", []
        role = roles[0]
        codes = set(self.permissions.get_role_permission_codes(role.id))
        if role.name == ROLE_ADMIN:
            # Admin is the emergency override: every permission is implied.
            from app.models import Permission as _Permission
            from app.extensions import db as _db

            all_codes = _db.session.scalars(
                sa.select(_Permission.code)
            ).all()
            codes |= set(all_codes)
        return role.name, sorted(codes)

    def ensure_system_roles_exist(self) -> None:
        """Idempotent seed of Student/Teacher/Admin + base permissions."""

        for name in SYSTEM_ROLES:
            if self.roles.get_system_role_by_name(name) is None:
                self.roles.create(name=name, description=name, is_system=True)
        seed_codes = {
            "chat:group:join",
            "chat:message:send",
            "library:resource:read",
            "library:resource:create",
            "library:file:upload",
            "admin:dashboard:view",
            "admin:roles:manage",
            "admin:users:manage",
            "admin:audit:read",
        }
        for module_action in sorted(seed_codes):
            module, action = module_action.split(":", 1)
            if self.permissions.get_by_code(module_action) is None:
                self.permissions.create(
                    code=module_action, module=module, description=f"Allow {action} in {module}"
                )
        db.session.commit()

    # --- role / permission CRUD (admin only) -------------------------------- #

    def grant_permissions_to_role(self, role_id: uuid.UUID, permission_codes: list[str]) -> int:
        """Replace the role's permission set with the given codes (idempotent)."""
        granted = self.permissions.grant_permissions(role_id, permission_codes)
        db.session.commit()
        return granted

    def revoke_permissions_from_role(self, role_id: uuid.UUID, permission_codes: list[str]) -> int:
        """Remove specific permission grants from a role."""
        revoked = self.permissions.revoke_permissions(role_id, permission_codes)
        db.session.commit()
        return revoked

    def assign_role_to_user(
        self, user_id: uuid.UUID, role_id: uuid.UUID, assigned_by: uuid.UUID
    ) -> bool:
        """Assign a role to a user (admin only)."""
        from app.repositories import UserRepository

        ur = UserRepository().create(user_id=user_id, role_id=role_id, assigned_by=assigned_by)
        db.session.commit()
        return ur is not None

    def revoke_role_from_user(self, user_id: uuid.UUID, role_id: uuid.UUID) -> int:
        """Revoke a role from a user (admin only)."""
        from app.repositories import UserRepository

        count = UserRepository().remove_role(user_id, role_id)
        db.session.commit()
        return count

    def get_user_effective_permissions(self, user_id: uuid.UUID) -> list[str]:
        """Return the effective permission codes for a user (convenience wrapper)."""
        _, codes = self.load_user_role_bundle(user_id)
        return codes


role_service = RoleService()
