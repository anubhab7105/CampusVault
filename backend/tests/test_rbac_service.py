"""Integration tests for RBACService — real Postgres, covers logic the repository doesn't."""
import pytest

from app.models.audit import AuditLog
from app.models.auth import UserType
from app.models.rbac import Permission
from app.repositories.auth_repository import AuthRepository
from app.services.rbac_service import RBACService
from app.utils.exceptions import ConflictError, NotFoundError, ValidationError


class TestRoleService:
    def test_create_role_success(self, db):
        service = RBACService(db)
        role = service.create_role("moderator", "Content moderator")
        assert role["name"] == "moderator"
        assert role["permissions"] == []

    def test_create_role_duplicate_name_rejected(self, db):
        service = RBACService(db)
        service.create_role("dup-role", None)
        with pytest.raises(ConflictError) as exc_info:
            service.create_role("dup-role", None)
        assert exc_info.value.code == "ROLE_NAME_TAKEN"

    def test_update_nonexistent_role_raises_not_found(self, db):
        import uuid
        service = RBACService(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.update_role(uuid.uuid4(), "x", None)
        assert exc_info.value.code == "ROLE_NOT_FOUND"

    def test_delete_role_in_use_is_blocked(self, db):
        service = RBACService(db)
        auth_repo = AuthRepository(db)

        role = service.create_role("blocked-role", None)
        user = auth_repo.create_user("blocked@college.edu", "U", UserType.STUDENT)
        db.flush()
        service.replace_user_roles(user.id, ["blocked-role"], actor_user_id=user.id)

        with pytest.raises(ConflictError) as exc_info:
            service.delete_role(role["id"])
        assert exc_info.value.code == "ROLE_IN_USE"

    def test_delete_unused_role_succeeds(self, db):
        service = RBACService(db)
        role = service.create_role("removable-role", None)
        service.delete_role(role["id"])  # should not raise


class TestRolePermissionsService:
    def test_replace_role_permissions_writes_audit_log(self, db):
        service = RBACService(db)
        auth_repo = AuthRepository(db)
        actor = auth_repo.create_user("actor1@college.edu", "Actor", UserType.ADMIN)
        db.commit()

        role = service.create_role("perm-role", None)
        perm = Permission(code="resource:upload", description="")
        db.add(perm)
        db.commit()

        result = service.replace_role_permissions(role["id"], ["resource:upload"], actor_user_id=actor.id)
        assert result["permissions"] == ["resource:upload"]

        log = db.query(AuditLog).filter_by(action="role.permissions_updated", entity_id=role["id"]).one()
        assert log.audit_metadata["before"] == []
        assert log.audit_metadata["after"] == ["resource:upload"]
        assert log.user_id == actor.id

    def test_replace_role_permissions_unknown_code_rejected(self, db):
        service = RBACService(db)
        auth_repo = AuthRepository(db)
        actor = auth_repo.create_user("actor2@college.edu", "Actor", UserType.ADMIN)
        db.commit()
        role = service.create_role("perm-role-2", None)

        with pytest.raises(ValidationError) as exc_info:
            service.replace_role_permissions(role["id"], ["totally:fake"], actor_user_id=actor.id)
        assert exc_info.value.code == "UNKNOWN_PERMISSION_CODE"


class TestUserRolesService:
    def test_replace_user_roles_writes_audit_log(self, db):
        service = RBACService(db)
        auth_repo = AuthRepository(db)

        user = auth_repo.create_user("audit-target@college.edu", "U", UserType.STUDENT)
        db.flush()
        service.create_role("audited-role", None)
        db.commit()

        roles = service.replace_user_roles(user.id, ["audited-role"], actor_user_id=user.id)
        assert roles == ["audited-role"]

        log = db.query(AuditLog).filter_by(action="role.assign", entity_id=user.id).one()
        assert log.audit_metadata["after"] == ["audited-role"]

    def test_replace_user_roles_unknown_user_raises(self, db):
        import uuid
        service = RBACService(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.replace_user_roles(uuid.uuid4(), [], actor_user_id=uuid.uuid4())
        assert exc_info.value.code == "USER_NOT_FOUND"

    def test_replace_user_roles_unknown_role_name_rejected(self, db):
        service = RBACService(db)
        auth_repo = AuthRepository(db)
        user = auth_repo.create_user("bad-role-target@college.edu", "U", UserType.STUDENT)
        db.commit()

        with pytest.raises(ValidationError) as exc_info:
            service.replace_user_roles(user.id, ["nonexistent-role"], actor_user_id=user.id)
        assert exc_info.value.code == "UNKNOWN_ROLE_NAME"


class TestPermissionResolution:
    def test_user_has_permission_true_and_false(self, db):
        service = RBACService(db)
        auth_repo = AuthRepository(db)

        user = auth_repo.create_user("perm-check@college.edu", "U", UserType.STUDENT)
        db.commit()
        role = service.create_role("checker-role", None)
        perm = Permission(code="chat:manage", description="")
        db.add(perm)
        db.commit()

        service.replace_role_permissions(role["id"], ["chat:manage"], actor_user_id=user.id)
        service.replace_user_roles(user.id, ["checker-role"], actor_user_id=user.id)

        assert service.user_has_permission(user.id, "chat:manage") is True
        assert service.user_has_permission(user.id, "rbac:manage") is False
