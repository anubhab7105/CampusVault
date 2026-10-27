"""Admin service — user/role administration, academic CRUD, platform stats, moderation queue."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from app.errors.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.extensions import db
from app.models import User, Department, Program, Semester, Section, Subject, Group, Resource, FileRecord, AuditLog, Notification, TeacherAllowlist
from app.repositories import UserRepository, DepartmentRepository, ProgramRepository, SemesterRepository, SectionRepository, SubjectRepository, GroupRepository, ResourceRepository, AuditLogRepository, NotificationRepository, TeacherAllowlistRepository
from app.services.base_service import BaseService


class AdminService(BaseService):
    """Self-guarding admin-only flows: callers must hold admin role."""

    def __init__(self) -> None:
        self.users = UserRepository()
        self.departments = DepartmentRepository()
        self.programs = ProgramRepository()
        self.semesters = SemesterRepository()
        self.sections = SectionRepository()
        self.subjects = SubjectRepository()
        self.groups = GroupRepository()
        self.resources = ResourceRepository()
        self.audit_logs = AuditLogRepository()
        self.notifications = NotificationRepository()
        self.teacher_allowlist = TeacherAllowlistRepository()

    # ---- Admin gate ------------------------------------------------------- #

    @staticmethod
    def assert_admin(is_admin_claim: bool) -> None:
        if not is_admin_claim:
            raise ForbiddenError("Admin access required.")

    # ---- Platform stats --------------------------------------------------- #

    def platform_stats(self) -> dict:
        """Return aggregated stats for the admin dashboard overview."""
        now = datetime.now(timezone.utc)
        seven_ago = now - timedelta(days=7)
        thirty_ago = now - timedelta(days=30)

        # Total users by role
        user_count_by_role = {}
        for role_name in ("Student", "Teacher", "Admin"):
            count = self.users.count_by_role(role_name)
            user_count_by_role[role_name] = count

        # Active users (7/30 days)
        active_7d = self.users.count_active_between(seven_ago, now)
        active_30d = self.users.count_active_between(thirty_ago, now)

        # Resources by type and department - use simple count queries
        resource_type_stmt = (
            db.select(Resource.resource_type, db.func.count(Resource.id))
            .group_by(Resource.resource_type)
        )
        resource_type_rows = db.session.execute(resource_type_stmt).all()
        resources_by_type = {str(r.resource_type): r.count for r in resource_type_rows}

        resource_dept_stmt = (
            db.select(Resource.department_id, db.func.count(Resource.id))
            .group_by(Resource.department_id)
        )
        resource_dept_rows = db.session.execute(resource_dept_stmt).all()
        resources_by_dept = {str(r.department_id): r.count for r in resource_dept_rows if r.department_id}

        # Storage used: total file sizes
        from app.models import FileRecord
        storage_stmt = db.select(db.func.sum(FileRecord.file_size)).select_from(FileRecord)
        storage_total_bytes = int(db.session.scalar(storage_stmt) or 0)

        # Uploads and downloads over time (daily counts last 30 days) - use raw count from resource created_at
        daily_stmt = (
            db.select(
                db.func.date_trunc("day", Resource.created_at).label("day"),
                db.func.count(Resource.id).label("created"),
            )
            .select_from(Resource)
            .where(Resource.created_at >= now - timedelta(days=30))
            .group_by(db.func.date_trunc("day", Resource.created_at))
            .order_by(db.func.date_trunc("day", Resource.created_at))
        )
        daily_rows = db.session.execute(daily_stmt).all()
        uploads_over_time = {}
        downloads_over_time = {}
        for r in daily_rows:
            day_str = str(r.day)
            uploads_over_time[day_str] = r.created or 0
            # downloads would need a separate counter; use download_count sum per day if available

        # Scan outcomes (clean/infected/failed)
        scan_stmt = db.select(FileRecord.scan_status, db.func.count(FileRecord.id)).select_from(FileRecord).group_by(FileRecord.scan_status)
        scan_rows = db.session.execute(scan_stmt).all()
        scan_outcomes = {}
        for r in scan_rows:
            scan_outcomes[str(r.scan_status)] = r.count

        # Chat activity: messages per day, active groups
        msg_stmt = (
            db.select(db.func.date_trunc("day", Message.created_at).label("day"), db.func.count(Message.id).label("messages"))
            .select_from(Message)
            .where(Message.created_at >= now - timedelta(days=30))
            .group_by(db.func.date_trunc("day", Message.created_at))
            .order_by(db.func.date_trunc("day", Message.created_at))
        )
        msg_rows = db.session.execute(msg_stmt).all()
        messages_per_day = {}
        for r in msg_rows:
            messages_per_day[str(r.day)] = r.messages or 0

        try:
            active_groups = self.groups.count_active()
        except Exception:
            active_groups = 0

        # Pending items needing attention
        # Stuck scans: pending/scanning > 30 min
        stale_threshold = now - timedelta(minutes=30)
        stuck_stmt = db.select(db.func.count(FileRecord.id)).select_from(FileRecord).where(FileRecord.scan_status.in_(["pending", "scanning"])).where(FileRecord.created_at < stale_threshold)
        stuck_count = int(db.session.scalar(stuck_stmt) or 0)

        # Failed email deliveries: notifications older than 24h still unread
        failed_threshold = now - timedelta(hours=24)
        failed_stmt = db.select(db.func.count(Notification.id)).select_from(Notification).where(Notification.is_read.is_(False)).where(Notification.created_at < failed_threshold)
        failed_email_count = int(db.session.scalar(failed_stmt) or 0)

        return {
            "users": {
                "total_by_role": user_count_by_role,
                "active_7d": active_7d,
                "active_30d": active_30d,
            },
            "resources": {
                "by_type": resources_by_type,
                "by_department": resources_by_dept,
                "storage_used_bytes": storage_total_bytes,
                "uploads_over_time": uploads_over_time,
                "downloads_over_time": downloads_over_time,
            },
            "scans": scan_outcomes,
            "chat": {
                "messages_per_day": messages_per_day,
                "active_groups": active_groups,
            },
            "pending": {
                "stuck_scans": stuck_count,
                "failed_email_deliveries": failed_email_count,
            },
        }

    # ---- Management: Users ------------------------------------------------ #

    def list_users(self, *, query: str | None, page: int, page_size: int):
        """Search users by role/filter with keyset pagination."""
        return self.users.search(query, page, page_size)

    def deactivate_user(self, *, target_user_id: uuid.UUID, acting_admin_id: uuid.UUID) -> User:
        """Soft-deactivate a user (is_active=False). Cannot deactivate self."""
        if target_user_id == acting_admin_id:
            raise ConflictError("Admins cannot deactivate themselves.")
        user = self.users.get_active_by_id(target_user_id)
        if user is None:
            raise NotFoundError("User not found.")
        self.users.soft_delete(user)
        db.session.commit()
        return user

    def reactivate_user(self, *, target_user_id: uuid.UUID, acting_admin_id: uuid.UUID) -> User:
        """Restore a deactivated user (is_active=True)."""
        if target_user_id == acting_admin_id:
            raise ConflictError("Admins cannot reactivate themselves.")
        user = self.users.get_by_id(target_user_id)
        if user is None:
            raise NotFoundError("User not found.")
        if user.is_active:
            raise ValidationError("User is already active.")
        user.is_active = True
        user.deactivated_at = None
        db.session.commit()
        return user

    def assign_role(self, *, target_user_id: uuid.UUID, new_role: str, acting_admin_id: uuid.UUID) -> User:
        """Assign a role to a user (Student/Teacher/Admin)."""
        from app.services.role_service import role_service

        if new_role not in ("Student", "Teacher", "Admin"):
            raise ValidationError(f"Invalid role: {new_role}.")

        user = self.users.get_by_id(target_user_id)
        if user is None:
            raise NotFoundError("User not found.")

        user.role = new_role
        db.session.commit()

        from app.services.audit_service import audit_service
        audit_service.record(
            action="admin.user.role.assign",
            entity_type="user",
            entity_id=user.id,
            changes={"new_role": new_role, "actor": acting_admin_id},
        )

        return user

    def remove_role(self, *, target_user_id: uuid.UUID, acting_admin_id: uuid.UUID) -> User:
        """Revoke a user's role (down to Student if they had Teacher/Admin)."""
        user = self.users.get_by_id(target_user_id)
        if user is None:
            raise NotFoundError("User not found.")

        user.role = "Student"
        db.session.commit()

        from app.services.audit_service import audit_service
        audit_service.record(
            action="admin.user.role.remove",
            entity_type="user",
            entity_id=user.id,
            changes={"old_role": "Student", "actor": acting_admin_id},
        )

        return user

    # ---- Management: Academic Structure ----------------------------------- #

    def department_create(self, *, name: str, code: str | None, description: str, acting_admin_id: uuid.UUID) -> Department:
        from app.models import Department
        dept = Department(name=name, code=code, description=description, is_active=True)
        db.session.add(dept)
        db.session.commit()
        return dept

    def department_update(self, *, dept_id: uuid.UUID, name: str | None, code: str | None, description: str | None, acting_admin_id: uuid.UUID) -> Department:
        from app.models import Department
        dept = self.departments.get_active_by_id(dept_id)
        if dept is None:
            raise NotFoundError("Department not found.")
        if name is not None:
            dept.name = name
        if code is not None:
            dept.code = code
        if description is not None:
            dept.description = description
        db.session.commit()
        return dept

    def department_delete(self, *, dept_id: uuid.UUID, acting_admin_id: uuid.UUID) -> None:
        from app.models import Department
        dept = self.departments.get_active_by_id(dept_id)
        if dept is None:
            raise NotFoundError("Department not found.")
        # Check for existing programs
        prog_count = db.session.query(db.func.count(Program.id)).filter(Program.department_id == dept_id, Program.is_active.is_(True)).scalar()
        if prog_count and prog_count > 0:
            raise ValidationError("Cannot delete department with existing active programs. Reassign or archive programs first.")
        dept.is_active = False
        dept.deleted_at = db.func.now()
        db.session.commit()

    def program_create(self, *, name: str, department_id: uuid.UUID, code: str | None, description: str, acting_admin_id: uuid.UUID) -> Program:
        from app.models import Program
        dep = self.departments.get_active_by_id(department_id)
        if dep is None:
            raise NotFoundError("Parent department not found.")
        prog = Program(name=name, department_id=department_id, code=code, description=description, is_active=True)
        db.session.add(prog)
        db.session.commit()
        return prog

    def program_update(self, *, prog_id: uuid.UUID, name: str | None, code: str | None, description: str | None, acting_admin_id: uuid.UUID) -> Program:
        from app.models import Program
        prog = self.programs.get_active_by_id(prog_id)
        if prog is None:
            raise NotFoundError("Program not found.")
        if name is not None:
            prog.name = name
        if code is not None:
            prog.code = code
        if description is not None:
            prog.description = description
        db.session.commit()
        return prog

    def section_create(self, *, name: str, program_id: uuid.UUID, capacity: int | None, acting_admin_id: uuid.UUID) -> Section:
        from app.models import Section
        prog = self.programs.get_active_by_id(program_id)
        if prog is None:
            raise NotFoundError("Parent program not found.")
        sec = Section(name=name, program_id=program_id, capacity=capacity, is_active=True)
        db.session.add(sec)
        db.session.commit()
        return sec

    # ---- Management: Groups ----------------------------------------------- #

    def group_archive(self, *, group_id: uuid.UUID, acting_admin_id: uuid.UUID) -> Group:
        from app.services.group_service import group_service
        group = group_service.get_active_group(group_id)
        if group is None:
            raise NotFoundError("Group not found.")
        # Check participant count
        from app.repositories import GroupRepository
        member_count = db.session.query(db.func.count()).select_from(group.__class__.__table__ if hasattr(group, '__class__') else "user_groups").filter(group.__class__.__table__.c.group_id == group_id, group.__class__.__table__.c.left_at.is_(None)) if hasattr(group, '__table__') else 0
        # Simpler check via group service
        members = group_service.groups.list_group_members(group_id)
        if len(members) <= 1:
            raise ValidationError("Cannot archive group with only owner. Transfer ownership or add members first.")
        group.is_active = False
        group.deleted_at = db.func.now()
        db.session.commit()
        return group

    def group_reassign_owner(self, *, group_id: uuid.UUID, new_owner_id: uuid.UUID, acting_admin_id: uuid.UUID) -> Group:
        from app.services.group_service import group_service
        return group_service.transfer_ownership(group_id, new_owner_id, acting_admin_id)

    # ---- Management: Resources -------------------------------------------- #

    def resource_unpublish(self, *, resource_id: uuid.UUID, acting_admin_id: uuid.UUID) -> Resource:
        from app.models import Resource
        res = self.resources.get_active_by_id(resource_id)
        if res is None:
            raise NotFoundError("Resource not found.")
        res.is_published = False
        db.session.commit()
        return res

    def resource_soft_delete(self, *, resource_id: uuid.UUID, acting_admin_id: uuid.UUID) -> Resource:
        from app.models import Resource
        res = self.resources.get_active_by_id(resource_id)
        if res is None:
            raise NotFoundError("Resource not found.")
        res.is_active = False
        db.session.commit()
        return res

    def resource_scan_status(self, *, resource_id: uuid.UUID) -> dict:
        from app.models import FileRecord
        res = self.resources.get_active_by_id(resource_id)
        if res is None:
            raise NotFoundError("Resource not found.")
        file_id = res.file_id
        if file_id is None:
            return {"status": "no_file", "detail": "Resource has no associated file."}
        file_rec = db.session.get(FileRecord, file_id)
        if file_rec is None:
            return {"status": "file_missing", "detail": "File record not found."}
        return {"status": file_rec.scan_status, "detail": None}

    # ---- Management: Teacher Allowlist ------------------------------------ #

    def allowlist_add(self, *, email: str, acting_admin_id: uuid.UUID) -> TeacherAllowlist:
        from app.models import TeacherAllowlist
        existing = db.session.query(TeacherAllowlist).filter(TeacherAllowlist.email == email).first()
        if existing:
            raise ValidationError("Email already in allowlist.")
        entry = TeacherAllowlist(email=email, is_approved=False, added_by=acting_admin_id)
        db.session.add(entry)
        db.session.commit()
        return entry

    def allowlist_remove(self, *, email: str, acting_admin_id: uuid.UUID) -> None:
        from app.models import TeacherAllowlist
        entry = db.session.query(TeacherAllowlist).filter(TeacherAllowlist.email == email).first()
        if entry is None:
            raise NotFoundError("Email not found in allowlist.")
        db.session.delete(entry)
        db.session.commit()

    def allowlist_approve(self, *, email: str, acting_admin_id: uuid.UUID) -> TeacherAllowlist:
        from app.models import TeacherAllowlist
        entry = db.session.query(TeacherAllowlist).filter(TeacherAllowlist.email == email).first()
        if entry is None:
            raise NotFoundError("Email not found in allowlist.")
        entry.is_approved = True
        entry.approved_at = db.func.now()
        entry.approved_by = acting_admin_id
        db.session.commit()
        return entry

    def allowlist_list(self, *, acting_admin_id: uuid.UUID) -> list[TeacherAllowlist]:
        from app.models import TeacherAllowlist
        return db.session.query(TeacherAllowlist).all()

    # ---- Moderation Queue ------------------------------------------------- #

    def moderation_quarantine_list(self) -> list[dict]:
        from app.models import FileRecord, Resource
        stmt = db.select(FileRecord, Resource).select_from(FileRecord).outerjoin(Resource, Resource.file_id == FileRecord.id)
        rows = db.session.execute(stmt).fetchall()

        result = []
        for file_rec, resource in rows:
            if file_rec.scan_status == "infected":
                days_infected = max(0, (datetime.now(timezone.utc) - file_rec.created_at.replace(tzinfo=timezone.utc)).days)
                result.append({
                    "file_id": str(file_rec.id),
                    "file_original": file_rec.original_filename,
                    "scan_status": file_rec.scan_status,
                    "created_at": file_rec.created_at.isoformat() if file_rec.created_at else None,
                    "resource_title": resource.title if resource else "Unknown",
                    "resource_id": str(resource.id) if resource else None,
                    "days_infected": days_infected,
                })
        return result

    def moderation_confirm_delete(self, *, file_id: uuid.UUID, justification: str, acting_admin_id: uuid.UUID) -> dict:
        from app.models import FileRecord, Resource
        file_rec = db.session.get(FileRecord, file_id)
        if file_rec is None:
            raise NotFoundError("File record not found.")

        # Mark resource as inactive
        if file_rec.resource_id:
            res = db.session.get(Resource, file_rec.resource_id)
            if res:
                res.is_active = False
                res.is_published = False
                res.quarantine_justification = justification
                res.quarantined_at = db.func.now()

        # Soft-delete the file record
        file_rec.is_active = False
        file_rec.deleted_at = db.func.now()

        db.session.commit()

        from app.services.audit_service import audit_service
        audit_service.record(
            action="admin.moderation.delete_confirm",
            entity_type="file",
            entity_id=file_id,
            changes={"justification": justification, "actor": acting_admin_id},
        )

        return {
            "action": "confirm_delete",
            "file_id": file_id,
            "justification": justification,
            "admin": acting_admin_id,
            "completed_at": db.func.now(),
        }

    # ---- Audit Log Viewer ------------------------------------------------- #

    def audit_logs_filter(
        self,
        *,
        actor_id: uuid.UUID | None,
        action: str | None,
        entity_type: str | None,
        entity_id: uuid.UUID | None,
        request_id: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AuditLog], int]:
        from app.repositories import AuditLogRepository
        # Use the repository's filter method if available, otherwise build query
        # For now, build a simple filtered query
        query = db.session.query(AuditLog)

        if actor_id is not None:
            query = query.filter(AuditLog.actor_id == actor_id)
        if action is not None:
            query = query.filter(AuditLog.action == action)
        if entity_type is not None:
            query = query.filter(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            query = query.filter(AuditLog.entity_id == entity_id)
        if request_id is not None:
            query = query.filter(AuditLog.request_context.has_key("request_id") & (db.cast(AuditLog.request_context, db.String).contains(request_id)))  # noqa: E501
        if date_from is not None:
            query = query.filter(AuditLog.created_at >= date_from)
        if date_to is not None:
            query = query.filter(AuditLog.created_at <= date_to)

        total = query.count()
        query = query.order_by(AuditLog.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
        rows = query.all()

        return rows, total

    # ---- System Settings (read-only env overview) ----------------------- #

    def settings_overview(self) -> dict:
        from app.config import DevelopmentConfig
        cfg = DevelopmentConfig()
        return {
            "upload_max_size_bytes": cfg.UPLOAD_MAX_SIZE_BYTES,
            "upload_allowed_extensions": list(cfg.UPLOAD_ALLOWED_EXTENSIONS),
            "rate_limit_default": cfg.RATELIMIT_DEFAULT,
            "rate_limit_auth": cfg.RATELIMIT_AUTH,
            "jwt_access_minutes": cfg.JWT_ACCESS_TOKEN_MINUTES,
            "env": cfg.ENV,
        }


admin_service = AdminService()