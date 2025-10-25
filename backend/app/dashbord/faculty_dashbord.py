# main.py
import os
from typing import List, Optional
from fastapi import FastAPI, Depends, Request, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ========== Config ==========
API_PREFIX = "/api"
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "web")  # put your frontend files in ./web
app = FastAPI(title="CampusVault API (Faculty)")

# CORS - restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change in production to frontend origin(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Pydantic models (API schemas) ==========
class User(BaseModel):
    id: int
    role: str
    name: str
    email: Optional[str]

class Course(BaseModel):
    id: Optional[int]
    code: Optional[str]
    title: str
    semester: Optional[str]
    enrolled: Optional[int]

class UploadOut(BaseModel):
    id: str
    title: str
    when: str  # ISO date in production
    type: Optional[str]
    url: Optional[str]

class UploadIn(BaseModel):
    title: str
    course_code: Optional[str]
    type: Optional[str]

class NoticeIn(BaseModel):
    faculty_id: int
    title: str
    body: str

# ========== Dummy stores (replace with DB) ==========
# NOTE: Replace these with real DB queries (SQLAlchemy / SQLModel / Tortoise / etc.)
_DUMMY_USERS = {
    "token-faculty-1": User(id=10, role="faculty", name="Prof. A", email="prof.a@example.com"),
    "token-student-1": User(id=1, role="student", name="Dipanjan Chakraborty", email="dip@example.com"),
}

_DUMMY_COURSES = {
    10: [
        Course(id=101, code="CS201", title="Data Structures", semester="Autumn 2025", enrolled=120),
        Course(id=102, code="CS403", title="Cybersecurity", semester="Autumn 2025", enrolled=88),
    ]
}

_DUMMY_UPLOADS = {
    10: [
        UploadOut(id="upl-1", title="Assignment 1", when="2025-10-16", type="pdf", url="/assets/assign1.pdf"),
        UploadOut(id="upl-2", title="Lecture 7 - Slides", when="2025-10-10", type="pdf", url="/assets/lec7.pdf"),
    ]
}

_DUMMY_NOTICES = []
_DUMMY_UPLOAD_STORE = []

# ========== Auth dependency (simple token stub) ==========
def get_current_user(request: Request) -> User:
    """
    Simple demo auth:
    - Client sends header 'Authorization: Bearer token-faculty-1'
    Replace with proper JWT/session in production.
    """
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header format")
    token = parts[1]
    user = _DUMMY_USERS.get(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user

# ========== API endpoints ==========
@app.get(API_PREFIX + "/me", response_model=User)
def api_me(current: User = Depends(get_current_user)):
    """
    Returns the currently authenticated user.
    Replace get_current_user with real auth lookup (decode JWT, lookup in DB).
    """
    return current

@app.get(API_PREFIX + "/faculty/{faculty_id}/courses", response_model=List[Course])
def faculty_courses(faculty_id: str, current: User = Depends(get_current_user)):
    """
    Return courses owned/taught by faculty.
    TODO: Replace dummy lookup with DB query:
      SELECT c.* FROM courses c WHERE c.faculty_id = :faculty_id
    """
    # Only allow faculty or admins to access; students should be blocked
    if current.role != "faculty":
        raise HTTPException(status_code=403, detail="Access restricted to faculty")
    # If client passes "me" allow current.id
    rid = current.id if faculty_id in ("me", str(current.id)) else int(faculty_id)
    return _DUMMY_COURSES.get(rid, [])

@app.get(API_PREFIX + "/faculty/{faculty_id}/uploads", response_model=List[UploadOut])
def faculty_uploads(faculty_id: str, limit: int = 10, current: User = Depends(get_current_user)):
    """
    Return recent uploads by this faculty.
    TODO: Replace with DB query ordering by created_at desc.
    """
    if current.role != "faculty":
        raise HTTPException(status_code=403, detail="Access restricted to faculty")
    rid = current.id if faculty_id in ("me", str(current.id)) else int(faculty_id)
    return _DUMMY_UPLOADS.get(rid, [])[:limit]

@app.post(API_PREFIX + "/uploads", response_model=UploadOut, status_code=201)
async def upload_metadata(data: UploadIn, current: User = Depends(get_current_user)):
    """
    Accepts metadata for an upload (title, course_code, type).
    In production you will:
      - Accept file upload (multipart/form-data) and store file (S3/local)
      - Save metadata in DB with file URL
    This endpoint is a placeholder showing where to insert DB/file-storage code.
    """
    if current.role != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty can upload")
    new_id = f"upl-{len(_DUMMY_UPLOAD_STORE)+1}"
    rec = UploadOut(id=new_id, title=data.title, when="2025-10-25", type=data.type or "file", url=f"/assets/{new_id}")
    _DUMMY_UPLOAD_STORE.append(rec.dict())
    # In production: INSERT into uploads table and return created record
    return rec

@app.post(API_PREFIX + "/notices", status_code=201)
def post_notice(payload: NoticeIn, current: User = Depends(get_current_user)):
    """
    Faculty posts a notice. TODO: insert into DB and notify students.
    """
    if current.role != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty can post notices")
    notice = {"id": len(_DUMMY_NOTICES) + 1, "faculty_id": payload.faculty_id, "title": payload.title, "body": payload.body, "created_at": "2025-10-25"}
    _DUMMY_NOTICES.append(notice)
    # In production: return created notice record (response_model) and push notification if needed
    return {"status": "ok", "id": notice["id"]}

# Mount frontend static files (optional)
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {"message": "Frontend missing. Put static files in ./web or mount separately."}

# Run with: uvicorn main:app --reload --port 8000
