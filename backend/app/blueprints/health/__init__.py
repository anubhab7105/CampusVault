"""Health blueprint — no auth, used by Nginx/Render/CI probes."""

from __future__ import annotations

from flask import Blueprint, current_app

from app.extensions import db
from app.utils.responses import success_response

bp = Blueprint("health", __name__)


@bp.get("/health/live")
def liveness():
    """Process is up — no dependencies probed here."""
    return success_response(
        data={"service": current_app.config["PROJECT_NAME"]},
        message="Alive.",
    )


@bp.get("/health/ready")
def readiness():
    """Dependency probe: database round-trip (fail fast on drift)."""
    db.session.execute(db.text("SELECT 1"))
    return success_response(message="Ready.")
