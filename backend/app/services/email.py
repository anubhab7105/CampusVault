#!/usr/bin/env python3
"""
send_credentials.py

Usage:
  - Set environment variable CAMPUSVAULT_EMAIL (optional, defaults to campusvault.official@gmail.com)
  - Set environment variable CAMPUSVAULT_APP_PASSWORD to the Gmail app password (recommended),
    or enter it when prompted.
  - Run: python send_credentials.py

This script will:
  1. generate a unique id for the user (prefix 'F' or 'S'),
  2. compose a plain + HTML email including the user's password, the unique id, and a message,
  3. send the email via Gmail SMTP (smtp.gmail.com:587).
"""

import os
import secrets
import string
import smtplib
from email.message import EmailMessage
import getpass

SENDER_DEFAULT = "campusvault.official@gmail.com"

def generate_unique_id(role: str, length_total: int = 10) -> str:
    """
    Generate a unique ID that starts with:
      'F' for faculty or 'S' for student (case-insensitive).
    The total length (including prefix) will be length_total (default 10).
    Uses cryptographically secure randomness.
    """
    role = (role or "S").strip().upper()
    prefix = "F" if role.startswith("F") else "S"
    if length_total < 2:
        raise ValueError("length_total must be >= 2")
    body_len = length_total - 1
    alphabet = string.ascii_uppercase + string.digits
    body = ''.join(secrets.choice(alphabet) for _ in range(body_len))
    return prefix + body

def build_email(sender: str, recipient: str, subject: str, plain_text: str, html_text: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(plain_text)
    msg.add_alternative(html_text, subtype="html")
    return msg

def send_via_gmail(sender_email: str, app_password: str, message: EmailMessage, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
    """
    Send EmailMessage via Gmail SMTP (TLS).
    """
    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        smtp.ehlo()
        smtp.starttls()           # upgrade to TLS
        smtp.ehlo()
        smtp.login(sender_email, app_password)
        smtp.send_message(message)

def main():
    # --- Inputs (replace or wire these from your app)
    sender_email = os.getenv("CAMPUSVAULT_EMAIL", SENDER_DEFAULT)
    app_password = os.getenv("CAMPUSVAULT_APP_PASSWORD")  # recommended to set in env
    recipient_email = input("Recipient email (user's email): ").strip()
    user_plain_password = input("User's password (to include in email): ").strip()
    user_role = input("User role ('F' for faculty, 'S' for student) [S]: ").strip() or "S"
    custom_message = input("Custom message to include in email: ").strip() or "Welcome to CampusVault!"
    unique_id_length = 10  # change if you want shorter/longer IDs

    if not app_password:
        # Don't echo password on terminal
        app_password = getpass.getpass(f"Enter app password for {sender_email} (input hidden): ").strip()

    # --- Generate unique ID
    unique_id = generate_unique_id(role=user_role, length_total=unique_id_length)

    # --- Compose email body
    subject = "CampusVault — Your account details"
    plain = (
        f"Hello,\n\n"
        f"Here are your account details for CampusVault:\n\n"
        f"Unique ID: {unique_id}\n"
        f"Password: {user_plain_password}\n\n"
        f"{custom_message}\n\n"
        f"If you did not request this, please contact your administrator.\n\n"
        f"Regards,\nCampusVault Team"
    )

    html = f"""
    <html>
      <body>
        <p>Hello,</p>
        <p>Here are your account details for <strong>CampusVault</strong>:</p>
        <ul>
          <li><strong>Unique ID:</strong> {unique_id}</li>
          <li><strong>Password:</strong> <code>{user_plain_password}</code></li>
        </ul>
        <p>{custom_message}</p>
        <p>If you did not request this, please contact your administrator.</p>
        <p>Regards,<br>CampusVault Team</p>
      </body>
    </html>
    """

    email_msg = build_email(sender=sender_email, recipient=recipient_email, subject=subject, plain_text=plain, html_text=html)

    # --- Send
    try:
        send_via_gmail(sender_email=sender_email, app_password=app_password, message=email_msg)
        print(f"Email successfully sent to {recipient_email} with Unique ID {unique_id}.")
    except Exception as e:
        print("Failed to send email. Error:", str(e))
        print("Common causes: invalid app password, SMTP blocked by Gmail, or network issues.")

if __name__ == "__main__":
    main()
