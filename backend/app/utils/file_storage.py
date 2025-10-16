import os
from .id_generator import new_id
from ..config import UPLOAD_DIR

def ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)

def store_uploaded(file_obj, filename=None):
    ensure_upload_dir()
    name = filename or new_id("file")
    path = os.path.join(UPLOAD_DIR, name)
    with open(path, "wb") as f:
        f.write(file_obj.read())
    return path
