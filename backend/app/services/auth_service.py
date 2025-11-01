import json
import traceback
from email.message import EmailMessage
import smtplib

from app.models.db_models import db, User
from app.models.login_db import LoginUser

# === PLACEHOLDER SECURITY FALLBACKS ===
# Prefer using your actual utils (hash_password, create_jwt_token) from app.utils.security
try:
    from app.utils.security import hash_password, create_jwt_token
except Exception:
    # 🔸 Placeholder fallback if the real security utils are missing
    import hashlib, hmac, time, base64
    def hash_password(p):
        """PLACEHOLDER: Replace with bcrypt or werkzeug.security.generate_password_hash"""
        return hashlib.sha256(p.encode('utf-8')).hexdigest()

    def create_jwt_token(unique_id):
        """PLACEHOLDER: Replace with your real JWT creation logic"""
        return base64.b64encode(f"token:{unique_id}:{int(time.time())}".encode()).decode()


from app.utils.id_generator import next_unique_id
from app.utils.encrypt import load_or_create_key, encrypt_data
from app.config import (
    SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
    SMTP_FROM, SMTP_USE_TLS
)


# =====================================================
#   EMAIL SENDER FUNCTION
# =====================================================
def _send_signup_email(to_email: str, siteid: str, plain_password: str, name: str = None):
    """
    Send an email containing the Site ID and password.
    ⚠ WARNING: Sending plaintext passwords via email is insecure.
       In production, send a reset link or one-time token instead.
    """
    try:
        msg = EmailMessage()
        msg["From"] = SMTP_FROM or "no-reply@example.com"
        msg["To"] = to_email
        msg["Subject"] = "Your Site ID and account details"

        body = f"""Hello {name or ''},

Your account has been created successfully.

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
        # log error but don’t block user creation
        print("Error sending signup email:", traceback.format_exc())


# =====================================================
#   MAIN USER CREATION FUNCTION
# =====================================================
def create_user(name: str, email: str, password: str, college_id: str, role: str):
    """
    Creates a user in both:
      - main database (User)
      - login database (LoginUser)
    Encrypts sensitive fields, generates a site ID, and returns:
      {"user": <User object>, "token": <jwt>, "siteid": <siteid>}
    """
    # Determine site ID prefix based on role
    role_char = 'S' if str(role).lower() == 'student' else (
        'F' if str(role).lower() == 'faculty' else 'A'
    )
    siteid = next_unique_id(role_char)

    try:
        # --- Encryption ---
        key = load_or_create_key()
        encrypted_name = encrypt_data(name, key)
        encrypted_email = encrypt_data(email, key)
        encrypted_college_id = encrypt_data(college_id, key)

        # --- Hash password (never store plain text) ---
        hashed_pw = hash_password(password)

        # --- Create and store User record ---
        user = User(
            unique_id=siteid,
            name=encrypted_name,
            email=encrypted_email,
            password=hashed_pw,
            role=role,
            college_id=encrypted_college_id
        )
        db.session.add(user)
        db.session.commit()

        # --- Add entry to login_db ---
        login_user = LoginUser(
            site_id=siteid,
            password=hashed_pw,
            role=role,
            email=email  # plaintext email only if your schema requires
        )
        login_user.save()

        # --- Send welcome email (optional, non-blocking) ---
        _send_signup_email(email, siteid, password, name)

        # --- Generate JWT token for immediate login ---
        token = create_jwt_token(siteid)

        return {
            "user": user,
            "token": token,
            "siteid": siteid
        }

    except Exception as e:
        db.session.rollback()
        print("Error creating user:", traceback.format_exc())
        raise e
