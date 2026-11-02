"""Tests for migration 0011: add academic hierarchy FKs to Resource.

These tests exercise the Alembic migration in isolation (upgrade/downgrade
round trips) on a file-based SQLite database via the Alembic CLI, so that
connections share the same schema and each alembic invocation is clean.
"""

from __future__ import annotations

import os
import subprocess

import pytest
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

ENV = {
    "APP_ENV": "testing",
    "APP_SECRET_KEY": "test-secret",
    "JWT_SECRET_KEY": "test-jwt-secret",
}


def _alembic(db_url):
    env = dict(ENV)
    env["TEST_DATABASE_URL"] = db_url
    os.environ["TEST_DATABASE_URL"] = db_url  # also set for create_app() in main proc
    return env


VENV_PYTHON = "/tmp/opencode/cv-venv/bin/python"

def _run_alembic(env, *args):
    """Run an alembic CLI command; raise on failure."""
    result = subprocess.run(
        [VENV_PYTHON, "-m", "alembic", *args],
        env=env,
        capture_output=True,
        text=True,
        cwd="/home/babai/Desktop/codeing/CampusVault/backend",
    )
    if result.returncode != 0:
        raise AssertionError(
            f"alembic {' '.join(args)} failed (rc={result.returncode})\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result.stdout


def _schema_state(engine):
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("resources")}
    fks = {fk["name"] for fk in insp.get_foreign_keys("resources") if fk["name"]}
    idxs = {ix["name"] for ix in insp.get_indexes("resources")}
    return cols, fks, idxs


class TestMigration0011:
    """Upgrade/downgrade round-trip tests for migration 0011."""

    @pytest.fixture
    def db_url(self, tmp_path):
        db_file = tmp_path / "test.db"
        db_file.unlink(missing_ok=True)
        return f"sqlite:///{db_file}"

    def test_downgrade_then_upgrade_round_trip(self, db_url):
        env = _alembic(db_url)
        app = create_app()
        with app.app_context():
            _db.create_all()
            # Stamp at new head (columns exist from create_all).
            _run_alembic(env, "stamp", NEW_HEAD)

            cols, fks, idxs = _schema_state(_db.engine)
            for c in HIERARCHY_COLUMNS:
                assert c in cols, f"{c} should exist after create_all"

            # Downgrade to previous head: columns/FKs/indexes removed.
            _run_alembic(env, "downgrade", PREVIOUS_HEAD)
            cols, fks, idxs = _schema_state(_db.engine)
            for c in HIERARCHY_COLUMNS:
                assert c not in cols, f"{c} should be removed after downgrade"
            for fk in FK_NAMES:
                assert fk not in fks, f"{fk} should be removed after downgrade"
            for ix in INDEX_NAMES:
                assert ix not in idxs, f"{ix} should be removed after downgrade"

            # Upgrade to new head: columns/FKs/indexes added back.
            _run_alembic(env, "upgrade", NEW_HEAD)
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

    def test_upgrade_downgrade_upgrade_triple(self, db_url):
        env = _alembic(db_url)
        app = create_app()
        with app.app_context():
            _db.create_all()
            _run_alembic(env, "stamp", NEW_HEAD)

            _run_alembic(env, "downgrade", PREVIOUS_HEAD)
            state1 = _schema_state(_db.engine)
            for c in HIERARCHY_COLUMNS:
                assert c not in state1[0]

            _run_alembic(env, "upgrade", NEW_HEAD)
            state2 = _schema_state(_db.engine)

            _run_alembic(env, "downgrade", PREVIOUS_HEAD)
            state3 = _schema_state(_db.engine)
            for c in HIERARCHY_COLUMNS:
                assert c not in state3[0]

            _run_alembic(env, "upgrade", NEW_HEAD)
            state4 = _schema_state(_db.engine)

            assert state2 == state4

    def test_no_model_migration_drift(self, db_url):
        """Autogenerate produces no diff: models match migrations."""
        env = _alembic(db_url)
        app = create_app()
        with app.app_context():
            _db.create_all()
            _run_alembic(env, "stamp", NEW_HEAD)

            # Autogenerate to a temp file; if there's no drift, the generated
            # migration body is empty (only revision identifiers).
            result = subprocess.run(
                [VENV_PYTHON, "-m", "alembic", "revision", "--autogenerate",
                 "-m", "drift_check"],
                env=env,
                capture_output=True,
                text=True,
                cwd="/home/babai/Desktop/codeing/CampusVault/backend",
            )
            assert result.returncode == 0, (
                f"autogenerate failed: {result.stderr}"
            )
            # Find the generated file and check it has no schema operations.
            import glob as _glob
            generated = _glob.glob(
                "/home/babai/Desktop/codeing/CampusVault/backend/alembic/versions/*drift_check.py"
            )
            assert generated, "autogenerate did not produce a file"
            content = open(generated[0]).read()
            assert "def upgrade()" in content
            assert "def downgrade()" in content
            # Body should contain only `pass` (no ops) if no drift.
            upgrade_body = content.split("def upgrade()")[1].split("def downgrade()")[0]
            downgrade_body = content.split("def downgrade()")[1]
            assert "pass" in upgrade_body or not any(
                op in upgrade_body for op in ("op.create", "op.add", "op.drop", "op.alter")
            ), f"Unexpected upgrade ops in drift check:\n{upgrade_body}"
            assert "pass" in downgrade_body or not any(
                op in downgrade_body for op in ("op.create", "op.add", "op.drop", "op.alter")
            ), f"Unexpected downgrade ops in drift check:\n{downgrade_body}"
            # Clean up generated file.
            os.remove(generated[0])
