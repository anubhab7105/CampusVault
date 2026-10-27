"""Per‑user upload quota tracking."""

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
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("uploads_this_session", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_per_session", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("reset_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )
    # SQLite cannot enforce the FK from quota_usage.user_id → users.id
    # (UUID type rendering). The application-layer guard is sufficient.


def downgrade() -> None:
    op.drop_table("quota_usage")