"""
Celery app instance. Minimal stub — full config (broker/backend URLs from
Redis, task routing, beat schedule if needed) gets fleshed out during the
DevOps/Deployment implementation step (11_DEPLOYMENT_GUIDE.md /
21_DEVOPS_GUIDE.md), not here. This exists now so task modules
(app/tasks/*.py) have a stable `celery_app` to register against.
"""
import os

from celery import Celery

celery_app = Celery(
    "campusvault",
    broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
