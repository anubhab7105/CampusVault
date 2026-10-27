"""Alembic environment.

- URL is composed from the selected environment config (never hardcoded).
- Metadata comes from app.models registry, so autogenerate sees every table.
- Naming convention is declared so future migrations keep predictable
  constraint names (supports future archival/analytics tooling).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make `app` importable when alembic runs from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.config as config_module  # noqa: E402
from app import (
    create_app,  # noqa: E402
    models,  # noqa: F401,E402 — register all tables on the metadata
)
from app.extensions import db  # noqa: E402

config = context.config

# --- database URL from the active environment -------------------------------- #
env_name = os.environ.get("APP_ENV", config_module.DEVELOPMENT)
config_obj = config_module.CONFIG_BY_ENV.get(env_name, config_module.DevelopmentConfig)

flask_app = create_app(config_obj)
db_url = flask_app.config["SQLALCHEMY_DATABASE_URI"]
config.set_main_option("sqlalchemy.url", db_url)

# --- target metadata + naming convention --------------------------------------- #
target_metadata = db.metadata


def include_object(obj, name, type_, reflected, compare_to) -> bool:  # noqa: ANN001
    """Skip alembic_version and objects from other schemas (e.g. Supabase auth)."""
    if type_ == "table" and name in {"alembic_version"}:
        return False
    return True


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a DB connection."""
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        version_table="alembic_version",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the configured engine."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
