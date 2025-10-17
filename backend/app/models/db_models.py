from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from ..config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)
    # create default admins if not present
    from sqlalchemy.orm import Session
    session: Session = SessionLocal()
    from ..utils.id_generator import ensure_initial_admins
    ensure_initial_admins(session)
    session.close()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    unique_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # admin / faculty / student
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    extra_json = Column(Text, nullable=True)

    uploads = relationship("Upload", back_populates="faculty", cascade="all, delete-orphan")
    sent_messages = relationship("ChatMessage", back_populates="sender", foreign_keys="ChatMessage.sender_unique_id", primaryjoin="User.unique_id==ChatMessage.sender_unique_id")

class Upload(Base):
    __tablename__ = "uploads"
    id = Column(Integer, primary_key=True)
    faculty_unique_id = Column(String, ForeignKey("users.unique_id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    doc_type = Column(String)
    title = Column(String)
    description = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    visibility = Column(String, default="college")
    tags = Column(Text, nullable=True)

    faculty = relationship("User", back_populates="uploads")
    notice = relationship("Notice", back_populates="upload", uselist=False)

class Notice(Base):
    __tablename__ = "notices"
    id = Column(Integer, primary_key=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    pinned = Column(Boolean, default=False)

    upload = relationship("Upload", back_populates="notice")

class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True)
    sender_unique_id = Column(String, nullable=False)
    subject = Column(String)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="open")  # open / in_progress / resolved
    admin_response = Column(Text, nullable=True)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True)
    sender_unique_id = Column(String, nullable=False, index=True)  # e.g., F000001
    receiver_unique_id = Column(String, nullable=True, index=True)  # null for global
    message = Column(Text)
    context_type = Column(String, default="global")  # global, upload_question, private
    context_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # lightweight backref
    # For back-population in User we use string-based foreign_keys
    sender = relationship("User", primaryjoin="User.unique_id==ChatMessage.sender_unique_id", viewonly=True)
