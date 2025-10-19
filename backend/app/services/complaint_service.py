from app.models.db_models import db, Complaint

def submit_complaint(sender_unique_id: str, subject: str, message: str):
    c = Complaint(sender_unique_id=sender_unique_id, subject=subject, message=message)
    db.session.add(c)
    db.session.commit()
    return c

def list_complaints(status=None):
    q = Complaint.query
    if status:
        q = q.filter_by(status=status)
    return q.order_by(Complaint.created_at.desc()).all()

def update_complaint(cid: int, status: str = None, admin_response: str = None):
    c = Complaint.query.get(cid)
    if not c:
        return None
    if status:
        c.status = status
    if admin_response:
        c.admin_response = admin_response
    db.session.commit()
    return c
