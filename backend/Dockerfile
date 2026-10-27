# syntax=docker/dockerfile:1
# CampusVault backend image — Gunicorn + eventlet (Flask-SocketIO capable).

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production

WORKDIR /srv/app

# OS deps: build tools for psycopg/bcrypt wheels are cached via pip; curl
# exists for the container healthcheck below.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements/ ./requirements/
RUN pip install --upgrade pip && pip install -r requirements/prod.txt

COPY . .

# Non-root runtime user.
RUN useradd --create-home --shell /usr/sbin/nologin campusvault \
 && chown -R campusvault:campusvault /srv/app
USER campusvault

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health/live || exit 1

# Single SocketIO-aware worker per container; scale by replicas + Redis queue.
CMD ["gunicorn", "wsgi:app", "-c", "gunicorn.conf.py"]
