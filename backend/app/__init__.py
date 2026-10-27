"""CampusVault application package.

`create_app()` is the single production entrypoint. It is used by:
- backend/wsgi.py (Gunicorn, production)
- the SocketIO dev server (development)
- backend/tests/conftest.py (Flask test client)

Request flow: Client → Middleware → Blueprint → Validation → Service →
Repository → Database → Response (docs/04_BACKEND_GUIDE.md).
"""

from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Any

from flask import Flask

import app.config as config_module


def _configure_logging(app: Flask) -> None:
    """Single-line application logs; log level from config only."""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt="%(asctime)s %(levelname)s %(name)s — %(message)s"))
    app.logger.handlers = [handler]
    app.logger.setLevel(app.config.get("LOG_LEVEL", logging.INFO))


def create_app(
    config_object: type[config_module.BaseConfig] | None = None,
    blueprint_overrides: dict[str, Any] | None = None,  # reserved for tests
) -> Flask:
    """Build and wire the Flask application.

    Args:
        config_object: Config class to load. Defaults to the environment
            selected by ``APP_ENV`` (development/staging/production/testing).
        blueprint_overrides: Reserved hook for test blueprints; the factory
            keeps registering the standard blueprints when omitted.
    """
    env_name = os.environ.get("APP_ENV", config_module.DEVELOPMENT)
    selected = config_object or config_module.CONFIG_BY_ENV.get(env_name, config_module.DevelopmentConfig)

    app = Flask(__name__)
    app.config.from_object(selected)

    # Fail fast on missing secrets — never silently fall back in production.
    for key in selected.environ_required():
        if not app.config.get(key):
            raise config_module.ConfigError(
                f"{key} is required for APP_ENV={app.config.get('ENV', env_name)}"
            )

    # ----- extensions -------------------------------------------------------- #
    from app.extensions import cors, db, jwt, limiter, mail, migrate, socketio

    app.config.setdefault("SQLALCHEMY_DATABASE_URI", selected.database_url())
    app.config.update(
        # JWT tombstone: derive access/refresh expiry here so config.py stays declarative.
        JWT_SECRET_KEY=app.config["JWT_SECRET_KEY"],
        JWT_ACCESS_TOKEN_EXPIRES=dt.timedelta(minutes=app.config["JWT_ACCESS_TOKEN_MINUTES"]),
        JWT_REFRESH_TOKEN_EXPIRES=dt.timedelta(days=app.config["JWT_REFRESH_TOKEN_DAYS"]),
    )

    db.init_app(app)
    migrate.init_app(app, db, compare_type=True)
    jwt.init_app(app)
    from app.middleware.auth import register_jwt_blocklist

    register_jwt_blocklist(jwt)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=False,
    )
    limiter.init_app(app)
    mail.init_app(app)

    # ----- errors → middleware → models → blueprints → sockets ---------------- #
    from app import models as _models  # noqa: F401 — ORM entity registration
    from app.blueprints import register_blueprints
    from app.errors.handlers import register_error_handlers
    from app.middleware import register_middleware
    from app.sockets import init_socketio

    register_error_handlers(app)
    register_middleware(app)
    register_blueprints(app, blueprint_overrides or {})
    init_socketio(app, socketio)

    _configure_logging(app)
    app.logger.info("CampusVault initialized. env=%s", app.config["ENV"])
    return app
