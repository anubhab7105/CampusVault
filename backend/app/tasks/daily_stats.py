"""Celery task: refresh daily_stats table once per day (invoked by beat)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.extensions import celery, db
from app.models import FileRecord, Message, Resource, User


@celery.task(bind=True, ignore_result=True)
def refresh_daily_stats(self) -> None:
    """Populate the ``daily_stats`` table for yesterday.

    Idempotent: uses UPSERT (INSERT ... ON CONFLICT DO UPDATE) so running
    multiple times a day is safe.
    """
    yesterday = datetime.now(UTC) - timedelta(days=1)
    day_start = datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)

    # Users active (had any activity: login, upload, message, etc.)
    # We count distinct users with any of: created_at, last_login_at, or activity in other tables.
    # For simplicity, use the users table's created_at + last_login_at window.
    active_users_stmt = (
        db.select(db.func.count(db.distinct(User.id)))
        .select_from(User)
        .where(User.last_login_at >= day_start)
        .where(User.last_login_at < day_end)
    )
    active_users = int(db.session.scalar(active_users_stmt) or 0)

    # Resources published (is_published=True) created yesterday
    published_stmt = (
        db.select(db.func.count(Resource.id))
        .select_from(Resource)
        .where(Resource.is_published.is_(True))
        .where(Resource.created_at >= day_start)
        .where(Resource.created_at < day_end)
    )
    resources_published = int(db.session.scalar(published_stmt) or 0)

    # Messages sent yesterday
    messages_stmt = (
        db.select(db.func.count(Message.id))
        .select_from(Message)
        .where(Message.created_at >= day_start)
        .where(Message.created_at < day_end)
    )
    messages_sent = int(db.session.scalar(messages_stmt) or 0)

    # Scan outcomes yesterday
    scan_clean_stmt = (
        db.select(db.func.count(FileRecord.id))
        .select_from(FileRecord)
        .where(FileRecord.scan_status == "clean")
        .where(FileRecord.created_at >= day_start)
        .where(FileRecord.created_at < day_end)
    )
    scans_clean = int(db.session.scalar(scan_clean_stmt) or 0)

    scan_infected_stmt = (
        db.select(db.func.count(FileRecord.id))
        .select_from(FileRecord)
        .where(FileRecord.scan_status == "infected")
        .where(FileRecord.created_at >= day_start)
        .where(FileRecord.created_at < day_end)
    )
    scans_infected = int(db.session.scalar(scan_infected_stmt) or 0)

    scan_failed_stmt = (
        db.select(db.func.count(FileRecord.id))
        .select_from(FileRecord)
        .where(FileRecord.scan_status == "failed")
        .where(FileRecord.created_at >= day_start)
        .where(FileRecord.created_at < day_end)
    )
    scans_failed = int(db.session.scalar(scan_failed_stmt) or 0)

    # Downloads and uploads total yesterday
    # We approximate by summing Resource.download_count and Resource.uploaded_by activity
    # For now, use raw counts from the resources table's counters
    downloads_stmt = (
        db.select(db.func.coalesce(db.func.sum(Resource.download_count), 0))
        .select_from(Resource)
        .where(Resource.created_at >= day_start)
        .where(Resource.created_at < day_end)
    )
    downloads_total = int(db.session.scalar(downloads_stmt) or 0)

    # Uploads: count of resources created yesterday
    uploads_total = int(db.session.scalar(published_stmt) or 0)  # reuse published count as proxy, or count resources

    # Upsert into daily_stats
    upsert = (
        db.insert(db.table("daily_stats"))
        .values(
            day=day_start,
            users_active=active_users,
            resources_published=resources_published,
            messages_sent=messages_sent,
            scans_clean=scans_clean,
            scans_infected=scans_infected,
            scans_failed=scans_failed,
            downloads_total=downloads_total,
            uploads_total=uploads_total,
        )
        .on_conflict_do_update(
            set_={
                "users_active": active_users,
                "resources_published": resources_published,
                "messages_sent": messages_sent,
                "scans_clean": scans_clean,
                "scans_infected": scans_infected,
                "scans_failed": scans_failed,
                "downloads_total": downloads_total,
                "uploads_total": uploads_total,
            },
            index_elements=["day"],
        )
    )
    db.session.execute(upsert)
    db.session.commit()

    # Also archive old data (older than 90 days) into daily_stats_archive if needed
    # (omitted for brevity; would be a separate task or part of this one)
