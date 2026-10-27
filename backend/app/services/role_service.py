"""RBAC service: role assignment and effective permission resolution."""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from app.constants import ROLE_ADMIN, SYSTEM_ROLES
from app.extensions import db
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
            from app.models import Permission

            all_codes = db.session.scalars(sa.select(Permission.code)).all()
            codes |= set(all_codes)
        return role.name, sorted(codes)

    def ensure_system_roles_exist(self) -> None:
        """Idempotent seed of Student/Teacher/Admin + base permissions."""
        from app.models import Permission as PermissionModel

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


role_service = RoleService()
