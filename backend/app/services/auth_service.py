import json
import traceback
from email.message import EmailMessage
import smtplib

from app.models.db_models import db, User
from app.models.login_db import LoginUser
try:
    from app.utils.security import hash_password, create_jwt_token
except Exception:
    # fallback implementations if utils are missing; prefer real ones in your project
    import hashlib, hmac, time, base64
    def hash_password(p):
        return hashlib.sha256(p.encode('utf-8')).hexdigest()
    def create_jwt_token(unique_id):
        # simple dummy token for compatibility; replace with real JWT implementation
        return base64.b64encode(f"token:{unique_id}:{int(time.time())}".encode()).decode()

from app.utils.id_generator import next_unique_id
from app.utils.encrypt import load_or_create_key, encrypt_data
from app.config import SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM, SMTP_USE_TLS


def _send_signup_email(to_email: str, siteid: str, plain_password: str, name: str = None):
    """
    Send an email containing the site id and password.
    WARNING: sending plaintext passwords by email is insecure — see security note in docs.
    """
    try:
        msg = EmailMessage()
        msg["From"] = SMTP_FROM or "no-reply@example.com"
        msg["To"] = to_email
        msg["Subject"] = "Your Site ID and account details"

        body = f"""Hello {name or ''},

Your account has been created.

Site ID: {siteid}
Password: {plain_password}

Please keep these credentials secure.
Regards,
Campus Vault Team
"""
        msg.set_content(body)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            if SMTP_USE_TLS:
                server.starttls()
            if SMTP_USERNAME and SMTP_PASSWORD:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

    except Exception:
        # catch and log but do not fail user creation
        print("Error sending signup email:", traceback.format_exc())


def create_user(name: str, email: str, password: str, college_id: str, role: str):
    """
    Creates a user record in the main users table and a LoginUser record in login_db.
    Returns dict: {"user": <User object>, "token": <jwt token>, "siteid": <siteid>}
    """
    role_char = 'S' if str(role).lower() == 'student' else ('F' if str(role).lower() == 'faculty' else 'A')
    siteid = next_unique_id(role_char)

