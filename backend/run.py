"""Local development entrypoint: Flask + Flask-SocketIO on one process.

Usage:
    python3 backend/run.py                 # API + sockets on :8000
    Flask DEBUG reload is driven by config (DevelopmentConfig.DEBUG).
"""

from app import create_app  # noqa: I001
from app.extensions import socketio

app = create_app()

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=8000,
        debug=app.config.get("DEBUG", False),
        allow_unsafe_werkzeug=True,
    )
