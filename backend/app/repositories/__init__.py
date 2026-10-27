"""Repository layer — the *only* place that touches the ORM session.

Import repositories through this package so refactors stay localized:
    from app.repositories import UserRepository
"""

from app.repositories.academic_repository import (
    DepartmentRepository,
    ProgramRepository,
    SectionRepository,
    SemesterRepository,
    SubjectRepository,
)
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.base_repository import BaseRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.file_repository import FileRepository
from app.repositories.group_repository import GroupRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.resource_repository import ResourceRepository
from app.repositories.role_repository import PermissionRepository, RoleRepository
from app.repositories.user_repository import UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "RoleRepository",
    "PermissionRepository",
    "DepartmentRepository",
    "ProgramRepository",
    "SemesterRepository",
    "SectionRepository",
    "SubjectRepository",
    "GroupRepository",
    "ConversationRepository",
    "MessageRepository",
    "FileRepository",
    "ResourceRepository",
    "NotificationRepository",
    "AuditLogRepository",
]
