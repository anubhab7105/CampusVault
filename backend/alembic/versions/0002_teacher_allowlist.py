"""teacher_allowlist table

Revision ID: 20261027_0002
Revises: 0001_initial_core_tables
Create Date: 2026-10-27 15:42:12.694838

"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20261027_0002"
down_revision = "0001_initial_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teacher_allowlist",
        sa.Column("id", sa.Uuid(), nullable=False, default=uuid.uuid4),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.sql.false()),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )


def downgrade() -> None:
    op.drop_table("teacher_allowlist")
