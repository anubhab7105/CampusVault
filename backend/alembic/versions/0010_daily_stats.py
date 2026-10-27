"""Daily summary statistics table — refreshed by Celery beat.

Stores aggregated metrics per day to avoid N+1 queries on the dashboard.
The ``daily_stats_archive`` table holds data older than ``RETENTION_DAYS``
(default 90) and is intended for cold storage or partitioning.

Migration 0010 creates the table; a separate Celery task (see tasks/daily_stats.py)
populates it once per day at 02:00 UTC.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_stats",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("users_active", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resources_published", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("messages_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scans_clean", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scans_infected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scans_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("downloads_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploads_total", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("day"),
    )
    op.create_index("ix_daily_stats_day", "daily_stats", ["day"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_daily_stats_day", table_name="daily_stats")
    op.drop_table("daily_stats")
