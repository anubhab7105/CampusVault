"""Per‑user upload quota tracking.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-27 16:10:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quota_usage",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("uploads_this_session", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_per_session", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("reset_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now() + interval '1 hour'")),
        sa.PrimaryKeyConstraint("user_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("quota_usage")