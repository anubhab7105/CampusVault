"""Socket.IO wiring (Redis adapter + JWT handshake).

Deployment model:
- development: single Flask dev process
- production: gunicorn eventlet workers; SocketIO scale-out needs
  `message_queue=<redis>` so every worker receives every event
"""

from __future__ import annotations

from flask import Flask
from flask_socketio import SocketIO


def init_socketio(app: Flask, socketio: SocketIO) -> None:
    """Bind SocketIO to the app and load all event modules exactly once."""
    socketio.init_app(
        app,
        cors_allowed_origins=app.config.get("CORS_ORIGINS", []),
        message_queue=app.config.get("REDIS_URL"),
        logger=app.debug,
        engineio_logger=app.debug,
    )

    # Import-time registration of handlers (they attach to `socketio`).
    from app.sockets import connection, events, handlers  # noqa: F401
