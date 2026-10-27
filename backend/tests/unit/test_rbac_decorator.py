"""Unit tests — RBAC decorator contract."""

from __future__ import annotations

import pytest

from app.middleware.rbac import permission_required


@pytest.mark.unit
def test_permission_required_allows_held_permission(monkeypatch):
    from flask_jwt_extended import get_jwt

    monkeypatch.setattr(
        "app.middleware.rbac.get_jwt",
        lambda: {"role": "Teacher", "role_permissions": ["library:resource:create"]},
    )
    monkeypatch.setattr(
        "app.middleware.rbac.verify_jwt_in_request", lambda **_: None
    )

    @permission_required("library:resource:create")
    def view():
        return "ok"

    assert view() == "ok"


@pytest.mark.unit
def test_permission_required_all_of_missing_denies():
    from flask_jwt_extended import get_jwt

    current = {"role": "Teacher", "role_permissions": ["library:resource:create"]}

    import app.middleware.rbac as rbac

    rbac_get = get_jwt
    response_holder = {}

    def fake_get_jwt():
        return current

    response_holder["get_jwt"] = fake_get_jwt

    import types

    monkey = types.SimpleNamespace(
        setattr=setattr,
    )

    @permission_required("library:resource:create", "admin:roles:manage")
    def view():
        return "ok"

    # Run inside a fake app request context with flask_jwt_extended patched.
    from flask import Flask

    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = "test"
    with app.test_request_context():
        from unittest.mock import patch

        with (
            patch("app.middleware.rbac.get_jwt", fake_get_jwt),
            patch("app.middleware.rbac.verify_jwt_in_request", lambda **_: None),
        ):
            from app.errors.exceptions import ForbiddenError

            with pytest.raises(ForbiddenError):
                view()


@pytest.mark.unit
def test_permission_required_any_of(monkeypatch):
    import app.middleware.rbac as rbac
    from unittest.mock import patch

    fake = {"role": "Student", "role_permissions": ["chat:message:send"]}

    @rbac.permission_required("library:resource:create", "chat:message:send", any_of=True)
    def view():
        return "granted"

    app_obj = rbac  # namespace reused for patch clarity
    with (
        patch.object(rbac, "get_jwt", lambda: fake),
        patch.object(rbac, "verify_jwt_in_request", lambda **_: None),
    ):
        assert view() == "granted"
