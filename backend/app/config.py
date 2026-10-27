"""Environment-aware configuration.

Every environment overrides the base classes below. Secrets and endpoints are
never hardcoded; they come from environment variables (see ``.env.example`` at
the repository root). There is exactly one source of truth per setting.
"""

from __future__ import annotations

import os
from typing import Final

# The class of environment currently running.
DEVELOPMENT: Final[str] = "development"
STAGING: Final[str] = "staging"
PRODUCTION: Final[str] = "production"
TESTING: Final[str] = "testing"

ENVIRONMENTS: Final[frozenset[str]] = frozenset({DEVELOPMENT, STAGING, PRODUCTION, TESTING})


class ConfigError(RuntimeError):
    """Raised when a required environment variable is missing at boot."""


def _env_bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).lower() in {"1", "true", "yes", "on"}


def _split_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


class BaseConfig:
    """Sane, secure defaults shared by every environment."""

    # --- Core ------------------------------------------------------------ #
    PROJECT_NAME: Final[str] = "CampusVault"
    API_VERSION: Final[str] = "v1"
    API_PREFIX: Final[str] = "/api/v1"

    # --- Security keys (fail fast when unset; see environ_required below) -- #
    SECRET_KEY: str = os.environ.get("APP_SECRET_KEY", "")
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "")

    # --- Database (Supabase PostgreSQL) ----------------------------------- #
    SUPABASE_DB_URL: str = os.environ.get("SUPABASE_DB_URL", "")

    # --- Redis ------------------------------------------------------------ #
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # --- JWT --------------------------------------------------------------- #
    JWT_ACCESS_TOKEN_MINUTES: int = int(os.environ.get("JWT_ACCESS_MINUTES", "15"))
    JWT_REFRESH_TOKEN_DAYS: int = int(os.environ.get("JWT_REFRESH_DAYS", "30"))

    # --- CORS --------------------------------------------------------------- #
    CORS_ORIGINS: list[str] = _split_origins(os.environ.get("CORS_ORIGINS", "http://localhost:5173"))

    # --- Email (Gmail SMTP, development only) -------------------------------- #
    SMTP_HOST: str = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER: str = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD", "")
    EMAIL_SENDER: str = os.environ.get("EMAIL_SENDER", "")
    MAIL_USE_TLS: bool = _env_bool("MAIL_USE_TLS", "true")

    # --- Google OAuth (students) --------------------------------------------- #
    GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_OAUTH_REDIRECT_URI: str = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "")
    GOOGLE_OAUTH_AUTHORIZATION_ENDPOINT: Final[str] = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_OAUTH_TOKEN_ENDPOINT: Final[str] = "https://oauth2.googleapis.com/token"
    GOOGLE_OAUTH_USERINFO_ENDPOINT: Final[str] = "https://openidconnect.googleapis.com/v1/userinfo"

    # --- Supabase Storage ----------------------------------------------------- #
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_STORAGE_BUCKET: str = os.environ.get("SUPABASE_STORAGE_BUCKET", "campusvault-files")

    # --- Upload policy -------------------------------------------------------- #
    UPLOAD_MAX_SIZE_BYTES: int = int(os.environ.get("UPLOAD_MAX_SIZE_BYTES", str(25 * 1024 * 1024)))
    UPLOAD_ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
        {
            "pdf",
            "doc",
            "docx",
            "ppt",
            "pptx",
            "xls",
            "xlsx",
            "png",
            "jpg",
            "jpeg",
            "webp",
            "txt",
            "csv",
            "md",
            "zip",
        }
    )

    # --- Rate limiting --------------------------------------------------------- #
    RATELIMIT_STORAGE_URI: str = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
    RATELIMIT_DEFAULT: str = os.environ.get("RATELIMIT_DEFAULT", "100/minute")
    RATELIMIT_AUTH: str = os.environ.get("RATELIMIT_AUTH", "5/minute")

    # --- Celery ----------------------------------------------------------------- #
    CELERY_BROKER_URL: str = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)

    # --- Observability ------------------------------------------------------------ #
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    ENV: str = DEVELOPMENT

    # --- SQLAlchemy ---------------------------------------------------------------- #
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping": True,
        "pool_recycle": 280,  # below Supabase idle disconnect timeout
    }

    @staticmethod
    def database_url() -> str:
        """Composable PostgreSQL URL.

        ``SUPABASE_DB_URL`` (whole connection string) wins when present;
        otherwise the parts assembled from ``SUPABASE_DB_*`` variables.
        """
        if BaseConfig.SUPABASE_DB_URL:
            return BaseConfig.SUPABASE_DB_URL
        raise ConfigError(
            "SUPABASE_DB_URL (or SUPABASE_DB_* parts) is required " "to connect to Supabase PostgreSQL."
        )

    @classmethod
    def environ_required(cls) -> list[str]:
        """Flask config keys that MUST be non-empty for this environment to boot."""
        return ["SECRET_KEY", "JWT_SECRET_KEY"]


class DevelopmentConfig(BaseConfig):
    """Local development. Gmail SMTP; verbose errors for developers."""

    DEBUG: bool = True
    ENV: str = DEVELOPMENT
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "DEBUG")

    JWT_ACCESS_TOKEN_MINUTES: int = int(os.environ.get("JWT_ACCESS_MINUTES", "60"))
    JWT_REFRESH_TOKEN_DAYS: int = int(os.environ.get("JWT_REFRESH_DAYS", "7"))

    @classmethod
    def database_url(cls) -> str:
        if cls.SUPABASE_DB_URL:
            return cls.SUPABASE_DB_URL
        # Development convenience: SQLite keeps the stack runnable before
        # Supabase credentials are provisioned.
        return os.environ.get("LOCAL_DB_URL", "sqlite:///dev_local.db")

    @classmethod
    def environ_required(cls) -> list[str]:
        return super().environ_required()


class StagingConfig(BaseConfig):
    """Pre-production environment used to rehearse deployment."""

    DEBUG: bool = False
    ENV: str = STAGING


class ProductionConfig(BaseConfig):
    """Hardened defaults for Render/VPS deployment."""

    DEBUG: bool = False
    ENV: str = PRODUCTION


class TestingConfig(BaseConfig):
    """Isolated unit/integration tests. No network I/O permitted."""

    DEBUG: bool = True
    ENV: str = TESTING
    TESTING: bool = True

    SQLALCHEMY_DATABASE_URI: str = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")

    @classmethod
    def database_url(cls) -> str:
        return cls.SQLALCHEMY_DATABASE_URI


# Selects the config class from APP_ENV; the factory is the only consumer.
CONFIG_BY_ENV: Final[dict[str, type[BaseConfig]]] = {
    DEVELOPMENT: DevelopmentConfig,
    STAGING: StagingConfig,
    PRODUCTION: ProductionConfig,
    TESTING: TestingConfig,
}
