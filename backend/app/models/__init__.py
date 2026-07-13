"""
Aggregates all models so Alembic's autogenerate can discover every table
via Base.metadata. Import this module (or app.models) before running
`alembic revision --autogenerate`.
"""
from app.models.base import Base

# Auth domain
from app.models.auth import User, StudentIdentity, TeacherIdentity, OTPCode, RefreshToken  # noqa: F401

# RBAC domain
from app.models.rbac import Role, Permission, RolePermission, UserRole  # noqa: F401

# Academic structure domain
from app.models.academic import Department, Program, Semester, Section, Subject, UserSection  # noqa: F401

# Chat domain
from app.models.chat import (  # noqa: F401
    Group,
    GroupMember,
    Conversation,
    ConversationParticipant,
    Message,
    MessageReceipt,
)

# Library / files domain
from app.models.library import File, Resource  # noqa: F401

# Notifications domain
from app.models.notifications import Notification  # noqa: F401

# Audit domain
from app.models.audit import AuditLog  # noqa: F401

__all__ = [
    "Base",
    "User", "StudentIdentity", "TeacherIdentity", "OTPCode", "RefreshToken",
    "Role", "Permission", "RolePermission", "UserRole",
    "Department", "Program", "Semester", "Section", "Subject", "UserSection",
    "Group", "GroupMember", "Conversation", "ConversationParticipant", "Message", "MessageReceipt",
    "File", "Resource",
    "Notification",
    "AuditLog",
]
