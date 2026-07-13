"""
Shared pytest fixtures. Per 10_TESTING_GUIDE.md: "Database fixtures" against
a real Postgres instance (not SQLite) — the models use Postgres-specific
types (CITEXT, INET, JSONB), so a real Postgres test DB is required for
fidelity, matching 03_DATABASE_GUIDE.md's locked database choice.

Requires a running Postgres with a `campusvault_test` database and the
`citext` / `pgcrypto` extensions enabled. Connection string overridable via
TEST_DATABASE_URL env var.
"""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/campusvault_test"
)


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL)
    with eng.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        conn.commit()
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def db(engine) -> Session:
    """
    Fresh, isolated session per test: wraps the test in an outer transaction
    that's always rolled back, so tests never leak state into each other
    regardless of commits the code under test performs.
    """
    connection = engine.connect()
    outer_txn = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    # Nested savepoint so that `session.commit()` calls inside service code
    # (which we deliberately don't mock, to test real behavior) don't end
    # the outer transaction early.
    session.begin_nested()

    from sqlalchemy import event

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    yield session

    session.close()
    outer_txn.rollback()
    connection.close()
