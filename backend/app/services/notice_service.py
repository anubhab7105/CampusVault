from app.models.db_models import db, Notice

def list_notices(limit=50, offset=0):
    q = Notice.query.order_by(Notice.created_at.desc()).limit(limit).offset(offset)
    return q.all()

def get_notice(nid: int):
    return Notice.query.get(nid)