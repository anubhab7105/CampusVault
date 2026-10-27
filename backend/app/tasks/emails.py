"""Email delivery tasks (OTP codes, welcome mail). Queued only."""

from __future__ import annotations

from celery import shared_task


@shared_task(
    name="app.tasks.emails.send_otp_email",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_otp_email(self, *, to: str, code: str, ttl_minutes: int) -> str:
    """Deliver the teacher OTP. Retries the SMTP hiccup then gives up."""
    try:
        from app.services.email_service import email_service

        email_service.send_otp(to=to, code=code, ttl_minutes=ttl_minutes)
        return "sent"
    except Exception:  # noqa: BLE001 — tasks log and re-raise via autoretry
        raise


@shared_task(
    name="app.tasks.emails.send_welcome_email",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_welcome_email(self, *, to: str, name: str) -> str:
    from app.services.email_service import email_service

    email_service.send_welcome(to=to, name=name)
    return "sent"
