"""Gunicorn production configuration.

Workers: eventlet — required so Flask-SocketIO/Engine.IO timelines hold
WebSockets open without blocking. One worker per process; scale horizontally
with the Redis message queue (flask_socketio message_queue) documented in
docs/07_SOCKET_GUIDE.md.
"""

import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "eventlet")
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
keepalive = 65  # above Nginx proxy_read timeout to avoid WS teardown races

# Access/error logs to stdout (the container's log collector pick these up).
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
access_log_format = '%(h)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(M)sms "%(a)s"'

# Retry on boot failures (Render/RDS cold-start flakiness).
preload_app = False
