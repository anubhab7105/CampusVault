"""User persistence: lookups, role joins, admin listings."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from app.extensions import db
from app.models import Role, User, UserRole
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        email = email.strip().lower()
        stmt = sa.select(User).where(User.email == email, User.deleted_at.is_(None))
        return db.session.scalar(stmt)

    def get_by_google_sub(self, google_sub: str) -> User | None:
        stmt = sa.select(User).where(User.google_sub == google_sub, User.deleted_at.is_(None))
        return db.session.scalar(stmt)

    def get_user_role(self, user_id: uuid.UUID) -> Role | None:
        """Primary role for a user (first assigned)."""
        stmt = (
            sa.select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .order_by(UserRole.created_at)
            .limit(1)
        )
        return db.session.scalar(stmt)

    def get_by_domain(self, domain: str) -> list[User]:
        """Return all active users whose email ends with ``domain`` (Google auto-provision)."""
        stmt = sa.select(User).where(
            User.deleted_at.is_(None),
            User.email.like(f"%@{domain}"),
        )
        return db.session.scalars(stmt).all()

    def is_teacher_allowlisted(self, email: str) -> bool:
        """Check whether ``email`` is on the teacher allowlist."""
        from app.models import TeacherAllowlist

        stmt = sa.select(TeacherAllowlist).where(
            TeacherAllowlist.email == email.strip().lower(),
            TeacherAllowlist.is_approved.is_(True),
        )
        allowlist_entry = db.session.scalar(stmt)
        return allowlist_entry is not None and allowlist_entry.is_approved

    def can_deactivate(self, user_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> bool:
        """Return False if deactivating this user would violate last-admin protection."""
        from app.models import Role, UserRole

        # Cannot deactivate self via actor check if actor is the same user
        if actor_id and user_id == actor_id:
            return False

        # Count admins
        admin_count = (
            db.session.query(UserRole)
            .join(Role, UserRole.role_id == Role.id)
            .filter(UserRole.user_id == user_id, Role.name == "Admin")
            .count()
        )
        # Count total admins in system
        total_admins = (
            db.session.query(UserRole)
            .join(Role, UserRole.role_id == Role.id)
            .filter(Role.name == "Admin")
            .count()
        )
        # If this user is an admin and they are the last one, block deactivation
        if admin_count > 0 and total_admins == 1 and admin_count == 1:
            return False
        return True

    def set_active(self, user_id: uuid.UUID, active: bool = True) -> User:
        """Set ``is_active`` on a user and emit audit event."""
        user = self.get(user_id)
        if user is None:
            return None
        user.is_active = active
        db.session.add(user)
        return user

    def search(self, query: str | None, page: int, page_size: int) -> tuple[Sequence[User], int]:
        conditions = [User.deleted_at.is_(None)]
        if query:
            conditions.append(User.full_name.ilike(f"%{query}%"))
        return self.paginate(page, page_size, *conditions, order_by=User.created_at.desc())
