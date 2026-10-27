"""Single registry for Flask extensions.

Instances are created here at import time and bound to the app inside the
factory. Blueprints, middleware and services import the extension objects —
never re-create them — so exactly one cycle exists (DRY).
"""

from __future__ import annotations

from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

# --- ORM / migrations -------------------------------------------------------- #
db = SQLAlchemy()
migrate = Migrate()

# --- Auth --------------------------------------------------------------------- #
jwt = JWTManager()

# --- Security headers / CORS --------------------------------------------------- #
cors = CORS()

# --- Rate limiting -------------------------------------------------------------- #
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379/1",  # overridden from config in factory
)

# --- Email (Gmail SMTP, development only) ----------------------------------------- #
mail = Mail()

# --- Real-time ---------------------------------------------------------------------- #
# async_mode eventlet: matches Gunicorn worker class in production.
socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode="eventlet",
    logger=False,
    engineio_logger=False,
)
