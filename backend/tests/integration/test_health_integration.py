"""Integration tests — health endpoints + request envelope over HTTP."""

from __future__ import annotations

import pytest


@pytest.mark.integration
class TestHealthEndpoints:
    def test_liveness_returns_envelope(self, client):
        response = client.get("/health/live")
        body = response.get_json()
        assert response.status_code == 200
        assert body["success"] is True
        assert body["data"]["service"] == "CampusVault"

    def test_readiness_probes_database(self, app, client):
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.get_json()["success"] is True

    def test_unknown_route_is_normalized_envelope(self, client):
        response = client.get("/api/v1/definitely-not-here")
        body = response.get_json()
        assert response.status_code == 404
        assert body["success"] is False
        assert "NOT_FOUND" in body["error"]["code"]


@pytest.mark.integration
class TestSecurityHeaders:
    def test_headers_present_on_every_response(self, client):
        response = client.get("/health/live")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "Content-Security-Policy" in response.headers
        assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.integration
class TestProtectedEndpoints:
    def test_requires_jwt(self, client):
        response = client.get("/api/v1/users/me")
        body = response.get_json()
        assert response.status_code == 401
        assert body["success"] is False
        assert body["error"]["code"] == "UNAUTHORIZED"
