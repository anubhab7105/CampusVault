from app.models.db_models import db, Upload, Notice
from app.utils.file_storage import save_uploaded_file, allowed_file
from datetime import datetime

def create_upload(faculty_unique_id: str, file_storage, title: str = None, description: str = None, tags: str = None, doc_type: str = None, visibility: str = "college"):
    if not allowed_file(file_storage.filename):
        raise ValueError("File type not allowed.")
    filename, file_path = save_uploaded_file(file_storage)
    upload = Upload(
        faculty_unique_id=faculty_unique_id,
        filename=filename,
        file_path=file_path,
        doc_type=doc_type or (file_storage.filename.rsplit(".", 1)[1].lower() if "." in file_storage.filename else None),
        title=title,
        description=description,
        uploaded_at=datetime.utcnow().isoformat() + "Z",
        visibility=visibility,
        tags=tags
    )
    db.session.add(upload)
    db.session.commit()
    # create notice
    notice_title = f"New material: {title or filename}"
    notice_content = description or f"{title or filename} uploaded by {faculty_unique_id}"
    notice = Notice(upload_id=upload.id, title=notice_title, content=notice_content, created_by=faculty_unique_id)
    db.session.add(notice)
    db.session.commit()
    return upload
