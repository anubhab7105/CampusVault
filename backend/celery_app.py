"""Celery application (Redis broker + Redis result backend).

Canonical usage:
- workers:      celery -A celery_app.celery_app worker -l info
- beat (later): celery -A celery_app.celery_app beat -l info

The factory is deliberately lightweight: Celery tasks import create_app() so
each worker has a full app context (same config sources, no duplication).
"""

from __future__ import annotations

from celery import Celery

from app.config import CONFIG_BY_ENV


def _resolve_broker() -> str:
    import os

    return os.environ.get(
        "CELERY_BROKER_URL",
        CONFIG_BY_ENV[os.environ.get("APP_ENV", "development")].CELERY_BROKER_URL,
    )


celery_app = Celery(
    "campusvault",
    broker=_resolve_broker(),
    backend=_resolve_broker(),
    include=[
        "app.tasks.emails",
        "app.tasks.malware_scan",
        "app.tasks.offline_notifications",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,            # survive worker crashes (reliability first)
    worker_prefetch_multiplier=1,   # fair distribution for slow scans
    timezone="UTC",
    enable_utc=True,
    task_time_limit=600,
    task_soft_time_limit=540,
)


def flask_app():
    """One app context per worker process, shared by tasks."""
    from app import create_app

    return create_app()


# Task base with app context (standard Flask/Celery bridge).
from celery import shared_task  # noqa: E402


@shared_task(name="app.ping")
def ping() -> str:
    """Liveness probe used by deployment health checks."""
    return "pong"
