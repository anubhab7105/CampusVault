# main.py
import os
from typing import List, Dict, Optional
from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

API_PREFIX = "/api"
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "web")  # put frontend files in ./web

app = FastAPI(title="CampusVault API (Admin)")

# CORS - in production replace "*" with your frontend origin(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======= Schemas =======
class User(BaseModel):
    id: int
    role: str
    name: str
    email: Optional[str] = None

class OverviewTile(BaseModel):
    title: str
    value: str
    subtitle: Optional[str] = None

class UploadItem(BaseModel):
    id: str
    title: str
    owner: str
    when: str
    url: Optional[str] = None

# ======= Dummy stores (replace these with DB) =======
# NOTE: Replace these with queries to your real DB (SQLAlchemy, SQLModel, or async ORM)
_DUMMY_USERS = {
    "token-admin-1": User(id=1000, role="admin", name="Anubhab", email="admin@example.com"),
}

_DUMMY_OVERVIEW = [
    OverviewTile(title="Total Users", value="2,134", subtitle="Students/Faculty/Admin"),
    OverviewTile(title="Total Uploads", value="4,890", subtitle="Last 30 days"),
    OverviewTile(title="Pending Approvals", value="12", subtitle="Uploads & User requests"),
    OverviewTile(title="Active Sessions", value="230", subtitle="Real-time"),
]

_DUMMY_UPLOADS = [
    UploadItem(id="u1", title="AI Lecture Notes", owner="Prof. X", when="2025-10-25T10:30:00Z", url="/assets/ai_notes.pdf"),
    UploadItem(id="u2", title="DBMS Slides", owner="Prof. Y", when="2025-10-24T14:00:00Z", url="/assets/dbms_slides.pdf"),
]

# ======= Simple auth dependency (placeholder) =======
def get_current_user(request: Request) -> User:
    """
    Demo token-based auth: "Authorization: Bearer token-admin-1"
    Replace with JWT/session lookup in production.
    """
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
    token = parts[1]
    user = _DUMMY_USERS.get(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user

# ======= Admin endpoints =======
@app.get(API_PREFIX + "/me", response_model=User)
def api_me(current: User = Depends(get_current_user)):
    """Return authenticated user info (used by front-end to show greetings & enforce role)."""
    return current

@app.get(API_PREFIX + "/admin/overview", response_model=List[OverviewTile])
def api_admin_overview(current: User = Depends(get_current_user)):
    """
    Return high-level system overview:
    TODO: Replace _DUMMY_OVERVIEW with queries that aggregate data from DB:
      - total users (SELECT COUNT(*) FROM users)
      - total uploads (SELECT COUNT(*) FROM uploads WHERE created_at >= now() - interval '30 days')
      - pending approvals (SELECT COUNT(*) FROM approvals WHERE status='pending')
      - active sessions (from session store or analytics)
    """
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return _DUMMY_OVERVIEW

@app.get(API_PREFIX + "/admin/uploads", response_model=List[UploadItem])
def api_admin_uploads(limit: int = 20, current: User = Depends(get_current_user)):
    """
    Return recent uploads & logs. Replace with DB query ordering by created_at desc.
    """
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    # In production: SELECT id,title,owner,created_at,url FROM uploads ORDER BY created_at DESC LIMIT :limit
    return _DUMMY_UPLOADS[:limit]

# Example maintenance/admin action endpoints (placeholders)
@app.post(API_PREFIX + "/admin/reports")
def api_generate_report(report_type: str, current: User = Depends(get_current_user)):
    """
    Trigger a server-side report generation (placeholder).
    TODO: Implement report job dispatch (Celery/RQ or background task) and return job id.
    """
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"status": "accepted", "report_type": report_type}

# ======= Mount static frontend (optional) =======
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {"message": "Frontend missing. Put site in ./web or mount separately."}

# ======= Run note =======
# Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
