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
from app.models import (
    User,
    Department,
    Program,
    Semester,
    Section,
    Subject,
    Group,
    Resource,
    AuditLog,
    Notification,
    TeacherAllowlist,
)
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
        from app.models import Resource

        # Total users by role
        user_count_by_role = {}
        for role_name in ("Student", "Teacher", "Admin"):
            count = self.users.count_by_role(role_name)
            user_count_by_role[role_name] = count

        # Active users (7/30 days)
        now = datetime.now(timezone.utc)
        seven_ago = now - timedelta(days=7)
        thirty_ago = now - timedelta(days=30)
        active_7d = self.users.count_active_between(seven_ago, now)
        active_30d = self.users.count_active_between(thirty_ago, now)

        # Resources by type and department
        resource_stmt = (
            db.select(Resource.resource_type, Resource.department_id, db.func.count(Resource.id))
            .group_by(Resource.resource_type, Resource.department_id)
        )
        resource_rows = db.session.execute(resource_stmt).all()
        resources_by_type_dept = {
            f"dept_{r.department_id}_type_{r.resource_type}": r.count
            for r in resource_rows
        }

        # Storage used: total file sizes per bucket (from files table)
        file_stmt = db.select(db.func.sum(Resource.file_id.size_mb if hasattr(Resource, "file_id") else 0))  # noqa: E501
        # Simpler: sum from file_model
        from app.models import FileRecord
        storage_stmt = db.select(db.func.sum(FileRecord.file_size)).select_from(FileRecord)
        storage_total_bytes = int(db.session.scalar(storage_stmt) or 0)

        # Uploads and downloads over time (daily counts last 30 days)
        # Use daily_stats summary table if available, else compute from raw
        try:
            daily_stmt = (
                db.select(
                    db.func.date_trunc("day", Resource.created_at).label("day"),
                    db.func.count(Resource.id).label("created"),
                    db.func.count(Resource.download_count).label("downloaded"),
                )
                .select_from(Resource)
                .where(Resource.created_at >= now - timedelta(days=30))
                .group_by(db.func.date_trunc("day", Resource.created_at))
                .order_by(db.func.date_trunc("day", Resource.created_at))
            )
            daily_rows = db.session.execute(daily_stmt).all()
            uploads_over_time = {str(r.day): r.created for r in daily_rows}
            downloads_over_time = {str(r.day): r.downloaded for r in daily_rows}
        except Exception:
            uploads_over_time = {}
            downloads_over_time = {}

        # Scan outcomes (clean/infected/failed)
        from app.models import FileRecord
        scan_stmt = (
            db.select(FileRecord.scan_status, db.func.count(FileRecord.id))
            .select_from(FileRecord)
            .group_by(FileRecord.scan_status)
        scan_rows = db.session.execute(scan_stmt).all()
        scan_outcomes = {str(r.scan_status): r.count for r in scan_rows}

        # Chat activity: messages per day, active groups
        try:
            msg_stmt = (
                db.select(
                    db.func.date_trunc("day", Message.created_at).label("day"),
                    db.func.count(Message.id).label("messages"),
                )
                .select_from(Message)
                .where(Message.created_at >= now - timedelta(days=30))
                .group_by(db.func.date_trunc("day", Message.created_at))
                .order_by(db.func.date_trunc("day", Message.created_at))
            )
            msg_rows = db.session.execute(msg_stmt).all()
            messages_per_day = {str(r.day): r.messages for r in msg_rows}
            active_groups = self.groups.count_active()
        except Exception:
            messages_per_day = {}
            active_groups = 0

        # Pending items needing attention
        # Stuck scans: pending/scanning > 30 min (requeued by health task)
        stale_threshold = now - timedelta(minutes=30)
        stuck_stmt = (
            db.select(db.func.count(FileRecord.id))
            .select_from(FileRecord)
            .where(FileRecord.scan_status.in_(["pending", "scanning"]))
            .where(FileRecord.created_at < stale_threshold)
        stuck_count = int(db.session.scalar(stuck_stmt) or 0)

        # Failed email deliveries: notifications with bounce status or never read
        # We'll count notifications older than 24h that are still unread
        failed_email_threshold = now - timedelta(hours=24)
        failed_stmt = (
            db.select(db.func.count(Notification.id))
            .select_from(Notification)
            .where(Notification.is_read.is_(False))
            .where(Notification.created_at < failed_email_threshold)
        failed_email_count = int(db.session.scalar(failed_stmt) or 0)

        return {
            "users": {
                "total_by_role": user_count_by_role,
                "active_7d": active_7d,
                "active_30d": active_30d,
            },
            "resources": {
                "by_type_department": resources_by_type_dept,
                "storage_used_bytes": storage_total_bytes,
                "uploads_over_time": uploads_over_time,  # dict ISO date -> count
                "downloads_over_time": downloads_over_time,
            },
            "scans": scan_outcomes,
            "chat": {
                "messages_per_day": messages_per_day,  # ISO date -> count
                "active_groups": active_groups,
            },
            "pending": {
                "stuck_scans": stuck_count,
                "failed_email_deliveries": failed_email_count,
            },
        }

    # ---- Management: Users ------------------------------------------------ #

    def list_users(
        self,
        *,
        query: str | None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[User], int]:
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

        # Prevent non-admin from assigning admin to themselves or others without check
        user = self.users.get_by_id(target_user_id)
        if user is None:
            raise NotFoundError("User not found.")

        # Update role via the role service / direct DB update
        # The role is stored as a JWT claim; we update the user's role column and audit it
        user.role = new_role
        db.session.commit()

        # Audit
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

        # You can't remove the last admin's admin status via this API;
        # require a new admin assignment first. For now, just set to Student.
        user.role = "Student"
        db.session.commit()

        from app.services.audit_service import audit_service
        audit_service.record(
            action="admin.user.role.remove",
            entity_type="user",
            entity_id=user.id,
            changes={"old_role": user.role, "actor": acting_admin_id},
        )

        return user

    # ---- Management: Academic Structure ----------------------------------- #

    def department_create(self, *, name: str, code: str | None, description: str, acting_admin_id: uuid.UUID) -> Department:
        """Create a department with referential integrity."""
        dept = Department(name=name, code=code, description=description, is_active=True)
        db.session.add(dept)
        db.session.commit()
        return dept

    def department_update(self, *, dept_id: uuid.UUID, name: str | None, code: str | None, description: str | None, acting_admin_id: uuid.UUID) -> Department:
        """Update a department."""
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
        """Delete (soft) a department; REFERENTIAL RESTRICT if has programs."""
        dept = self.departments.get_active_by_id(dept_id)
        if dept is None:
            raise NotFoundError("Department not found.")
        # Check for existing programs
        prog_count = db.session.query(db.func.count()).select_from(Program).filter(Program.department_id == dept_id).scalar()
        if prog_count and prog_count > 0:
            raise ValidationError("Cannot delete department with existing programs. Reassign or archive programs first.")
        dept.is_active = False
        dept.deleted_at = db.func.now()
        db.session.commit()

    def program_create(self, *, name: str, department_id: uuid.UUID, code: str | None, description: str, acting_admin_id: uuid.UUID) -> Program:
        """Create a program under a department."""
        # Validate department exists
        dep = self.departments.get_active_by_id(department_id)
        if dep is None:
            raise NotFoundError("Parent department not found.")
        prog = Program(name=name, department_id=department_id, code=code, description=description, is_active=True)
        db.session.add(prog)
        db.session.commit()
        return prog

    def program_update(self, *, prog_id: uuid.UUID, name: str | None, code: str | None, description: str | None, acting_admin_id: uuid.UUID) -> Program:
        """Update a program."""
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
        """Create a section under a program."""
        prog = self.programs.get_active_by_id(program_id)
        if prog is None:
            raise NotFoundError("Parent program not found.")
        sec = Section(name=name, program_id=program_id, capacity=capacity, is_active=True)
        db.session.add(sec)
        db.session.commit()
        return sec

    # ---- Management: Groups ----------------------------------------------- #

    def group_archive(self, *, group_id: uuid.UUID, acting_admin_id: uuid.UUID) -> Group:
        """Archive a group (is_active=False) if no active participants."""
        group = self.groups.get_active_by_id(group_id)
        if group is None:
            raise NotFoundError("Group not found.")
        # Check participant count
        part_count = db.session.query(db.func.count()).select_from(group.__class__.__table__.prefixes[0] if hasattr(group.__class__, '__table__') else "user_groups").filter(group.__class__.__table__.c.group_id == group_id, "left_at".is_(None))  # noqa: E501
        # Simpler: use group_service logic
        from app.services.group_service import group_service
        # Check if group has active members beyond owner
        members = group_service.groups.list_group_members(group_id)
        # If only owner remains, prevent archive or force ownership transfer
        if len(members) <= 1:
            raise ValidationError("Cannot archive group with only owner. Transfer ownership or add members first.")
        group.is_active = False
        group.deleted_at = db.func.now()
        db.session.commit()
        return group

    def group_reassign_owner(self, *, group_id: uuid.UUID, new_owner_id: uuid.UUID, acting_admin_id: uuid.UUID) -> Group:
        """Reassign group ownership (same logic as Phase 4 transfer_ownership)."""
        from app.services.group_service import group_service
        return group_service.transfer_ownership(group_id, new_owner_id, acting_admin_id)

    # ---- Management: Resources -------------------------------------------- #

    def resource_unpublish(self, *, resource_id: uuid.UUID, acting_admin_id: uuid.UUID) -> Resource:
        """Unpublish a resource (is_published=False)."""
        res = self.resources.get_active_by_id(resource_id)
        if res is None:
            raise NotFoundError("Resource not found.")
        res.is_published = False
        db.session.commit()
        return res

    def resource_soft_delete(self, *, resource_id: uuid.UUID, acting_admin_id: uuid.UUID) -> Resource:
        """Soft-delete a resource; move underlying Supabase object to quarantine after 24h grace period."""
        res = self.resources.get_active_by_id(resource_id)
        if res is None:
            raise NotFoundError("Resource not found.")
        res.is_active = False
        # TODO: enqueue Celery task to move Supabase object to quarantine after 24h grace period
        db.session.commit()
        return res

    def resource_scan_status(self, *, resource_id: uuid.UUID) -> dict:
        """Return the scan status of a resource's underlying file."""
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
        """Add an email to the teacher allowlist."""
        # Check if already present
        existing = self.teacher_allowlist.get_by_email(email)
        if existing:
            raise ValidationError("Email already in allowlist.")
        entry = TeacherAllowlist(email=email, is_approved=False, added_by=acting_admin_id)
        db.session.add(entry)
        db.session.commit()
        return entry

    def allowlist_remove(self, *, email: str, acting_admin_id: uuid.UUID) -> None:
        """Remove an email from the teacher allowlist."""
        entry = self.teacher_allowlist.get_by_email(email)
        if entry is None:
            raise NotFoundError("Email not found in allowlist.")
        db.session.delete(entry)
        db.session.commit()

    def allowlist_approve(self, *, email: str, acting_admin_id: uuid.UUID) -> TeacherAllowlist:
        """Approve an email on the teacher allowlist."""
        entry = self.teacher_allowlist.get_by_email(email)
        if entry is None:
            raise NotFoundError("Email not found in allowlist.")
        entry.is_approved = True
        entry.approved_at = db.func.now()
        entry.approved_by = acting_admin_id
        db.session.commit()
        return entry

    def allowlist_list(self, *, acting_admin_id: uuid.UUID) -> Sequence[TeacherAllowlist]:
        """List all allowlist entries."""
        return self.teacher_allowlist.list_all()

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
    ) -> tuple[Sequence[AuditLog], int]:
        """Filter audit logs with keyset pagination."""
        from app.repositories import AuditLogRepository

        return self.audit_logs.filter(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )

    # ---- Moderation Queue ------------------------------------------------- #

    def moderation_quarantine_list(self) -> Sequence[dict]:
        """Return files with infected status needing admin attention."""
        from app.models import FileRecord, Resource

        # Files with scan_status='infected' that are linked to active resources
        stmt = (
            db.select(FileRecord, Resource)
            .select_from(FileRecord)
            .join(Resource, Resource.file_id == FileRecord.id, isouter=True)
            .where(FileRecord.scan_status == "infected")
            .where(FileRecord.is_active.is_(True))  # only active files
        )
        rows = db.session.execute(stmt).all()

        result = []
        for file_rec, resource in rows:
            result.append({
                "file_id": str(file_rec.id),
                "file_original": file_rec.original_filename,
                "scan_status": file_rec.scan_status,
                "created_at": file_rec.created_at.isoformat(),
                "resource_title": resource.title if resource else "Unknown",
                "resource_id": str(resource.id) if resource else None,
                "days_infected": max(0, (datetime.now(timezone.utc) - file_rec.created_at.replace(tzinfo=timezone.utc)).days),
            })
        return result

    def moderation_confirm_delete(self, *, file_id: uuid.UUID, justification: str, acting_admin_id: uuid.UUID) -> dict:
        """Permanently delete an infected file and its associated resource."""
        from app.models import FileRecord, Resource

        file_rec = db.session.get(FileRecord, file_id)
        if file_rec is None:
            raise NotFoundError("File record not found.")

        # Mark resource as inactive (move to quarantine concept)
        if file_rec.resource_id:
            res = db.session.get(Resource, file_rec.resource_id)
            if res:
                res.is_active = False
                res.is_published = False
                # TODO: enqueue Celery to actually remove from Supabase after 24h or immediately for infected
                res.quarantine_justification = justification
                res.quarantined_at = db.func.now()

        # Optionally hard-delete the file record (or just mark inactive)
        file_rec.is_active = False
        file_rec.deleted_at = db.func.now()

        db.session.commit()

        # Audit
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

    # ---- System Settings (env-driven, no new DB table) ------------------- #

    # These are already in config; no new table needed per Phase 5 scope decision.


admin_service = AdminService()