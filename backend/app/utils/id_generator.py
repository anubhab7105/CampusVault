import uuid

def new_id(prefix="id"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"
