from app.models.db_models import db, ChatMessage
from datetime import datetime

def send_message(sender_unique_id: str, receiver_unique_id: str, message: str, context_type: str = "global", context_id: int = None):
    cm = ChatMessage(
        sender_unique_id=sender_unique_id,
        receiver_unique_id=receiver_unique_id,
        message=message,
        context_type=context_type,
        context_id=context_id,
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    db.session.add(cm)
    db.session.commit()
    return cm

def fetch_conversation(user_a: str, user_b: str, limit=50):
    q = ChatMessage.query.filter(
        ((ChatMessage.sender_unique_id == user_a) & (ChatMessage.receiver_unique_id == user_b)) |
        ((ChatMessage.sender_unique_id == user_b) & (ChatMessage.receiver_unique_id == user_a))
    ).order_by(ChatMessage.created_at.desc()).limit(limit)
    return list(reversed(q.all()))

def fetch_new_messages(since_iso: str):
    return ChatMessage.query.filter(ChatMessage.created_at > since_iso).order_by(ChatMessage.created_at.asc()).all()
