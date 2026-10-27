"""Unit tests — response envelope contract (docs/08_API_GUIDE.md)."""

from __future__ import annotations

import pytest
from flask import Flask

from app.utils.responses import error_response, success_response


@pytest.fixture()
def flask_scope():
    app = Flask(__name__)
    app.config["TESTING"] = True
    with app.app_context():
        yield app


@pytest.mark.unit
@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"hello": "world"}, 200),
        ({}, 201),
        ({"nested": {"a": 1}}, 204),
    ],
)
def test_success_envelope(payload, status, flask_scope):
    response = success_response(data=payload, message="Done.", status_code=status)
    body = response.get_json()
    assert response.status_code == status
    assert body["success"] is True
    assert body["message"] == "Done."
    assert body["data"] == payload


@pytest.mark.unit
@pytest.mark.parametrize(
    ("code", "status"),
    [("VALIDATION_ERROR", 400), ("INTERNAL_ERROR", 500), ("NOT_FOUND", 404)],
)
def test_error_envelope(code, status, flask_scope):
    response = error_response(code, "Something failed.", status_code=status)
    body = response.get_json()
    assert response.status_code == status
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert body["error"]["message"] == "Something failed."


@pytest.mark.unit
def test_error_details_round_trip(flask_scope):
    response = error_response("VALIDATION_ERROR", "Bad.", status_code=400, details={"f": ["x"]})
    assert response.get_json()["error"]["details"] == {"f": ["x"]}


@pytest.mark.unit
def test_paging_meta_bounds():
    from app.utils.pagination import PagingMeta

    meta = PagingMeta(page=2, page_size=10, total=25).as_dict()
    assert meta["total_pages"] == 3
    assert meta["has_next"] is True
    assert meta["has_prev"] is True
