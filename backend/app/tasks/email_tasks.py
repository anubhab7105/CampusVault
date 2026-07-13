"""
Email-sending Celery tasks. Per 04_BACKEND_GUIDE.md/Deployment Guide,
outbound email is async so request handlers never block on SMTP.

Gmail SMTP is the dev-environment provider per the README's locked stack.
Actual Celery app wiring (broker URL, task registration) happens in the
app factory / celery_app.py once the DevOps setup is built — this file
defines the task contract now so app/services/auth_service.py has a
stable import target.
"""
import logging
import smtplib
from email.message import EmailMessage

from app.celery_app import celery_app  # created during app factory setup

logger = logging.getLogger("campusvault.tasks")


@celery_app.task(name="email.send_otp", max_retries=3, default_retry_delay=30)
def send_otp_email(to_email: str, code: str) -> None:
    """
    Sends the OTP code via Gmail SMTP (dev) / configured SMTP provider (prod).
    SMTP credentials come from environment variables — never hardcoded, per
    04_BACKEND_GUIDE.md's "no hardcoded secrets" rule.
    """
    import os

    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]

    msg = EmailMessage()
    msg["Subject"] = "Your CampusVault verification code"
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content(f"Your CampusVault verification code is: {code}\nIt expires in 10 minutes.")

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except Exception:
        logger.exception("Failed to send OTP email to %s", to_email)
        raise
