"""Add academic hierarchy foreign keys to Resource.

Adds department_id, program_id, semester_id and section_id columns to the
``resources`` table, each with a named foreign key and a named index.

department_id / program_id / semester_id are denormalized: they are derived
from subject_id (subject -> semester -> program -> department) on write and are
backfilled from existing subject_id values in this migration. section_id is
stored independently (not derivable from subject) and is left NULL for existing
rows.

All four columns are nullable in this migration so existing resources remain
valid and college-wide scoping is allowed. A follow-up migration can tighten
department_id / program_id / semester_id to NOT NULL once zero NULLs are
confirmed after backfill.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-02
"""

from __future__ import annotations

import logging

import sqlalchemy as sa

from alembic import context, op

# revision identifiers, used by Alembic.
revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

TABLE = "resources"

# Locally-defined UUID type so this migration is independent of application
# model imports (preserves the same UUID semantics as the app models).
UUID_TYPE = sa.Uuid(as_uuid=True)

# Constraint / index names (explicit, matching project convention).
FK_DEPARTMENT = "fk_resources_department_id"
FK_PROGRAM = "fk_resources_program_id"
FK_SEMESTER = "fk_resources_semester_id"
FK_SECTION = "fk_resources_section_id"

IX_DEPARTMENT = "ix_resources_department_id"
IX_PROGRAM = "ix_resources_program_id"
IX_SEMESTER = "ix_resources_semester_id"
IX_SECTION = "ix_resources_section_id"


def upgrade() -> None:
    # Add columns + FKs + indexes. batch_alter_table is used so the same
    # migration works on SQLite (which needs table rebuild for ALTER COLUMN
    # with constraints) and on PostgreSQL.
    with op.batch_alter_table(TABLE, schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("department_id", UUID_TYPE, nullable=True)
        )
        batch_op.add_column(
            sa.Column("program_id", UUID_TYPE, nullable=True)
        )
        batch_op.add_column(
            sa.Column("semester_id", UUID_TYPE, nullable=True)
        )
        batch_op.add_column(
            sa.Column("section_id", UUID_TYPE, nullable=True)
        )
        batch_op.create_foreign_key(
            FK_DEPARTMENT, "departments", ["department_id"], ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            FK_PROGRAM, "programs", ["program_id"], ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            FK_SEMESTER, "semesters", ["semester_id"], ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            FK_SECTION, "sections", ["section_id"], ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(IX_DEPARTMENT, ["department_id"])
        batch_op.create_index(IX_PROGRAM, ["program_id"])
        batch_op.create_index(IX_SEMESTER, ["semester_id"])
        batch_op.create_index(IX_SECTION, ["section_id"])

    # --- Backfill department_id / program_id / semester_id from subject_id ---
    # Use portable correlated subqueries (work on SQLite and PostgreSQL).
    # Soft-deleted ancestors are NOT filtered on deleted_at so that resources
    # pointing to soft-deleted hierarchy rows still populate.
    op.execute(
        sa.text(
            """
            UPDATE resources
            SET department_id = (
                SELECT d.id
                FROM subjects s
                JOIN semesters sem ON sem.id = s.semester_id
                JOIN programs p ON p.id = sem.program_id
                JOIN departments d ON d.id = p.department_id
                WHERE s.id = resources.subject_id
                LIMIT 1
            ),
            program_id = (
                SELECT p.id
                FROM subjects s
                JOIN semesters sem ON sem.id = s.semester_id
                JOIN programs p ON p.id = sem.program_id
                WHERE s.id = resources.subject_id
                LIMIT 1
            ),
            semester_id = (
                SELECT s.semester_id
                FROM subjects s
                WHERE s.id = resources.subject_id
                LIMIT 1
            )
            WHERE subject_id IS NOT NULL
            """
        )
    )

    # Report the count of rows still NULL on department_id after backfill.
    # A non-zero count indicates broken hierarchy data (subject without a
    # complete chain). Columns are nullable so this is informational, not fatal.
    # Skip in offline mode (no connection available); report via Alembic logging.
    if not context.is_offline_mode():
        connection = op.get_bind()
        result = connection.execute(
            sa.text("SELECT COUNT(*) FROM resources WHERE department_id IS NULL")
        )
        null_count = result.scalar() or 0
        logging.getLogger("alembic").info(
            "[0011] resources with NULL department_id after backfill: %s", null_count
        )


def downgrade() -> None:
    # Drop indexes, then FK constraints, then columns (reverse dependency order).
    with op.batch_alter_table(TABLE, schema=None) as batch_op:
        batch_op.drop_index(IX_SECTION)
        batch_op.drop_index(IX_SEMESTER)
        batch_op.drop_index(IX_PROGRAM)
        batch_op.drop_index(IX_DEPARTMENT)
        batch_op.drop_constraint(FK_SECTION, type_="foreignkey")
        batch_op.drop_constraint(FK_SEMESTER, type_="foreignkey")
        batch_op.drop_constraint(FK_PROGRAM, type_="foreignkey")
        batch_op.drop_constraint(FK_DEPARTMENT, type_="foreignkey")
        batch_op.drop_column("section_id")
        batch_op.drop_column("semester_id")
        batch_op.drop_column("program_id")
        batch_op.drop_column("department_id")
