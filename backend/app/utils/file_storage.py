import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from app.config import UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {
    "pdf", "pptx", "ppt", "docx", "doc", "exel", "word", "txt", 
}

def ensure_upload_folder():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename: str):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def save_uploaded_file(file_obj, subdir: str = "") -> tuple[str, str]:
    """
    Saves the uploaded file into UPLOAD_FOLDER[/subdir] and returns (filename, file_path)
    file_obj is a Werkzeug FileStorage object.
    """
    ensure_upload_folder()
    filename = secure_filename(file_obj.filename)
    if subdir:
        target_dir = os.path.join(UPLOAD_FOLDER, secure_filename(subdir))
    else:
        target_dir = UPLOAD_FOLDER
    os.makedirs(target_dir, exist_ok=True)
    # use uuid prefix to avoid collisions
    unique_prefix = uuid.uuid4().hex[:8]
    stored_name = f"{unique_prefix}_{filename}"
    stored_path = os.path.join(target_dir, stored_name)
    file_obj.save(stored_path)
    return stored_name, stored_path
