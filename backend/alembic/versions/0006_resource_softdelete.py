"""Soft‑delete for resources with deferred cleanup task.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-27 16:20:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The ``resources`` table already has ``is_active`` (SoftDeleteMixin).
    # This migration just ensures the column defaults are explicit and adds a
    # comment for the deferred cleanup task.
    with op.batch_alter_table("resources", schema=None) as batch:
        batch.alter_column("is_active",
                           nullable=False,
                           server_default=sa.text("true"))
    # Note: the actual cleanup task (moving to quarantine / deleting the Supabase
    # object) is handled by a Celery beat task, not by a DB trigger.


def downgrade() -> None:
    with op.batch_alter_table("resources", schema=None) as batch:
        batch.alter_column("is_active",
                           nullable=True,
                           server_default=None)
