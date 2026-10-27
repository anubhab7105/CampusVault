"""Admin service — user/role administration and platform stats."""

from __future__ import annotations

import uuid

from app.errors.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.extensions import db
from app.models import User
from app.repositories import UserRepository
from app.services.base_service import BaseService


class AdminService(BaseService):
    """Self-guarding admin-only flows: callers must hold admin role."""

    def __init__(self) -> None:
        self.users = UserRepository()

    @staticmethod
    def assert_admin(is_admin_claim: bool) -> None:
        if not is_admin_claim:
            raise ForbiddenError("Admin access required.")

    def list_users(self, *, query: str | None, page: int, page_size: int):
        return self.users.search(query, page, page_size)

    def deactivate_user(self, *, target_user_id: uuid.UUID, acting_admin_id: uuid.UUID) -> User:
        if target_user_id == str(acting_admin_id):
            raise ConflictError("Admins cannot deactivate themselves.")
        user = self.users.get_active_by_id(target_user_id)
        if user is None:
            raise NotFoundError("User not found.")
        self.users.soft_delete(user)
        db.session.commit()
        return user

    def platform_stats(self) -> dict:
        from app.models import Resource

        user_count = self.users.count()
        resource_stmt = db.select(db.func.count()).select_from(Resource.__table__)
        resource_count = int(db.session.scalar(resource_stmt) or 0)
        return {"users": user_count, "resources": resource_count}


admin_service = AdminService()
