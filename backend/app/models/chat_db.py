from sqlmodel import SQLModel, create_engine, Session, select
from models import Participant, Message
from typing import List

# SQLite file
DATABASE_URL = "sqlite:///./chat.db"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    return Session(engine)


# convenience helpers (optional)
def add_participant(username: str, email: str = None, avatar_color: str = None) -> Participant:
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


def get_recent_messages(room_id: str, limit: int = 100):
    with get_session() as s:
        stmt = select(Message).where(Message.room_id == room_id).order_by(Message.timestamp)
        return s.exec(stmt).all()
