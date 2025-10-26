#!/usr/bin/env python3
"""
send_credentials_db.py

Usage:
  - Set environment variable CAMPUSVAULT_EMAIL (optional, defaults to campusvault.official@gmail.com)
  - Set environment variable CAMPUSVAULT_APP_PASSWORD to the Gmail app password (recommended).
  - Optionally set CAMPUSVAULT_DB (path to sqlite file, default: campusvault.db)
  - Run: python send_credentials_db.py

What it does:
  - Initializes a SQLite DB with a `users` table (email, role, unique_id, password, sent flag, timestamps).
  - Provides functions to add users (you can use your own unique id / password generator).
  - Scans for unsent users and sends the credential email (plain + html) using Gmail SMTP.
  - Marks each successfully sent user as sent (and records sent_at).
"""

import os
import sqlite3
import secrets
import string
import smtplib
from email.message import EmailMessage
from datetime import datetime
import getpass
import logging
from typing import Optional, List, Tuple

# ---------- Config ----------
DEFAULT_SENDER = "campusvault.official@gmail.com"
DB_PATH = os.getenv("CAMPUSVAULT_DB", "campusvault.db")
SENDER_EMAIL = os.getenv("CAMPUSVAULT_EMAIL", DEFAULT_SENDER)
APP_PASSWORD_ENV = os.getenv("CAMPUSVAULT_APP_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


# ---------- YOUR existing unique id generator (copied/adapted) ----------
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


# ---------- Optional secure password generator (you said you already have one) ----------
def generate_password(length: int = 12) -> str:
    """Generate a reasonably secure random password (you can replace with your own)."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ---------- Email building & sending (re-uses patterns from your script) ----------
def build_email(sender: str, recipient: str, subject: str, plain_text: str, html_text: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(plain_text)
    msg.add_alternative(html_text, subtype="html")
    return msg


def send_via_gmail(sender_email: str, app_password: str, message: EmailMessage,
                   smtp_server: str = SMTP_SERVER, smtp_port: int = SMTP_PORT):
    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(sender_email, app_password)
        smtp.send_message(message)


# ---------- SQLite DB helpers ----------
def init_db(db_path: str = DB_PATH):
    """Create users table if not exists."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL,
        unique_id TEXT NOT NULL,
        password TEXT NOT NULL,
        sent INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        sent_at TEXT
    );
    """)
    conn.commit()
    conn.close()
    logging.info("Database initialized at %s", db_path)


def add_user(email: str, role: str = "S", unique_id: Optional[str] = None,
             password: Optional[str] = None, db_path: str = DB_PATH) -> bool:
    """
    Insert a new user. If unique_id or password is None, we generate them.
    Returns True if inserted, False if user already exists.
    """
    if not unique_id:
        unique_id = generate_unique_id(role=role)
    if not password:
        password = generate_password()

    created_at = datetime.utcnow().isoformat()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (email, role, unique_id, password, created_at) VALUES (?, ?, ?, ?, ?)",
            (email, role.upper(), unique_id, password, created_at)
        )
        conn.commit()
        logging.info("Added user %s (id=%s)", email, unique_id)
        return True
    except sqlite3.IntegrityError:
        logging.warning("User %s already exists in DB", email)
        return False
    finally:
        conn.close()


def get_unsent_users(limit: Optional[int] = None, db_path: str = DB_PATH) -> List[Tuple]:
    """
    Return list of unsent users as tuples:
    (id, email, role, unique_id, password, created_at)
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    q = "SELECT id, email, role, unique_id, password, created_at FROM users WHERE sent = 0 ORDER BY id ASC"
    if limit:
        q += f" LIMIT {int(limit)}"
    cur.execute(q)
    rows = cur.fetchall()
    conn.close()
    return rows


def mark_user_sent(user_id: int, db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE users SET sent = 1, sent_at = ? WHERE id = ?", (datetime.utcnow().isoformat(), user_id))
    conn.commit()
    conn.close()
    logging.info("Marked user id=%s as sent", user_id)


# ---------- Email content template ----------
def make_email_texts(unique_id: str, user_plain_password: str, custom_message: str = "Welcome to CampusVault!") -> Tuple[str, str]:
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
    return subject, plain, html


# ---------- Main routine: send unsent emails ----------
def send_unsent_emails(limit: Optional[int] = None, sender_email: str = SENDER_EMAIL,
                       app_password: Optional[str] = APP_PASSWORD_ENV, db_path: str = DB_PATH,
                       custom_message: str = "Welcome to CampusVault!"):
    if not app_password:
        # Prompt for app password if not set in env
        app_password = getpass.getpass(f"Enter app password for {sender_email} (input hidden): ").strip()

    unsent = get_unsent_users(limit=limit, db_path=db_path)
    if not unsent:
        logging.info("No unsent users found.")
        return

    logging.info("Found %d unsent users (limit=%s). Starting send...", len(unsent), limit)

    for user in unsent:
        user_id, email, role, unique_id, password, created_at = user
        subject, plain, html = make_email_texts(unique_id=unique_id, user_plain_password=password, custom_message=custom_message)
        try:
            msg = build_email(sender=sender_email, recipient=email, subject=subject, plain_text=plain, html_text=html)
            send_via_gmail(sender_email=sender_email, app_password=app_password, message=msg)
            mark_user_sent(user_id, db_path=db_path)
            logging.info("Email sent to %s", email)
        except Exception as e:
            # Log and continue with other users
            logging.error("Failed to send email to %s (id=%s): %s", email, user_id, e)


# ---------- Example CLI ----------
def cli():
    import argparse
    parser = argparse.ArgumentParser(description="Manage CampusVault credential emails (SQLite).")
    parser.add_argument("--init-db", action="store_true", help="Create DB and tables if missing.")
    parser.add_argument("--add-user", nargs=2, metavar=("EMAIL","ROLE"), help="Add a user (ROLE: F or S).")
    parser.add_argument("--add-user-with", nargs=3, metavar=("EMAIL","ROLE","PASSWORD"), help="Add user with explicit password (and generate unique_id).")
    parser.add_argument("--send-unsent", action="store_true", help="Send emails to unsent users.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of unsent users to send in this run.")
    parser.add_argument("--custom-message", type=str, default="Welcome to CampusVault!", help="Custom message to include in email.")
    args = parser.parse_args()

    if args.init_db:
        init_db(DB_PATH)
    if args.add_user:
        email, role = args.add_user
        added = add_user(email=email, role=role, db_path=DB_PATH)
        if added:
            print(f"Added {email}")
        else:
            print(f"{email} already exists")
    if args.add_user_with:
        email, role, password = args.add_user_with
        unique_id = generate_unique_id(role=role)
        added = add_user(email=email, role=role, unique_id=unique_id, password=password, db_path=DB_PATH)
        if added:
            print(f"Added {email} with provided password")
        else:
            print(f"{email} already exists")
    if args.send_unsent:
        send_unsent_emails(limit=args.limit, sender_email=SENDER_EMAIL, app_password=APP_PASSWORD_ENV, db_path=DB_PATH, custom_message=args.custom_message)


if __name__ == "__main__":
    cli()
