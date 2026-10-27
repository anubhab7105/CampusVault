"""User notification preferences (minimal model)."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email_notifications", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("push_notifications", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("in_app_notifications", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("digest_frequency", sa.String(16), nullable=False,
                  server_default="minute",  # minute | hour | day | off
                  ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("user_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
