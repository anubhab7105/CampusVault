"""pytest fixtures: app factory, database, client, identity helpers."""

from __future__ import annotations

import os

# Test env must be set before importing the app config.
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("APP_SECRET_KEY", "test-app-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")

import pytest  # noqa: E402
from flask import request
from flask.testing import FlaskClient  # noqa: E402
from flask_jwt_extended import verify_jwt_in_request

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


@pytest.fixture
def auth_client(app, client):
    """Test client that optionally verifies JWT on /api/v1/* requests so the
    rate-limit key function can key on user ID (get_jwt_identity) rather than
    falling back to IP for every authenticated route."""
    @app.before_request
    def _verify_jwt_optional_for_rate_limit():
        if request.path.startswith("/api/v1/"):
            try:
                verify_jwt_in_request(optional=True)
            except Exception:
                pass
    return client


@pytest.fixture
def make_jwt_token(app):
    """Factory that returns a signed access token for a given user id/claims."""

    def _make(user_id: str = "00000000-0000-0000-0000-000000000001", role: str = "Student",
              permissions: list[str] | None = None):
        with app.app_context():
            from flask_jwt_extended import create_access_token
            claims = {"role": role, "role_permissions": permissions or []}
            return create_access_token(identity=user_id, additional_claims=claims)
    return _make
