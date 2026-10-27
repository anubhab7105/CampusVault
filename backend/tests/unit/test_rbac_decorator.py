"""Unit tests — RBAC decorator contract."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from flask import Flask

from app.errors.exceptions import ForbiddenError
from app.middleware.rbac import permission_required


@pytest.fixture()
def claims_app():
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = "test"
    with app.test_request_context():
        yield app


def _patch_claims(claims: dict[str, Any]):
    return (
        patch("app.middleware.rbac.get_jwt", lambda: claims),
        patch("app.middleware.rbac.verify_jwt_in_request", lambda **_: None),
    )


@pytest.mark.unit
def test_allows_held_permission(claims_app):
    claims = {"role": "Teacher", "role_permissions": ["library:resource:create"]}

    @permission_required("library:resource:create")
    def view():
        return "ok"

    patches = _patch_claims(claims)
    with patches[0], patches[1]:
        assert view() == "ok"


@pytest.mark.unit
def test_denies_missing_permission(claims_app):
    claims = {"role": "Teacher", "role_permissions": ["library:resource:create"]}

    @permission_required("library:resource:create", "admin:roles:manage")
    def view():
        return "ok"

    patches = _patch_claims(claims)
    with patches[0], patches[1]:
        with pytest.raises(ForbiddenError):
            view()


@pytest.mark.unit
def test_any_of_grants_when_one_matches(claims_app):
    claims = {"role": "Student", "role_permissions": ["chat:message:send"]}

    @permission_required("library:resource:create", "chat:message:send", any_of=True)
    def view():
        return "granted"

    patches = _patch_claims(claims)
    with patches[0], patches[1]:
        assert view() == "granted"


@pytest.mark.unit
def test_empty_permissions_denies(claims_app):
    claims = {"role": "Student", "role_permissions": []}

    @permission_required("chat:message:send", any_of=True)
    def view():
        return "ok"

    patches = _patch_claims(claims)
    with patches[0], patches[1]:
        with pytest.raises(ForbiddenError):
            view()
