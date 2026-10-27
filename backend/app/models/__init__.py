"""Model registry.

All models in one import surface — Alembic env.py and repositories import
from here so autogenerate always sees every table.
"""

from app.models.academic import Department, Program, Section, Semester, Subject
from app.models.audit_log import AuditLog
from app.models.base import (
    BaseModel,
    JSONType,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDType,
)
from app.models.conversation import Conversation, ConversationParticipant
from app.models.file_model import FileRecord
from app.models.group import Group, UserGroup
from app.models.message import Message
from app.models.notification import Notification
from app.models.resource import Resource
from app.models.role import Permission, Role, RolePermission
from app.models.user import User, UserRole

__all__ = [
    "BaseModel",
    "JSONType",
    "SoftDeleteMixin",
    "TimestampMixin",
    "UUIDType",
    "User",
    "UserRole",
    "Role",
    "Permission",
    "RolePermission",
    "Department",
    "Program",
    "Semester",
    "Section",
    "Subject",
    "Group",
    "UserGroup",
    "Conversation",
    "ConversationParticipant",
    "Message",
    "FileRecord",
    "Resource",
    "Notification",
    "AuditLog",
]
