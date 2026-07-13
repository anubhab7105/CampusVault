"""
RBAC domain service. Implements the service logic specified in
API_SPEC_RBAC.md, including audit logging for role/permission changes
(06_SECURITY_GUIDE.md names "admin actions" as an explicit audit category).
"""
import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.repositories.auth_repository import AuthRepository
from app.repositories.rbac_repository import RBACRepository
from app.utils.exceptions import ConflictError, NotFoundError, ValidationError


class RBACService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RBACRepository(db)
        self.auth_repo = AuthRepository(db)

    # ---------- Roles ----------

    def list_roles(self) -> list[dict]:
        roles = self.repo.list_roles()
        return [self._role_with_permissions(r) for r in roles]

    def _role_with_permissions(self, role) -> dict:
        return {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "permissions": self.repo.get_permission_codes_for_role(role.id),
        }

    def create_role(self, name: str, description: str | None) -> dict:
        if self.repo.get_role_by_name(name) is not None:
            raise ConflictError("Role name already taken.", code="ROLE_NAME_TAKEN")
        role = self.repo.create_role(name, description)
        self.db.commit()
        return self._role_with_permissions(role)

    def update_role(self, role_id: uuid.UUID, name: str | None, description: str | None) -> dict:
        role = self.repo.get_role_by_id(role_id)
        if role is None:
            raise NotFoundError("Role not found.", code="ROLE_NOT_FOUND")
        role = self.repo.update_role(role, name, description)
        self.db.commit()
        return self._role_with_permissions(role)

    def delete_role(self, role_id: uuid.UUID) -> None:
        role = self.repo.get_role_by_id(role_id)
        if role is None:
            raise NotFoundError("Role not found.", code="ROLE_NOT_FOUND")
        if self.repo.role_in_use(role_id):
            raise ConflictError("Role is assigned to one or more users.", code="ROLE_IN_USE")
        self.repo.delete_role(role)
        self.db.commit()

    # ---------- Permissions ----------

    def list_permissions(self) -> list[dict]:
        perms = self.repo.list_permissions()
        return [{"id": p.id, "code": p.code, "description": p.description} for p in perms]

    def replace_role_permissions(self, role_id: uuid.UUID, permission_codes: list[str], actor_user_id: uuid.UUID) -> dict:
        role = self.repo.get_role_by_id(role_id)
        if role is None:
            raise NotFoundError("Role not found.", code="ROLE_NOT_FOUND")

        before = self.repo.get_permission_codes_for_role(role_id)

        found = self.repo.get_permissions_by_codes(permission_codes)
        found_codes = {p.code for p in found}
        unknown = set(permission_codes) - found_codes
        if unknown:
            raise ValidationError(
                f"Unknown permission code(s): {', '.join(sorted(unknown))}", code="UNKNOWN_PERMISSION_CODE"
            )

        self.repo.replace_role_permissions(role_id, [p.id for p in found])

        self.db.add(AuditLog(
            user_id=actor_user_id,
            action="role.permissions_updated",
            entity_type="role",
            entity_id=role_id,
            audit_metadata={"before": sorted(before), "after": sorted(permission_codes)},
        ))
        self.db.commit()
        return self._role_with_permissions(role)

    # ---------- User <-> Role ----------

    def get_user_roles(self, user_id: uuid.UUID) -> list[str]:
        return self.repo.get_role_names_for_user(user_id)

    def replace_user_roles(self, user_id: uuid.UUID, role_names: list[str], actor_user_id: uuid.UUID) -> list[str]:
        user = self.auth_repo.get_user_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")

        before = self.repo.get_role_names_for_user(user_id)

        found_roles = self.repo.get_role_ids_by_names(role_names)
        found_names = {r.name for r in found_roles}
        unknown = set(role_names) - found_names
        if unknown:
            raise ValidationError(f"Unknown role name(s): {', '.join(sorted(unknown))}", code="UNKNOWN_ROLE_NAME")

        self.repo.replace_user_roles(user_id, [r.id for r in found_roles])

        self.db.add(AuditLog(
            user_id=actor_user_id,
            action="role.assign",
            entity_type="user",
            entity_id=user_id,
            audit_metadata={"before": sorted(before), "after": sorted(role_names)},
        ))
        self.db.commit()
        return self.repo.get_role_names_for_user(user_id)

    # ---------- Permission resolution (used by middleware) ----------

    def user_has_permission(self, user_id: uuid.UUID, permission_code: str) -> bool:
        return permission_code in self.repo.get_permission_codes_for_user(user_id)
