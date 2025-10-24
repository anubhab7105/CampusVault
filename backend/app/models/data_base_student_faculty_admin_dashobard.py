# main.py
import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from db_models import db, User, Upload, Notice, Complaint, ChatMessage, AuditLog  # your Flask models file


# ================================================================
# CONFIG
# ================================================================
API_PREFIX = "/api"
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "web")
DATABASE_URL = "sqlite:///campusvault.db"  # you can switch to PostgreSQL later

app = FastAPI(title="CampusVault Unified API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with frontend origin in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================================
# DATABASE SETUP
# ================================================================
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
db.init_app(app)
db.metadata.create_all(engine)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))


def get_db():
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


# ================================================================
# AUTH (Simple Token Stub)
# ================================================================
def get_current_user(request: Request, db_sess=Depends(get_db)) -> User:
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header format")

    token = parts[1]
    # Here token is just unique_id for demo, in production use JWT
    user = db_sess.query(User).filter_by(unique_id=token).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return user


# ================================================================
# SHARED UTILITIES
# ================================================================
def now_iso():
    return datetime.utcnow().isoformat() + "Z"


# ================================================================
# STUDENT ENDPOINTS
# ================================================================
@app.get(API_PREFIX + "/me", response_model=dict)
def api_me(current: User = Depends(get_current_user)):
    return {
        "id": current.id,
        "unique_id": current.unique_id,
        "role": current.role,
        "name": current.name,
        "email": current.email,
    }


@app.get(API_PREFIX + "/student/resources")
def get_resources(current: User = Depends(get_current_user), db_sess=Depends(get_db)):
    if current.role != "student":
        raise HTTPException(status_code=403, detail="Access restricted to students")

    uploads = db_sess.query(Upload).all()
    return [{"id": u.id, "title": u.title, "faculty": u.faculty_unique_id, "file": u.filename} for u in uploads]


@app.post(API_PREFIX + "/complaints", status_code=201)
def raise_complaint(subject: str = Form(...), message: str = Form(...), current: User = Depends(get_current_user), db_sess=Depends(get_db)):
    if current.role != "student":
        raise HTTPException(status_code=403, detail="Only students may raise complaints")

    complaint = Complaint(sender_unique_id=current.unique_id, subject=subject, message=message, status="open")
    db_sess.add(complaint)
    db_sess.commit()

    return {"id": complaint.id, "status": complaint.status}


# ================================================================
# FACULTY ENDPOINTS
# ================================================================
@app.get(API_PREFIX + "/faculty/uploads")
def faculty_uploads(current: User = Depends(get_current_user), db_sess=Depends(get_db)):
    if current.role != "faculty":
        raise HTTPException(status_code=403, detail="Access restricted to faculty")

    uploads = db_sess.query(Upload).filter_by(faculty_unique_id=current.unique_id).all()
    return [{"id": u.id, "title": u.title, "when": u.uploaded_at, "file": u.filename} for u in uploads]


@app.post(API_PREFIX + "/faculty/upload", status_code=201)
async def faculty_upload(
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type: str = Form("pdf"),
    db_sess=Depends(get_db),
    current: User = Depends(get_current_user)
):
    if current.role != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty can upload files")

    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    new_upload = Upload(
        faculty_unique_id=current.unique_id,
        filename=file.filename,
        file_path=file_path,
        doc_type=doc_type,
        title=title,
        uploaded_at=now_iso(),
    )
    db_sess.add(new_upload)
    db_sess.commit()

    return {"status": "success", "id": new_upload.id, "title": new_upload.title}


@app.post(API_PREFIX + "/faculty/notice", status_code=201)
def post_notice(title: str = Form(...), content: str = Form(...), current: User = Depends(get_current_user), db_sess=Depends(get_db)):
    if current.role != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty can post notices")

    new_notice = Notice(title=title, content=content, created_by=current.unique_id, created_at=now_iso())
    db_sess.add(new_notice)
    db_sess.commit()

    return {"status": "ok", "notice_id": new_notice.id}


# ================================================================
# ADMIN ENDPOINTS
# ================================================================
@app.get(API_PREFIX + "/admin/overview")
def admin_overview(current: User = Depends(get_current_user), db_sess=Depends(get_db)):
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    total_users = db_sess.query(User).count()
    total_uploads = db_sess.query(Upload).count()
    pending_complaints = db_sess.query(Complaint).filter_by(status="open").count()

    return {
        "Total Users": total_users,
        "Total Uploads": total_uploads,
        "Pending Complaints": pending_complaints,
    }


@app.get(API_PREFIX + "/admin/uploads")
def admin_all_uploads(current: User = Depends(get_current_user), db_sess=Depends(get_db)):
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    uploads = db_sess.query(Upload).all()
    return [{"id": u.id, "title": u.title, "faculty": u.faculty_unique_id, "uploaded_at": u.uploaded_at} for u in uploads]


# ================================================================
# STATIC FRONTEND
# ================================================================
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {"message": "Frontend missing. Place files in ./web"}


# ================================================================
# RUN
# ================================================================
# Run using: uvicorn main:app --reload --host 0.0.0.0 --port 8000
