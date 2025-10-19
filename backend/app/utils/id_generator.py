import re
from app.models.db_models import db, User
from sqlalchemy import func

def _extract_number(unique_id: str) -> int:
    # remove leading letter(s) and leading zeros
    m = re.search(r'([A-Za-z]+)(0*)(\d+)$', unique_id)
    if not m:
        return 0
    return int(m.group(3))

def next_unique_id(role_char: str) -> str:
    """
    role_char: 'F' or 'S' or 'A'
    Format: <role_char><zero-padded number>
    Faculty & Student use 6 digits after letter, e.g., F000001
    Admin: A001 (keep as A001... we pre-create)
    """
    role_char = role_char.upper()
    if role_char == "A":
        # For admin we follow A001, A002, ...
        # find max numeric suffix of existing A* ids
        max_id = db.session.query(func.max(User.unique_id)).filter(User.unique_id.like("A%")).scalar()
        if not max_id:
            n = 1
        else:
            # get numeric suffix
            n = _extract_number(max_id) + 1
        return f"A{n:03d}"
    else:
        # Students and Faculty: 6-digit suffix
        pattern = f"{role_char}%"
        max_id = db.session.query(func.max(User.unique_id)).filter(User.unique_id.like(pattern)).scalar()
        if not max_id:
            n = 1
        else:
            n = _extract_number(max_id) + 1
        return f"{role_char}{n:06d}"
