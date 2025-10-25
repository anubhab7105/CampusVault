# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, create_engine, Session, select
from datetime import datetime
import asyncio
import uvicorn

# ---------------------------
# Models (SQLModel)
# ---------------------------
class Participant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: Optional[str] = None
    avatar_color: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str
    sender: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------
# Database (SQLite)
# ---------------------------
DATABASE_URL = "sqlite:///./chat.db"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    return Session(engine)


def add_participant(username: str, email: Optional[str] = None, avatar_color: Optional[str] = None) -> Participant:
    with get_session() as s:
        stmt = select(Participant).where(Participant.username == username)
        existing = s.exec(stmt).first()
        if existing:
            return existing
        p = Participant(username=username, email=email, avatar_color=avatar_color)
        s.add(p)
        s.commit()
        s.refresh(p)
        return p


def list_participants() -> List[Participant]:
    with get_session() as s:
        return s.exec(select(Participant)).all()


def add_message(room_id: str, sender: str, content: str) -> Message:
    with get_session() as s:
        m = Message(room_id=room_id, sender=sender, content=content)
        s.add(m)
        s.commit()
        s.refresh(m)
        return m


def get_recent_messages(room_id: str, limit: int = 100) -> List[Message]:
    with get_session() as s:
        stmt = select(Message).where(Message.room_id == room_id).order_by(Message.timestamp)
        return s.exec(stmt).all()


# ---------------------------
# WebSocket Connection Manager
# ---------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(room_id, []).append(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket):
        conns = self.active_connections.get(room_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active_connections.pop(room_id, None)

    async def broadcast(self, room_id: str, message: dict):
        conns = self.active_connections.get(room_id, [])[:]
        if not conns:
            return
        await asyncio.gather(*(conn.send_json(message) for conn in conns))


# ---------------------------
# FastAPI app
# ---------------------------
app = FastAPI(title="Chat Backend (single-file)")

# Allow your frontend origins (adjust for production)
origins = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000", "*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()


@app.on_event("startup")
def on_startup():
    init_db()


# ---------- REST models ----------
class CreateParticipantRequest(BaseModel):
    username: str
    email: Optional[str] = None
    avatar_color: Optional[str] = None


class SendMessageRequest(BaseModel):
    room_id: str
    sender: str
    content: str


# ---------- REST endpoints ----------
@app.post("/api/participants")
def create_participant(req: CreateParticipantRequest):
    p = add_participant(req.username, email=req.email, avatar_color=req.avatar_color)
    return {"id": p.id, "username": p.username, "email": p.email, "created_at": p.created_at.isoformat()}


@app.get("/api/participants")
def get_participants():
    parts = list_participants()
    return [{"id": p.id, "username": p.username, "email": p.email, "created_at": p.created_at.isoformat()} for p in parts]


@app.get("/api/messages/{room_id}")
def get_messages(room_id: str, limit: int = 100):
    msgs = get_recent_messages(room_id, limit=limit)
    return [
        {"id": m.id, "room_id": m.room_id, "sender": m.sender, "content": m.content, "timestamp": m.timestamp.isoformat()}
        for m in msgs
    ]


@app.post("/api/messages/send")
def rest_send_message(req: SendMessageRequest):
    m = add_message(req.room_id, req.sender, req.content)
    payload = {
        "type": "message",
        "id": m.id,
        "room_id": m.room_id,
        "sender": m.sender,
        "content": m.content,
        "timestamp": m.timestamp.isoformat(),
    }
    # schedule broadcast if any websocket listeners exist
    try:
        asyncio.create_task(manager.broadcast(req.room_id, payload))
    except RuntimeError:
        # no running event loop in current thread — it's okay for sync usage
        pass
    return payload


# ---------- WebSocket endpoint ----------
@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, username: Optional[str] = Query(None)):
    """
    Connect example: ws://localhost:8000/ws/main?username=Anubhab

    Expected client message:
      {"type": "message", "sender": "Anubhab", "content": "hello"}

    Server sends history first: {"type":"history", "messages":[...]}
    """
    await manager.connect(room_id, websocket)
    if username:
        add_participant(username)

    try:
        # send chat history on connect
        history = get_recent_messages(room_id, limit=100)
        await websocket.send_json({
            "type": "history",
            "messages": [
                {"id": m.id, "sender": m.sender, "content": m.content, "timestamp": m.timestamp.isoformat()}
                for m in history
            ]
        })

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "message":
                content = (data.get("content") or "").strip()
                sender = data.get("sender") or username or "anonymous"
                if not content:
                    continue
                m = add_message(room_id, sender, content)
                payload = {
                    "type": "message",
                    "id": m.id,
                    "room_id": room_id,
                    "sender": sender,
                    "content": content,
                    "timestamp": m.timestamp.isoformat(),
                }
                await manager.broadcast(room_id, payload)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json({"type": "error", "message": "unknown message type"})

    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
    except Exception:
        manager.disconnect(room_id, websocket)
        raise


# Run with: uvicorn main:app --reload --port 8000
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
