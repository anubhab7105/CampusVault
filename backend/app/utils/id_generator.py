from sqlalchemy import select, func
from ..models import db_models
from ..models.db_models import User
import re

def _extract_number(unique_id: str):
    m = re.search(r'(\d+)$', unique_id or "")
    return int(m.group(1)) if m else 0

def generate_unique_id(session, role_char: str, width: int = 6):
    """
    Generate unique id like F000001 or S000123. role_char single char.
    """
    # find max numeric suffix for role
    stmt = select(User.unique_id).where(User.unique_id.like(f"{role_char}%"))
    results = session.execute(stmt).scalars().all()
    max_n = 0
    for uid in results:
        n = _extract_number(uid)
        if n > max_n:
            max_n = n
    new_num = max_n + 1
    formatted = f"{role_char}{str(new_num).zfill(width)}"
    # ensure uniqueness - double check DB
    exists = session.query(User).filter_by(unique_id=formatted).first()
    if exists:
        # fallback loop
        while True:
            new_num += 1
            formatted = f"{role_char}{str(new_num).zfill(width)}"
            if not session.query(User).filter_by(unique_id=formatted).first():
                break
    return formatted

def ensure_initial_admins(session):
    """
    Ensure at least 3 admin users exist A001..A003 (or A0001 style).
    If none exist, create A001..A003 with a default password 'adminpass' (hashed by caller)
    Note: For security, in production supply real admin creation.
    """
    # check any admin exists
    if session.query(User).filter_by(role="admin").count() == 0:
        from ..utils.security import hash_password
        for i in range(1, 4):
            uid = f"A{str(i).zfill(3)}"
            user = User(
                unique_id=uid,
                name=f"Admin {i}",
                email=f"admin{i}@example.com",
                password_hash=hash_password("adminpass"),
                role="admin",
            )
            session.add(user)
        session.commit()
