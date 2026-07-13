"""Integration tests for RBACRepository — real Postgres."""
from app.models.auth import UserType
from app.models.rbac import Permission
from app.repositories.auth_repository import AuthRepository
from app.repositories.rbac_repository import RBACRepository


class TestRoleCRUD:
    def test_create_and_get_role(self, db):
        repo = RBACRepository(db)
        role = repo.create_role("teacher", "Teaching staff")
        db.flush()

        fetched = repo.get_role_by_id(role.id)
        assert fetched is not None
        assert fetched.name == "teacher"

    def test_get_role_by_name(self, db):
        repo = RBACRepository(db)
        repo.create_role("librarian", None)
        db.flush()

        assert repo.get_role_by_name("librarian") is not None
        assert repo.get_role_by_name("does-not-exist") is None

    def test_update_role(self, db):
        repo = RBACRepository(db)
        role = repo.create_role("staff", "old desc")
        db.flush()

        updated = repo.update_role(role, name=None, description="new desc")
        assert updated.name == "staff"  # unchanged
        assert updated.description == "new desc"

    def test_delete_role(self, db):
        repo = RBACRepository(db)
        role = repo.create_role("temp-role", None)
        db.flush()
        role_id = role.id

        repo.delete_role(role)
        db.flush()
        assert repo.get_role_by_id(role_id) is None

    def test_role_in_use_true_when_assigned(self, db):
        auth_repo = AuthRepository(db)
        repo = RBACRepository(db)

        user = auth_repo.create_user("u1@college.edu", "U1", UserType.STUDENT)
        role = repo.create_role("in-use-role", None)
        db.flush()

        repo.replace_user_roles(user.id, [role.id])
        db.flush()

        assert repo.role_in_use(role.id) is True

    def test_role_in_use_false_when_unassigned(self, db):
        repo = RBACRepository(db)
        role = repo.create_role("unused-role", None)
        db.flush()
        assert repo.role_in_use(role.id) is False


class TestRolePermissions:
    def test_replace_role_permissions_and_read_back(self, db):
        repo = RBACRepository(db)
        role = repo.create_role("editor", None)
        p1 = Permission(code="resource:upload", description="Upload resources")
        p2 = Permission(code="resource:delete", description="Delete resources")
        db.add_all([p1, p2])
        db.flush()

        repo.replace_role_permissions(role.id, [p1.id, p2.id])
        db.flush()

        codes = set(repo.get_permission_codes_for_role(role.id))
        assert codes == {"resource:upload", "resource:delete"}

    def test_replace_role_permissions_is_idempotent_full_replace(self, db):
        repo = RBACRepository(db)
        role = repo.create_role("reviewer", None)
        p1 = Permission(code="a:x", description="")
        p2 = Permission(code="a:y", description="")
        db.add_all([p1, p2])
        db.flush()

        repo.replace_role_permissions(role.id, [p1.id, p2.id])
        db.flush()
        # Replace again with only p1 — p2 should be removed, not accumulated.
        repo.replace_role_permissions(role.id, [p1.id])
        db.flush()

        codes = set(repo.get_permission_codes_for_role(role.id))
        assert codes == {"a:x"}

    def test_get_permissions_by_codes_filters_unknown(self, db):
        repo = RBACRepository(db)
        p1 = Permission(code="known:code", description="")
        db.add(p1)
        db.flush()

        found = repo.get_permissions_by_codes(["known:code", "totally:unknown"])
        assert len(found) == 1
        assert found[0].code == "known:code"


class TestUserRoles:
    def test_replace_user_roles_and_read_back(self, db):
        auth_repo = AuthRepository(db)
        repo = RBACRepository(db)

        user = auth_repo.create_user("u2@college.edu", "U2", UserType.STUDENT)
        r1 = repo.create_role("role-a", None)
        r2 = repo.create_role("role-b", None)
        db.flush()

        repo.replace_user_roles(user.id, [r1.id, r2.id])
        db.flush()

        names = set(repo.get_role_names_for_user(user.id))
        assert names == {"role-a", "role-b"}

    def test_get_permission_codes_for_user_resolves_through_roles(self, db):
        """The core RBAC resolution the middleware depends on: user -> roles -> permissions."""
        auth_repo = AuthRepository(db)
        repo = RBACRepository(db)

        user = auth_repo.create_user("u3@college.edu", "U3", UserType.STUDENT)
        role = repo.create_role("uploader", None)
        perm = Permission(code="resource:upload", description="")
        db.add(perm)
        db.flush()

        repo.replace_role_permissions(role.id, [perm.id])
        repo.replace_user_roles(user.id, [role.id])
        db.flush()

        effective = repo.get_permission_codes_for_user(user.id)
        assert effective == {"resource:upload"}

    def test_user_with_no_roles_has_no_permissions(self, db):
        auth_repo = AuthRepository(db)
        repo = RBACRepository(db)
        user = auth_repo.create_user("u4@college.edu", "U4", UserType.STUDENT)
        db.flush()

        assert repo.get_permission_codes_for_user(user.id) == set()
