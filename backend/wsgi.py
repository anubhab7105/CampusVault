"""Gunicorn entrypoint (production).

Run with the eventlet worker class (see gunicorn.conf.py) so Flask-SocketIO
serves WebSocket connections inside the same worker pool.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Dev-only fallback; production uses `gunicorn wsgi:app`.
    app.run(host="0.0.0.0", port=8000, debug=True)  # noqa: S104
