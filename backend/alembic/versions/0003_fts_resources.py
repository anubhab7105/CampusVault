"""Full‑text search index on resources.

Migration adds a ``fts`` column stored as ``TEXT`` (PostgreSQL ``TSVector``)
with a GIN index. On SQLite it is a plain ``TEXT`` column with no default; the
application generates the tsvector at insert time (``ResourceRepository.create``)
and the repository search method switches to ``LIKE`` queries automatically when
the dialect is not PostgreSQL.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-27 16:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resources",
        sa.Column("fts", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_resources_fts",
        "resources",
        ["fts"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_resources_fts", table_name="resources")
    op.drop_column("resources", "fts")