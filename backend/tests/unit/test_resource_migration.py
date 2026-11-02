"""Tests for migration 0011: add academic hierarchy FKs to Resource.

These tests exercise the Alembic migration in isolation (upgrade/downgrade
round trips) on a file-based SQLite database so that connections share the
same schema. Backfill behaviour is covered by the repository tests
(``test_resource_repository.py``) since the migration's backfill SQL is the
same derive logic exercised there.
"""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app import create_app
from app import models as all_models  # noqa: F401 — register all tables
from app.extensions import db as _db

PREVIOUS_HEAD = "0010"
NEW_HEAD = "0011"

HIERARCHY_COLUMNS = ("department_id", "program_id", "semester_id", "section_id")
FK_NAMES = (
    "fk_resources_department_id",
    "fk_resources_program_id",
    "fk_resources_semester_id",
    "fk_resources_section_id",
)
INDEX_NAMES = (
    "ix_resources_department_id",
    "ix_resources_program_id",
    "ix_resources_semester_id",
    "ix_resources_section_id",
)


def _make_app(tmp_path):
    import os

    db_file = tmp_path / "test.db"
    db_file.unlink(missing_ok=True)
    os.environ["APP_ENV"] = "testing"
    os.environ["APP_SECRET_KEY"] = "test-secret"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
    os.environ["TEST_DATABASE_URL"] = f"sqlite:///{db_file}"
    app = create_app()
    return app


def _alembic_config():
    return Config("alembic.ini")


def _schema_state(engine):
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("resources")}
    fks = {fk["name"] for fk in insp.get_foreign_keys("resources") if fk["name"]}
    idxs = {ix["name"] for ix in insp.get_indexes("resources")}
    return cols, fks, idxs


class TestMigration0011:
    """Upgrade/downgrade round-trip tests for migration 0011."""

    def test_downgrade_then_upgrade_round_trip(self, tmp_path):
        """Start with full schema (0011 columns present via create_all),
        downgrade to 0010 (columns removed), upgrade to 0011 (columns added
        back). Verifies both directions of the migration work."""
        app = _make_app(tmp_path)
        with app.app_context():
            _db.create_all()
            # Mark the DB as at the new head so we can downgrade from it.
            command.stamp(_alembic_config(), NEW_HEAD)

            # Start at full schema (0011 columns present from create_all).
            cols, fks, idxs = _schema_state(_db.engine)
            for c in HIERARCHY_COLUMNS:
                assert c in cols, f"{c} should exist after create_all"

            # Downgrade to previous head: columns/FKs/indexes removed.
            command.downgrade(_alembic_config(), PREVIOUS_HEAD)
            cols, fks, idxs = _schema_state(_db.engine)
            for c in HIERARCHY_COLUMNS:
                assert c not in cols, f"{c} should be removed after downgrade"
            for fk in FK_NAMES:
                assert fk not in fks, f"{fk} should be removed after downgrade"
            for ix in INDEX_NAMES:
                assert ix not in idxs, f"{ix} should be removed after downgrade"

            # Upgrade to new head: columns/FKs/indexes added back.
            command.upgrade(_alembic_config(), NEW_HEAD)
            cols, fks, idxs = _schema_state(_db.engine)
            for c in HIERARCHY_COLUMNS:
                assert c in cols, f"{c} should exist after upgrade"
            for fk in FK_NAMES:
                assert fk in fks, f"{fk} should exist after upgrade"
            for ix in INDEX_NAMES:
                assert ix in idxs, f"{ix} should exist after upgrade"

            # Verify FK targets.
            fk_map = {fk["name"]: fk for fk in inspect(_db.engine).get_foreign_keys("resources")}
            assert fk_map["fk_resources_department_id"]["referred_table"] == "departments"
            assert fk_map["fk_resources_program_id"]["referred_table"] == "programs"
            assert fk_map["fk_resources_semester_id"]["referred_table"] == "semesters"
            assert fk_map["fk_resources_section_id"]["referred_table"] == "sections"

    def test_upgrade_downgrade_upgrade_triple(self, tmp_path):
        """Upgrade → downgrade → upgrade leaves schema identical to
        post-upgrade state (no orphan constraints/indexes)."""
        app = _make_app(tmp_path)
        with app.app_context():
            _db.create_all()
            command.stamp(_alembic_config(), NEW_HEAD)

            command.downgrade(_alembic_config(), PREVIOUS_HEAD)
            command.upgrade(_alembic_config(), NEW_HEAD)
            state_after_first_upgrade = _schema_state(_db.engine)

            command.downgrade(_alembic_config(), PREVIOUS_HEAD)
            state_after_downgrade = _schema_state(_db.engine)
            for c in HIERARCHY_COLUMNS:
                assert c not in state_after_downgrade[0]

            command.upgrade(_alembic_config(), NEW_HEAD)
            state_after_second_upgrade = _schema_state(_db.engine)

            assert state_after_first_upgrade == state_after_second_upgrade
