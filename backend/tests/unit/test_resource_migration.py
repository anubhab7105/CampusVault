"""Tests for migration 0011: add academic hierarchy FKs to Resource.

These tests exercise the Alembic migration in isolation (upgrade/downgrade
round trips) on a file-based SQLite database via the Alembic CLI. Schema
setup uses raw SQLAlchemy (not Flask-SQLAlchemy) so the DB URL is fully
under our control and the alembic subprocess connects to the same file.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from app import models as all_models  # noqa: F401 — register all tables on metadata
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

VENV_PYTHON = sys.executable
BACKEND_DIR = str(Path(__file__).resolve().parents[2])


def _alembic_env(db_url):
    env = dict(os.environ)
    env.update(
        {
            "APP_ENV": "testing",
            "APP_SECRET_KEY": "test-secret",
            "JWT_SECRET_KEY": "test-jwt-secret",
            "TEST_DATABASE_URL": db_url,
        }
    )
    return env


def _run_alembic(env, *args):
    result = subprocess.run(  # noqa: S603, PLW1510
        [VENV_PYTHON, "-m", "alembic", *args],
        env=env,
        capture_output=True,
        text=True,
        cwd=BACKEND_DIR,
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


def _create_all_tables(engine):
    """Create every table from the SQLAlchemy metadata on the given engine."""
    _db.Model.metadata.create_all(engine)


def _reset_resources_to_pre_0011(engine):
    """Drop and recreate the resources table with the pre-0011 schema (no
    hierarchy columns, matching migration 0001). Other tables are untouched."""
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS resources"))
        conn.execute(
            text(
                """
                CREATE TABLE resources (
                    id BLOB PRIMARY KEY,
                    subject_id BLOB NOT NULL REFERENCES subjects(id) ON DELETE RESTRICT,
                    file_id BLOB UNIQUE REFERENCES files(id) ON DELETE SET NULL,
                    uploaded_by BLOB NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                    title VARCHAR(160) NOT NULL,
                    description VARCHAR(2000),
                    resource_type VARCHAR(24) NOT NULL,
                    visibility VARCHAR(16) NOT NULL DEFAULT 'college',
                    external_url VARCHAR(2048),
                    share_token VARCHAR(64),
                    is_published BOOLEAN NOT NULL DEFAULT 1,
                    download_count INTEGER NOT NULL DEFAULT 0,
                    view_count INTEGER NOT NULL DEFAULT 0,
                    deleted_at DATETIME,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT ck_resources_type CHECK (
                        resource_type IN ('note','book','past_paper','slide','link')
                    ),
                    CONSTRAINT ck_resources_visibility CHECK (
                        visibility IN ('section','subject','department','college','private')
                    ),
                    CONSTRAINT ck_resources_title_min_length CHECK (length(title) >= 3)
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX ix_resources_subject_id ON resources (subject_id)"))
        conn.execute(text("CREATE INDEX ix_resources_uploaded_by ON resources (uploaded_by)"))
        conn.execute(text("CREATE INDEX ix_resources_resource_type ON resources (resource_type)"))
        conn.execute(text("CREATE INDEX ix_resources_subject_created ON resources (subject_id, created_at)"))


class TestMigration0011:
    """Upgrade/downgrade round-trip tests for migration 0011."""

    @pytest.fixture
    def db_url(self, tmp_path):
        db_file = tmp_path / "test.db"
        db_file.unlink(missing_ok=True)
        return f"sqlite:///{db_file}"

    def test_downgrade_then_upgrade_round_trip(self, db_url):
        env = _alembic_env(db_url)
        engine = create_engine(db_url)

        _create_all_tables(engine)
        _reset_resources_to_pre_0011(engine)

        _run_alembic(env, "stamp", PREVIOUS_HEAD)

        cols, fks, idxs = _schema_state(engine)
        for c in HIERARCHY_COLUMNS:
            assert c not in cols, f"{c} should not exist before upgrade"
        for fk in FK_NAMES:
            assert fk not in fks, f"{fk} should not exist before upgrade"
        for ix in INDEX_NAMES:
            assert ix not in idxs, f"{ix} should not exist before upgrade"

        # Upgrade to new head: columns/FKs/indexes added.
        _run_alembic(env, "upgrade", NEW_HEAD)
        cols, fks, idxs = _schema_state(engine)
        for c in HIERARCHY_COLUMNS:
            assert c in cols, f"{c} should exist after upgrade"
        for fk in FK_NAMES:
            assert fk in fks, f"{fk} should exist after upgrade"
        for ix in INDEX_NAMES:
            assert ix in idxs, f"{ix} should exist after upgrade"

        fk_map = {fk["name"]: fk for fk in inspect(engine).get_foreign_keys("resources")}
        assert fk_map["fk_resources_department_id"]["referred_table"] == "departments"
        assert fk_map["fk_resources_program_id"]["referred_table"] == "programs"
        assert fk_map["fk_resources_semester_id"]["referred_table"] == "semesters"
        assert fk_map["fk_resources_section_id"]["referred_table"] == "sections"

    def test_downgrade_removes_columns_fks_indexes(self, db_url):
        env = _alembic_env(db_url)
        engine = create_engine(db_url)

        _create_all_tables(engine)
        _reset_resources_to_pre_0011(engine)
        _run_alembic(env, "stamp", PREVIOUS_HEAD)
        _run_alembic(env, "upgrade", NEW_HEAD)

        _run_alembic(env, "downgrade", PREVIOUS_HEAD)

        cols, fks, idxs = _schema_state(engine)
        for c in HIERARCHY_COLUMNS:
            assert c not in cols, f"{c} should be removed after downgrade"
        for fk in FK_NAMES:
            assert fk not in fks, f"{fk} should be removed after downgrade"
        for ix in INDEX_NAMES:
            assert ix not in idxs, f"{ix} should be removed after downgrade"

    def test_upgrade_downgrade_upgrade_triple(self, db_url):
        env = _alembic_env(db_url)
        engine = create_engine(db_url)

        _create_all_tables(engine)
        _reset_resources_to_pre_0011(engine)
        _run_alembic(env, "stamp", PREVIOUS_HEAD)

        _run_alembic(env, "upgrade", NEW_HEAD)
        state1 = _schema_state(engine)

        _run_alembic(env, "downgrade", PREVIOUS_HEAD)
        state2 = _schema_state(engine)
        for c in HIERARCHY_COLUMNS:
            assert c not in state2[0]

        _run_alembic(env, "upgrade", NEW_HEAD)
        state3 = _schema_state(engine)

        assert state1 == state3

    def test_no_model_migration_drift(self, db_url):
        """Build the schema with pre-0011 resources table, upgrade to
        NEW_HEAD, then run Alembic's check command to detect
        model-migration drift.

        The repo's migration chain cannot upgrade from scratch (pre-existing
        0001/0005 overlap on audit_logs.changes), so we build the schema via
        create_all(), reset the resources table to pre-0011 state, stamp to
        0010, upgrade to NEW_HEAD, and let alembic check compare the live
        schema against autogenerated model metadata.
        """
        env = _alembic_env(db_url)
        engine = create_engine(db_url)

        _create_all_tables(engine)
        _reset_resources_to_pre_0011(engine)
        _run_alembic(env, "stamp", PREVIOUS_HEAD)
        _run_alembic(env, "upgrade", NEW_HEAD)

        # Run alembic check: compares the database at head against the
        # current SQLAlchemy model metadata; exits non-zero on drift.
        result = subprocess.run(  # noqa: S603, PLW1510
            [VENV_PYTHON, "-m", "alembic", "check"],
            env=env,
            capture_output=True,
            text=True,
            cwd=BACKEND_DIR,
        )
        assert result.returncode == 0, (
            f"alembic check detected drift (rc={result.returncode})\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
