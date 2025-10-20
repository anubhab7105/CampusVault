from app.models.db_models import db, User
from app.utils.security import hash_password, verify_password, create_jwt_token
from app.utils.id_generator import next_unique_id
from app.config import SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM, SMTP_USE_TLS
import smtplib
from email.message import EmailMessage
import traceback

def create_user(name: str, email: str, password: str, college_id: str, role: str):
    """
    Create a user; role should be 'student' or 'faculty' (or 'admin').
    college_id is stored in extra_json if desired.
    Returns created user object.
    """
    # Determine role character for unique id
    role = role.lower()
    if role == "student":
        rc = "S"
    elif role == "faculty":
        rc = "F"
    elif role == "admin":
        rc = "A"
    else:
        raise ValueError("Invalid role. Must be student, faculty, or admin.")
    unique_id = next_unique_id(rc)
    pwd_hash = hash_password(password)
    extra = {"college_id": college_id} if college_id else None
    user = User(unique_id=unique_id, name=name, email=email, password_hash=pwd_hash, role=role, extra_json=str(extra) if extra else None)
    db.session.add(user)
    db.session.commit()
    # Send email with credentials
    try:
        send_signup_email(email, name, unique_id, password)
    except Exception as ex:
        # Log but don't fail creation
        print("Failed to send signup email:", ex)
        traceback.print_exc()
    return user

def authenticate_user(email: str, password: str):
    user = User.query.filter_by(email=email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    token = create_jwt_token(identity=user.unique_id, role=user.role)
    return {"user": user, "token": token}

def send_signup_email(to_email: str, name: str, unique_id: str, password_plain: str):
    msg = EmailMessage()
    msg["Subject"] = "Welcome — Your account details"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    body = f"""Hello {name},

Your account has been created.

Unique ID: {unique_id}
Password: {password_plain}

Please keep these credentials secure. You may change your password in profile after first login.

Regards,
Campus Vault Team
"""
    msg.set_content(body)
    # send
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        if SMTP_USE_TLS:
            server.starttls()
        if SMTP_USERNAME and SMTP_PASSWORD:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
