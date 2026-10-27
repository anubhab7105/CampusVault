"""API documentation blueprint.

- GET /api/v1/openapi.json  → machine-readable OpenAPI 3.1 spec
- GET /api/v1/docs          → Swagger UI (served from CDN in development)

The spec is code-defined here (single source of truth for scaffolding) and
will be extended per-endpoint as features land.
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template_string

bp = Blueprint("docs", __name__, url_prefix="/api/v1")

_SWAGGER_UI_TEMPLATE = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CampusVault API — Swagger</title>
    <link rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
  </head>
  <body>
    <div id="swagger"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.onload = () => {
        SwaggerUIBundle({ url: '%(spec_url)s', dom_id: '#swagger' });
      };
    </script>
  </body>
</html>
"""


def _spec() -> dict:
    base = current_app.config["API_PREFIX"]
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "CampusVault API",
            "version": "1.0.0",
            "description": "Academic library + collaboration platform API.",
            "license": {"name": "Internal"},
        },
        "servers": [{"url": "/", "description": "current deployment"}],
        "tags": [
            {"name": "health", "description": "Liveness/readiness probes"},
            {"name": "auth", "description": "Google OAuth (students), email OTP (teachers), JWT lifecycle"},
            {"name": "users", "description": "Profiles and user directory"},
            {"name": "rbac", "description": "Roles, permissions, grants"},
            {"name": "academic", "description": "Department→Program→Semester→Section→Subject"},
            {"name": "groups", "description": "User groups and chat room mirrors"},
            {"name": "chat", "description": "Conversations and messages (REST fallback)"},
            {"name": "library", "description": "Resource catalog"},
            {"name": "files", "description": "Upload metadata + scan pipeline"},
            {"name": "notifications", "description": "Notification stream"},
            {"name": "admin", "description": "Admin console endpoints"},
            {"name": "audit", "description": "Append-only audit trail"},
        ],
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
            },
            "schemas": {
                "SuccessEnvelope": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "const": True},
                        "message": {"type": "string"},
                        "data": {"type": "object"},
                    },
                },
                "ErrorEnvelope": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "const": False},
                        "error": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "message": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
        "paths": {
            f"{base}/health/ready": {
                "get": {"tags": ["health"], "summary": "Readiness probe",
                        "responses": {"200": {"description": "Ready"},
                                      "503": {"description": "Dependency down"}}},
            },
            f"{base}/auth/google/authorize": {
                "get": {"tags": ["auth"], "summary": "Google OAuth authorize URL",
                        "responses": {"200": {"description": "URL + state"}}},
            },
            f"{base}/auth/teachers/otp/request": {
                "post": {"tags": ["auth"], "summary": "Request teacher OTP",
                         "requestBody": {"required": True, "content": {"application/json": {"schema": {
                             "type": "object",
                             "required": ["email"],
                             "properties": {"email": {"type": "string", "format": "email"}}}}}},
                         "responses": {"200": {"description": "Queued"},
                                       "429": {"description": "Rate limited"}}},
            },
            f"{base}/auth/teachers/otp/verify": {
                "post": {"tags": ["auth"], "summary": "Verify OTP → tokens",
                         "requestBody": {"required": True, "content": {"application/json": {"schema": {
                             "type": "object",
                             "required": ["email", "code"],
                             "properties": {"email": {"type": "string"},
                                            "code": {"type": "string", "minLength": 6, "maxLength": 6}}}}}},
                         "responses": {"200": {"description": "Token pair issued"},
                                       "401": {"description": "Invalid code"}}},
            },
            f"{base}/auth/refresh": {
                "post": {"tags": ["auth"], "summary": "Rotate refresh token",
                         "security": [{"bearerAuth": []}],
                         "responses": {"200": {"description": "New token pair"}}},
            },
            f"{base}/library/resources": {
                "get": {"tags": ["library"], "summary": "Browse/search resources",
                        "security": [{"bearerAuth": []}],
                        "parameters": [
                            {"name": "subject_id", "in": "query", "schema": {"type": "string"}},
                            {"name": "q", "in": "query", "schema": {"type": "string"}},
                            {"name": "sort", "in": "query", "schema": {"type": "string"}},
                            {"name": "order", "in": "query", "schema": {"type": "string"}},
                            {"name": "page", "in": "query", "schema": {"type": "integer"}},
                            {"name": "page_size", "in": "query", "schema": {"type": "integer"}},
                        ],
                        "responses": {"200": {"description": "Paged resources"}}},
            },
        },
    }


@bp.get("/openapi.json")
def openapi_json():
    return jsonify(_spec())


@bp.get("/docs")
def swagger_ui():
    spec_url = current_app.config["API_PREFIX"] + "/openapi.json"
    return render_template_string(_SWAGGER_UI_TEMPLATE, spec_url=spec_url)
