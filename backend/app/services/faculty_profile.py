# app.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import bcrypt
import os

# ---------- Configuration ----------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./campusvault.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

app = FastAPI(title="CampusVault API (single-file)")

# Allow your frontend to call this API (change origin in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # TODO: replace "*" with your frontend origin(s) in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Database model ----------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, nullable=True)
    role = Column(String, nullable=True)            # student / faculty
    college = Column(String, nullable=True)
    department = Column(String, nullable=True)
    degree = Column(String, nullable=True)
    year = Column(String, nullable=True)
    registration = Column(String, nullable=True)
    github = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    password = Column(String, nullable=False)       # hashed password

Base.metadata.create_all(bind=engine)

# ---------- Pydantic schemas ----------
class UserBase(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    college: Optional[str] = None
    department: Optional[str] = None
    degree: Optional[str] = None
    year: Optional[str] = None
    registration: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    bio: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserUpdate(UserBase):
    password: Optional[str] = Field(None, min_length=6)

class UserOut(UserBase):
    id: int

    class Config:
        orm_mode = True

# ---------- Dependency ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Utility helpers ----------
def hash_password(plain: str) -> str:
    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

# ---------- CRUD & Endpoints ----------
@app.post("/signup", response_model=UserOut)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    if payload.email is None:
        raise HTTPException(status_code=400, detail="Email is required")
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(payload.password)
    user = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        role=payload.role,
        college=payload.college,
        department=payload.department,
        degree=payload.degree,
        year=payload.year,
        registration=payload.registration,
        github=payload.github,
        linkedin=payload.linkedin,
        bio=payload.bio,
        password=hashed
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/login")
def login(email: EmailStr, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Simple: return user id (you can replace with JWT or session cookie)
    return {"message": "Login successful", "user_id": user.id}

@app.get("/profile/{user_id}", response_model=UserOut)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/profile/{user_id}", response_model=UserOut)
def update_profile(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    data = payload.dict(exclude_unset=True)
    # Handle password separately (hash if provided)
    if "password" in data:
        pw = data.pop("password")
        if pw:  # non-empty provided password -> hash & set
            user.password = hash_password(pw)
    # Update other fields
    for k, v in data.items():
        if hasattr(user, k):
            setattr(user, k, v)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/logout")
def logout():
    # stateless example — frontend should delete any stored token or session client-side
    return {"message": "Logged out"}

# Simple health check
@app.get("/ping")
def ping():
    return {"status": "ok"}

# ---------- Run with: uvicorn app:app --reload ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
