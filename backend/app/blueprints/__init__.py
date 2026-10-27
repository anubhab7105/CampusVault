"""Blueprint registry.

One blueprint per feature (docs/04_BACKEND_GUIDE.md). Controllers here are
thin: parse → validate (schemas) → service call → envelope. Business logic
lives only in services.
"""

from __future__ import annotations

import os
from typing import Any

from flask import Flask

DEFAULT_BLUEPRINTS: tuple[str, ...] = (
    "app.blueprints.health",
    "app.blueprints.auth",
    "app.blueprints.users",
    "app.blueprints.rbac",
    "app.blueprints.academic",
    "app.blueprints.groups",
    "app.blueprints.chat",
    "app.blueprints.library",
    "app.blueprints.files",
    "app.blueprints.notifications",
    "app.blueprints.admin",
    "app.blueprints.audit",
    "app.blueprints.docs",
)


def register_blueprints(app: Flask, overrides: dict[str, Any] | None = None) -> None:
    """Import and register every feature blueprint (url_prefix per folder)."""
    modules = list(DEFAULT_BLUEPRINTS)
    if overrides:
        modules = overrides.get("modules", modules)

    for import_path in modules:
        if os.environ.get("APP_ENV") == "testing" and import_path.endswith("docs"):
            # Swagger docs blueprint stays optional in tests to keep imports light.
            continue
        module = __import__(import_path, fromlist=["bp"])
        app.register_blueprint(module.bp)
