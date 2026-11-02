"""Tests for migration 0011: add academic hierarchy FKs to Resource.

These tests exercise the Alembic migration in isolation (upgrade/downgrade
round trips, backfill of existing rows) on a file-based SQLite database so
that connections share the same schema.
"""

from __future__ import annotations

import uuid

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

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
    db_file = tmp_path / "test.db"
    db_file.unlink(missing_ok=True)
    import os

    os.environ["APP_ENV"] = "testing"
    os.environ["APP_SECRET_KEY"] = "test-secret"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
    os.environ["TEST_DATABASE_URL"] = f"sqlite:///{db_file}"
    app = create_app()
    return app, db_file


def _alembic_config():
    return Config("alembic.ini")


def _drop_hierarchy_objects(session):
    """Recreate the resources table without the 0011 columns/FKs/indexes.

    SQLite cannot drop a column that participates in a foreign key, so we
    drop and recreate the resources table using the pre-0011 schema (matching
    migration 0001). All other tables are untouched.
    """
    session.execute(text("DROP TABLE IF EXISTS resources"))
    session.execute(
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
                CONSTRAINT ck_resources_type CHECK (resource_type IN ('note','book','past_paper','slide','link')),
                CONSTRAINT ck_resources_visibility CHECK (visibility IN ('section','subject','department','college','private')),
                CONSTRAINT ck_resources_title_min_length CHECK (length(title) >= 3)
            )
            """
        )
    )
    session.execute(text("CREATE INDEX ix_resources_subject_id ON resources (subject_id)"))
    session.execute(text("CREATE INDEX ix_resources_uploaded_by ON resources (uploaded_by)"))
    session.execute(text("CREATE INDEX ix_resources_resource_type ON resources (resource_type)"))
    session.execute(text("CREATE INDEX ix_resources_subject_created ON resources (subject_id, created_at)"))
    session.commit()


def _schema_state(engine):
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("resources")}
    fks = {fk["name"] for fk in insp.get_foreign_keys("resources") if fk["name"]}
    idxs = {ix["name"] for ix in insp.get_indexes("resources")}
    return cols, fks, idxs


def _insert_hierarchy_and_resource(session):
    """Insert a full department→program→semester→section→subject chain and a
    resource referencing the subject. Returns the resource row id."""
    dept_id = uuid.uuid4()
    prog_id = uuid.uuid4()
    sem_id = uuid.uuid4()
    sec_id = uuid.uuid4()
    subj_id = uuid.uuid4()
    user_id = uuid.uuid4()
    res_id = uuid.uuid4()

    session.execute(
        text(
            "INSERT INTO departments (id, name, code, created_at, updated_at) "
            "VALUES (:id,'Computer Science','CS', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": str(dept_id)},
    )
    session.execute(
        text(
            "INSERT INTO programs (id, department_id, name, code, created_at, updated_at) "
            "VALUES (:id,:dept,'B.Tech CS','BTCS', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": str(prog_id), "dept": str(dept_id)},
    )
    session.execute(
        text(
            "INSERT INTO semesters (id, program_id, number, created_at, updated_at) "
            "VALUES (:id,:prog,1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": str(sem_id), "prog": str(prog_id)},
    )
    session.execute(
        text(
            "INSERT INTO sections (id, semester_id, name, created_at, updated_at) "
            "VALUES (:id,:sem,'A', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": str(sec_id), "sem": str(sem_id)},
    )
    session.execute(
        text(
            "INSERT INTO subjects (id, semester_id, name, code, created_at, updated_at) "
            "VALUES (:id,:sem,'Data Structures','DS101', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": str(subj_id), "sem": str(sem_id)},
    )
    session.execute(
        text(
            "INSERT INTO users (id, email, full_name, auth_provider, created_at, updated_at) "
            "VALUES (:id,'a@b.c','User','otp', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": str(user_id)},
    )
    session.execute(
        text(
            "INSERT INTO resources (id, subject_id, uploaded_by, title, resource_type, "
            "visibility, created_at, updated_at) VALUES (:id,:subj,:user,'Test "
            "Resource','note','college', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": str(res_id), "subj": str(subj_id), "user": str(user_id)},
    )
    session.commit()
    return str(res_id), str(dept_id), str(prog_id), str(sem_id), str(sec_id)


class TestMigration0011:
    """Upgrade/downgrade + backfill tests for migration 0011."""

    def test_clean_upgrade_adds_columns_fks_indexes(self, tmp_path):
        app, _ = _make_app(tmp_path)
        with app.app_context():
            _db.create_all()
            _drop_hierarchy_objects(_db.session)
            command.stamp(_alembic_config(), PREVIOUS_HEAD)

            cols, fks, idxs = _schema_state(_db.engine)
            for c in HIERARCHY_COLUMNS:
                assert c not in cols, f"{c} should not exist before upgrade"
            for fk in FK_NAMES:
                assert fk not in fks, f"{fk} should not exist before upgrade"
            for ix in INDEX_NAMES:
                assert ix not in idxs, f"{ix} should not exist before upgrade"

            command.upgrade(_alembic_config(), NEW_HEAD)

            cols, fks, idxs = _schema_state(_db.engine)
            for c in HIERARCHY_COLUMNS:
                assert c in cols, f"{c} should exist after upgrade"
            for fk in FK_NAMES:
                assert fk in fks, f"{fk} should exist after upgrade"
            for ix in INDEX_NAMES:
                assert ix in idxs, f"{ix} should exist after upgrade"

            # Verify FK targets
            insp = inspect(_db.engine)
            fk_map = {fk["name"]: fk for fk in insp.get_foreign_keys("resources")}
            assert fk_map["fk_resources_department_id"]["referred_table"] == "departments"
            assert fk_map["fk_resources_program_id"]["referred_table"] == "programs"
            assert fk_map["fk_resources_semester_id"]["referred_table"] == "semesters"
            assert fk_map["fk_resources_section_id"]["referred_table"] == "sections"

    def test_upgrade_backfills_existing_rows(self, tmp_path):
        app, _ = _make_app(tmp_path)
        with app.app_context():
            _db.create_all()
            _drop_hierarchy_objects(_db.session)
            command.stamp(_alembic_config(), PREVIOUS_HEAD)

            res_id, dept_id, prog_id, sem_id, sec_id = _insert_hierarchy_and_resource(
                _db.session
            )

            command.upgrade(_alembic_config(), NEW_HEAD)

            rows = _db.session.execute(
                text(
                    "SELECT department_id, program_id, semester_id, section_id "
                    "FROM resources WHERE id = :rid"
                ),
                {"rid": res_id},
            ).fetchone()
            assert rows is not None
            assert str(rows.department_id) == dept_id
            assert str(rows.program_id) == prog_id
            assert str(rows.semester_id) == sem_id
            # section_id is not derivable from subject, stays NULL
            assert rows.section_id is None

    def test_downgrade_removes_columns_fks_indexes(self, tmp_path):
        app, _ = _make_app(tmp_path)
        with app.app_context():
            _db.create_all()
            _drop_hierarchy_objects(_db.session)
            command.stamp(_alembic_config(), PREVIOUS_HEAD)
            command.upgrade(_alembic_config(), NEW_HEAD)

            command.downgrade(_alembic_config(), PREVIOUS_HEAD)

            cols, fks, idxs = _schema_state(_db.engine)
            for c in HIERARCHY_COLUMNS:
                assert c not in cols, f"{c} should be removed after downgrade"
            for fk in FK_NAMES:
                assert fk not in fks, f"{fk} should be removed after downgrade"
            for ix in INDEX_NAMES:
                assert ix not in idxs, f"{ix} should be removed after downgrade"

    def test_upgrade_downgrade_upgrade_round_trip(self, tmp_path):
        app, _ = _make_app(tmp_path)
        with app.app_context():
            _db.create_all()
            _drop_hierarchy_objects(_db.session)
            command.stamp(_alembic_config(), PREVIOUS_HEAD)
            res_id, *_ = _insert_hierarchy_and_resource(_db.session)

            command.upgrade(_alembic_config(), NEW_HEAD)
            rows = _db.session.execute(
                text("SELECT department_id FROM resources WHERE id = :rid"),
                {"rid": res_id},
            ).fetchone()
            assert rows.department_id is not None

            command.downgrade(_alembic_config(), PREVIOUS_HEAD)
            cols, _, _ = _schema_state(_db.engine)
            assert "department_id" not in cols

            command.upgrade(_alembic_config(), NEW_HEAD)
            cols, _, _ = _schema_state(_db.engine)
            assert "department_id" in cols
            rows2 = _db.session.execute(
                text("SELECT department_id FROM resources WHERE id = :rid"),
                {"rid": res_id},
            ).fetchone()
            assert rows2.department_id is not None
