from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    unique_id = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(256), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), nullable=False)  # admin, faculty, student
    created_at = db.Column(db.String(64), default=now_iso)
    is_active = db.Column(db.Boolean, default=True)
    extra_json = db.Column(db.Text, nullable=True)

    uploads = db.relationship("Upload", backref="faculty", lazy=True, primaryjoin="User.unique_id==foreign(Upload.faculty_unique_id)")
    complaints = db.relationship("Complaint", backref="sender", lazy=True, primaryjoin="User.unique_id==foreign(Complaint.sender_unique_id)")

class Upload(db.Model):
    __tablename__ = "uploads"
    id = db.Column(db.Integer, primary_key=True)
    faculty_unique_id = db.Column(db.String(32), db.ForeignKey("users.unique_id"), nullable=False)
    filename = db.Column(db.String(512), nullable=False)
    file_path = db.Column(db.String(1024), nullable=False)
    doc_type = db.Column(db.String(64), nullable=True)
    title = db.Column(db.String(512), nullable=True)
    description = db.Column(db.Text, nullable=True)
    uploaded_at = db.Column(db.String(64), default=now_iso)
    visibility = db.Column(db.String(64), default="college")
    tags = db.Column(db.String(1024), nullable=True)

class Notice(db.Model):
    __tablename__ = "notices"
    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey("uploads.id"), nullable=True)
    title = db.Column(db.String(512), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.String(32), nullable=False)  # unique_id
    created_at = db.Column(db.String(64), default=now_iso)
    pinned = db.Column(db.Boolean, default=False)

class Complaint(db.Model):
    __tablename__ = "complaints"
    id = db.Column(db.Integer, primary_key=True)
    sender_unique_id = db.Column(db.String(32), db.ForeignKey("users.unique_id"), nullable=False)
    subject = db.Column(db.String(512), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.String(64), default=now_iso)
    status = db.Column(db.String(32), default="open")  # open, in_progress, resolved
    admin_response = db.Column(db.Text, nullable=True)

class ChatMessage(db.Model):
    __tablename__ = "chat_messages"
    id = db.Column(db.Integer, primary_key=True)
    sender_unique_id = db.Column(db.String(32), nullable=False)
    receiver_unique_id = db.Column(db.String(32), nullable=True)  # null -> group/global
    message = db.Column(db.Text, nullable=False)
    context_type = db.Column(db.String(64), default="global")  # global, upload_question, private
    context_id = db.Column(db.Integer, nullable=True)  # upload id if context_type == upload_question
    created_at = db.Column(db.String(64), default=now_iso)

class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(256), nullable=False)
    user_unique_id = db.Column(db.String(32), nullable=True)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.String(64), default=now_iso)
