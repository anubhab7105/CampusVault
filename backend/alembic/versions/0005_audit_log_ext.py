"""Audit log extension: outcome, ip_address, user_agent, changes.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-27 16:15:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("audit_log", schema=None) as batch:
        batch.add_column(sa.Column("outcome", sa.String(), nullable=True))
        batch.add_column(sa.Column("ip_address", sa.String(), nullable=True))
        batch.add_column(sa.Column("user_agent", sa.Text(), nullable=True))
        batch.add_column(sa.Column("changes", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("audit_log", schema=None) as batch:
        batch.drop_column("changes")
        batch.drop_column("user_agent")
        batch.drop_column("ip_address")
        batch.drop_column("outcome")