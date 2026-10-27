"""pytest fixtures: app factory, database, client, identity helpers."""

from __future__ import annotations

import os

# Test env must be set before importing the app config.
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("APP_SECRET_KEY", "test-app-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")

import pytest  # noqa: E402
from flask.testing import FlaskClient  # noqa: E402

from app import create_app  # noqa: E402
from app import models as all_models  # noqa: E402,F401 — entity registration
from app.extensions import db as _db  # noqa: E402


@pytest.fixture()
def app():
    """App under test: in-memory SQLite, no network I/O."""
    app = create_app()
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture()
def client(app) -> FlaskClient:
    return app.test_client()


@pytest.fixture()
def db():  # convenience re-export
    return _db
