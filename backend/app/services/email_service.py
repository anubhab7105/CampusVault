"""Email delivery via Flask-Mail (Gmail SMTP — development only).

Production sends through a transactional provider; the interface below stays
stable, so only the backend of `send` changes. Every send is queued through
Celery in app/tasks/emails.py — never called inline from a request handler.
"""

from __future__ import annotations

from flask import current_app, render_template_string
from flask_mail import Message

from app.extensions import mail


class EmailService:
    sender: str | None = None

    @classmethod
    def send(cls, to: str, subject: str, body: str, html: str | None = None) -> None:
        """Synchronous send — call from Celery tasks, not request handlers."""
        sender = cls.sender or current_app.config.get("EMAIL_SENDER") or None
        message = Message(subject=subject, recipients=[to], body=body, html=html, sender=sender)
        mail.send(message)

    @classmethod
    def send_otp(cls, to: str, code: str, ttl_minutes: int) -> None:
        html = render_template_string(
            "<p>Your CampusVault verification code is "
            "<strong style='font-size:20px'>{{ code }}</strong>. "
            "It expires in {{ ttl_minutes }} minutes.</p>",
            code=code,
            ttl_minutes=ttl_minutes,
        )
        cls.send(
            to=to,
            subject="CampusVault verification code",
            body=f"Your CampusVault verification code is {code} (valid {ttl_minutes} minutes).",
            html=html,
        )

    @classmethod
    def send_welcome(cls, to: str, name: str) -> None:
        cls.send(
            to=to,
            subject="Welcome to CampusVault",
            body=f"Hi {name}, welcome to CampusVault! Your account is ready.",
        )


email_service = EmailService()
