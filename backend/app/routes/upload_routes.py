from flask import Blueprint, request, jsonify, current_app, send_file
from app.models.db_models import db, Upload, User
from app.services.upload_service import create_upload
from app.utils.security import decode_jwt_token
from functools import wraps
import os

bp = Blueprint("uploads", __name__, url_prefix="/api/uploads")

def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Missing Authorization header"}), 401
        token = auth.split(" ", 1)[1]
        try:
            payload = decode_jwt_token(token)
            request.user = payload
        except Exception as e:
            return jsonify({"error": "Invalid token", "details": str(e)}), 401
        return fn(*args, **kwargs)
    return wrapper

@bp.route("", methods=["POST"])
@auth_required
def upload_file():
    # only faculty
    role = request.user.get("role")
    uid = request.user.get("sub")
    if role != "faculty":
        return jsonify({"error": "Only faculty can upload files"}), 403
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file_obj = request.files["file"]
    title = request.form.get("title")
    description = request.form.get("description")
    tags = request.form.get("tags")
    visibility = request.form.get("visibility", "college")
    try:
        upload = create_upload(faculty_unique_id=uid, file_storage=file_obj, title=title, description=description, tags=tags, visibility=visibility)
    except Exception as ex:
        current_app.logger.exception("Upload failed")
        return jsonify({"error": "Upload failed", "details": str(ex)}), 400
    return jsonify({
        "message": "Uploaded",
        "upload": {
            "id": upload.id,
            "title": upload.title,
            "filename": upload.filename,
            "doc_type": upload.doc_type,
            "uploaded_at": upload.uploaded_at,
            "faculty_unique_id": upload.faculty_unique_id
        }
    }), 201

@bp.route("", methods=["GET"])
@auth_required
def list_uploads():
    # returns visible uploads; add filtering by tag or doc_type via query params
    q = Upload.query.order_by(Upload.uploaded_at.desc())
    tag = request.args.get("tag")
    doc_type = request.args.get("doc_type")
    page = int(request.args.get("page", "1"))
    per_page = int(request.args.get("per_page", "20"))
    if tag:
        q = q.filter(Upload.tags.like(f"%{tag}%"))
    if doc_type:
        q = q.filter_by(doc_type=doc_type)
    total = q.count()
    items = q.limit(per_page).offset((page - 1) * per_page).all()
    results = []
    for u in items:
        results.append({
            "id": u.id,
            "title": u.title,
            "filename": u.filename,
            "doc_type": u.doc_type,
            "uploaded_at": u.uploaded_at,
            "faculty_unique_id": u.faculty_unique_id,
            "visibility": u.visibility
        })
    return jsonify({"total": total, "items": results})

@bp.route("/<int:upload_id>", methods=["GET"])
@auth_required
def download_upload(upload_id):
    u = Upload.query.get(upload_id)
    if not u:
        return jsonify({"error": "Not found"}), 404
    # permission check: visibility can be enforced here
    if not os.path.exists(u.file_path):
        return jsonify({"error": "File missing on server"}), 500
    return send_file(u.file_path, as_attachment=True, download_name=u.filename)

@bp.route("/<int:upload_id>", methods=["PUT"])
@auth_required
def edit_upload(upload_id):
    u = Upload.query.get(upload_id)
    if not u:
        return jsonify({"error": "Not found"}), 404
    uid = request.user.get("sub")
    role = request.user.get("role")
    if role != "admin" and u.faculty_unique_id != uid:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json() or {}
    if "title" in data:
        u.title = data["title"]
    if "description" in data:
        u.description = data["description"]
    if "tags" in data:
        u.tags = data["tags"]
    db.session.commit()
    return jsonify({"message": "Updated"})
