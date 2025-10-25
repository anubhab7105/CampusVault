# main.py
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os

# ========== Config ==========
API_PREFIX = "/api"

app = FastAPI(title="CampusVault API")

# Allow your frontend origin(s). For local dev use: http://localhost:5500 or where you host.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change this to the exact origin(s) in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======= Simple "database" placeholders ========
# Replace these functions / structures with actual DB calls (SQLAlchemy, async DB, etc.)
# Example: connect to Postgres via asyncpg or SQLAlchemy; return rows mapped to pydantic models.

class User(BaseModel):
    id: int
    role: str
    name: str
    email: Optional[str] = None

class Resource(BaseModel):
    id: int
    title: str
    source: str
    link: Optional[str] = None

class Upload(BaseModel):
    id: int
    title: str
    when: str  # or datetime in real DB

class ComplaintIn(BaseModel):
    student_id: int
    subject: str
    message: str

class ComplaintOut(BaseModel):
    id: int
    status: str

# Dummy in-memory store (for demo). Replace with DB access code.
_DUMMY_USERS = {
    "token-student-1": User(id=1, role="student", name="Dipanjan Chakraborty", email="dip@example.com"),
    "token-faculty-1": User(id=2, role="faculty", name="Prof. A", email="prof@example.com"),
}

_DUMMY_RESOURCES = {
    1: [  # user id -> list of resources
        Resource(id=1, title="Data Structures - Notes", source="Prof. A", link="/assets/ds.pdf"),
        Resource(id=2, title="OS Lab Manual", source="Library", link="/assets/os_lab.pdf"),
    ]
}

_DUMMY_UPLOADS = [
    Upload(id=1, title="Database Notes", when="2025-10-23"),
    Upload(id=2, title="Programming Lab Solutions", when="2025-10-21"),
]

_DUMMY_COMPLAINTS = []


# ========== Auth dependency (placeholder) ===========
def get_current_user(request: Request) -> User:
    # Simple token auth for demo: send header Authorization: Bearer token-student-1
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth header format")
    token = parts[1]
    user = _DUMMY_USERS.get(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user


# ========== API Endpoints ===========
@app.get(API_PREFIX + "/me", response_model=User)
def api_me(current: User = Depends(get_current_user)):
    """Return current logged-in user's basic info."""
    return current


@app.get(API_PREFIX + "/student/resources", response_model=List[Resource])
def api_student_resources(current: User = Depends(get_current_user)):
    """Return resources/courses for the logged-in student.
    TODO: replace in-memory lookup with DB query (e.g., SELECT resources JOIN enrollments WHERE student_id = current.id)
    """
    if current.role != "student":
        raise HTTPException(status_code=403, detail="Access restricted to students")
    # Placeholder: fetch from DB by current.id
    return _DUMMY_RESOURCES.get(current.id, [])


@app.get(API_PREFIX + "/uploads/latest", response_model=List[Upload])
def api_latest_uploads(limit: int = 10):
    """Return latest uploads. In production, sort by created_at desc and return top `limit`."""
    # Replace with DB query that orders by timestamp.
    return _DUMMY_UPLOADS[:limit]


@app.get(API_PREFIX + "/library/search", response_model=List[Resource])
def api_library_search(q: str, limit: int = 20):
    """Search library. Replace this with fulltext search in DB or an index (Elasticsearch, Postgres full-text)."""
    if not q:
        return []
    q_lower = q.lower()
    results = []
    # Placeholder simple search on dummy resources
    pool = sum(_DUMMY_RESOURCES.values(), [])
    for r in pool:
        if q_lower in r.title.lower() or q_lower in (r.source or "").lower():
            results.append(r)
    return results[:limit]


@app.post(API_PREFIX + "/complaints", response_model=ComplaintOut, status_code=201)
def api_raise_complaint(payload: ComplaintIn, current: User = Depends(get_current_user)):
    """Student raises a complaint. In production: insert into DB and notify support."""
    if current.role != "student":
        raise HTTPException(status_code=403, detail="Only students may raise complaints")
    # Here, store in DB. Placeholder:
    new_id = len(_DUMMY_COMPLAINTS) + 1
    record = {
        "id": new_id,
        "student_id": payload.student_id,
        "subject": payload.subject,
        "message": payload.message,
        "status": "open",
    }
    _DUMMY_COMPLAINTS.append(record)
    return ComplaintOut(id=new_id, status="open")


# ========== Serve frontend static files ===========
# Point this to the directory where your HTML/CSS/JS live.
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "web")  # put your frontend build in ./web

if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    # If no static directory present, root will show a simple message
    @app.get("/")
    def root():
        return {"message": "Frontend not found. Put your site in ./web directory or mount static files."}


# ========== Run ===========
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
