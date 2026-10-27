"""initial core tables

Revision ID: 0001
Revises:
Create Date: 2026-10-27

Creates the full Phase-1 core schema:
  users, roles, permissions, user_roles, role_permissions,
  departments, programs, semesters, sections, subjects,
  groups, user_groups, conversations, conversation_participants,
  messages, files, resources, notifications, audit_logs

Conventions (docs/03_DATABASE_GUIDE.md):
- UUID primary keys, FK integrity enforced, composite indexes on hot paths
- soft delete via deleted_at where product behavior requires history
- enum-like columns constrained with CHECK constraints (portable across
  Supabase PostgreSQL and SQLite test runs)

Documented future work (not built here): full-text search, materialized
views, analytics tables, archival strategy — see docs/03_DATABASE_GUIDE.md.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models import JSONType, UUIDType

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON_TS = sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    # ---- departments (referenced by users.department_id) ------------------- #
    op.create_table(
        "departments",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("description", sa.String(255)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.UniqueConstraint("name", name="uq_departments_name"),
        sa.UniqueConstraint("code", name="uq_departments_code"),
    )

    # ---- users ------------------------------------------------------------ #
    op.create_table(
        "users",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("avatar_url", sa.String(512)),
        sa.Column("auth_provider", sa.String(20), nullable=False, server_default="otp"),
        sa.Column("google_sub", sa.String(64)),
        sa.Column("email_verified_at", sa.DateTime(timezone=True)),
        sa.Column("department_id", UUIDType, sa.ForeignKey("departments.id", ondelete="SET NULL")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("google_sub", name="uq_users_google_sub"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_department_id", "users", ["department_id"])

    # ---- roles / permissions ------------------------------------------------ #
    op.create_table(
        "roles",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("description", sa.String(255)),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )
    op.create_index("ix_roles_name", "roles", ["name"])

    op.create_table(
        "permissions",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("module", sa.String(64), nullable=False),
        sa.Column("description", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"])
    op.create_index("ix_permissions_module", "permissions", ["module"])

    op.create_table(
        "user_roles",
        sa.Column("user_id", UUIDType, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", UUIDType, sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by", UUIDType, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_user_roles"),
    )
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    op.create_table(
        "role_permissions",
        sa.Column("role_id", UUIDType, sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "permission_id", UUIDType, sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
    )
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    # ---- academic hierarchy -------------------------------------------------- #
    op.create_table(
        "programs",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column(
            "department_id", UUIDType, sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("code", sa.String(24), nullable=False),
        sa.Column("description", sa.String(255)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.UniqueConstraint("department_id", "code", name="uq_programs_dept_code"),
    )
    op.create_index("ix_programs_department_id", "programs", ["department_id"])

    op.create_table(
        "semesters",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column("program_id", UUIDType, sa.ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("number", sa.SmallInteger, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.UniqueConstraint("program_id", "number", name="uq_semesters_program_num"),
    )
    op.create_index("ix_semesters_program_id", "semesters", ["program_id"])

    op.create_table(
        "sections",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column("semester_id", UUIDType, sa.ForeignKey("semesters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(24), nullable=False),
        sa.Column("capacity", sa.Integer),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.UniqueConstraint("semester_id", "name", name="uq_sections_semester_name"),
    )
    op.create_index("ix_sections_semester_id", "sections", ["semester_id"])

    op.create_table(
        "subjects",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column("semester_id", UUIDType, sa.ForeignKey("semesters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("code", sa.String(24), nullable=False),
        sa.Column("credits", sa.SmallInteger),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.UniqueConstraint("semester_id", "code", name="uq_subjects_semester_code"),
    )
    op.create_index("ix_subjects_semester_id", "subjects", ["semester_id"])

    # ---- groups / user_groups ------------------------------------------------- #
    op.create_table(
        "groups",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(1000)),
        sa.Column("group_type", sa.String(32), nullable=False, server_default="subject_group"),
        sa.Column("owner_id", UUIDType, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("subject_id", UUIDType, sa.ForeignKey("subjects.id", ondelete="SET NULL")),
        sa.Column("section_id", UUIDType, sa.ForeignKey("sections.id", ondelete="SET NULL")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
    )
    op.create_index("ix_groups_owner_id", "groups", ["owner_id"])
    op.create_index("ix_groups_subject_id", "groups", ["subject_id"])
    op.create_index("ix_groups_section_id", "groups", ["section_id"])
    op.create_index("ix_groups_group_type", "groups", ["group_type"])

    op.create_table(
        "user_groups",
        sa.Column("user_id", UUIDType, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("group_id", UUIDType, sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("added_by", UUIDType, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("left_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("user_id", "group_id", name="pk_user_groups"),
    )
    op.create_index("ix_user_groups_group_id", "user_groups", ["group_id"])

    # ---- files (before messages/resources reference them) ------------------------ #
    op.create_table(
        "files",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column("uploader_id", UUIDType, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("subject_id", UUIDType, sa.ForeignKey("subjects.id", ondelete="SET NULL")),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False, unique=True),
        sa.Column("bucket", sa.String(120), nullable=False),
        sa.Column("mime_type", sa.String(127), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("sha256_checksum", sa.String(64)),
        sa.Column("scan_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("scanned_at", sa.DateTime(timezone=True)),
        sa.Column("scan_pipeline_version", sa.String(32)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.CheckConstraint(
            "scan_status IN ('pending','clean','infected','failed')", name="ck_files_scan_status"
        ),
    )
    op.create_index("ix_files_uploader_id", "files", ["uploader_id"])
    op.create_index("ix_files_subject_id", "files", ["subject_id"])
    op.create_index("ix_files_scan_status", "files", ["scan_status"])
    op.create_index("ix_files_uploader_created", "files", ["uploader_id", "created_at"])
    op.create_index("ix_files_subject_created", "files", ["subject_id", "created_at"])

    # ---- conversations / participants ------------------------------------------- #
    op.create_table(
        "conversations",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column("conversation_type", sa.String(16), nullable=False),
        sa.Column("group_id", UUIDType, sa.ForeignKey("groups.id", ondelete="CASCADE"), unique=True),
        sa.Column("created_by", UUIDType, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("last_message_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.CheckConstraint(
            "conversation_type IN ('group','direct')", name="ck_conversations_type"
        ),
    )
    op.create_index("ix_conversations_conversation_type", "conversations", ["conversation_type"])
    op.create_index(
        "ix_conversations_type_last_msg", "conversations", ["conversation_type", "last_message_at"]
    )

    op.create_table(
        "conversation_participants",
        sa.Column(
            "conversation_id", UUIDType, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", UUIDType, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("last_read_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("conversation_id", "user_id", name="pk_conversation_participants"),
    )
    op.create_index("ix_conv_participants_user", "conversation_participants", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column(
            "conversation_id", UUIDType, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("sender_id", UUIDType, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("message_type", sa.String(16), nullable=False, server_default="text"),
        sa.Column("content", sa.Text),
        sa.Column("file_id", UUIDType, sa.ForeignKey("files.id", ondelete="SET NULL")),
        sa.Column("reply_to_id", UUIDType, sa.ForeignKey("messages.id", ondelete="SET NULL")),
        sa.Column("is_edited", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("edited_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.CheckConstraint("message_type IN ('text','file','system')", name="ck_messages_type"),
    )
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"])
    op.create_index("ix_messages_sender_conversation", "messages", ["sender_id", "conversation_id"])

    # ---- resources ------------------------------------------------------------------ #
    op.create_table(
        "resources",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column("subject_id", UUIDType, sa.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("file_id", UUIDType, sa.ForeignKey("files.id", ondelete="SET NULL"), unique=True),
        sa.Column("uploaded_by", UUIDType, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.String(2000)),
        sa.Column("resource_type", sa.String(24), nullable=False),
        sa.Column("visibility", sa.String(16), nullable=False, server_default="college"),
        sa.Column("external_url", sa.String(2048)),
        sa.Column("share_token", sa.String(64)),
        sa.Column("is_published", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("download_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("view_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.CheckConstraint(
            "resource_type IN ('note','book','past_paper','slide','link')",
            name="ck_resources_type",
        ),
        sa.CheckConstraint(
            "visibility IN ('section','subject','department','college','private')",
            name="ck_resources_visibility",
        ),
        sa.CheckConstraint("char_length(title) >= 3", name="ck_resources_title_min_length"),
    )
    op.create_index("ix_resources_subject_id", "resources", ["subject_id"])
    op.create_index("ix_resources_uploaded_by", "resources", ["uploaded_by"])
    op.create_index("ix_resources_resource_type", "resources", ["resource_type"])
    op.create_index("ix_resources_subject_created", "resources", ["subject_id", "created_at"])

    # ---- notifications ------------------------------------------------------------------ #
    op.create_table(
        "notifications",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column("user_id", UUIDType, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notification_type", sa.String(64), nullable=False, server_default="system"),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.String(500)),
        sa.Column("payload", JSONType),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
    )
    op.create_index(
        "ix_notifications_user_read_created", "notifications", ["user_id", "is_read", "created_at"]
    )
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])

    # ---- audit_logs ------------------------------------------------------------------------ #
    op.create_table(
        "audit_logs",
        sa.Column("id", UUIDType, primary_key=True, nullable=False),
        sa.Column("actor_id", UUIDType, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", UUIDType),
        sa.Column("request_context", JSONType),
        sa.Column("changes", JSONType),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=JSON_TS),
    )
    op.create_index("ix_audit_logs_actor_created", "audit_logs", ["actor_id", "created_at"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_action_created", "audit_logs", ["action", "created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("notifications")
    op.drop_table("resources")
    op.drop_table("messages")
    op.drop_table("conversation_participants")
    op.drop_table("conversations")
    op.drop_table("files")
    op.drop_table("user_groups")
    op.drop_table("groups")
    op.drop_table("subjects")
    op.drop_table("sections")
    op.drop_table("semesters")
    op.drop_table("programs")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("departments")
