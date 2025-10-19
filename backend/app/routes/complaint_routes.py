from flask import Blueprint, request, jsonify
from app.services.complaint_service import submit_complaint, list_complaints, update_complaint
from app.models.db_models import User
from app.routes.upload_routes import auth_required

bp = Blueprint("complaints", __name__, url_prefix="/api/complaints")

@bp.route("", methods=["POST"])
@auth_required
def create_complaint():
    data = request.get_json() or {}
    subject = data.get("subject")
    message = data.get("message")
    if not subject or not message:
        return jsonify({"error": "Missing subject or message"}), 400
    sender_unique_id = request.user.get("sub")
    c = submit_complaint(sender_unique_id=sender_unique_id, subject=subject, message=message)
    return jsonify({"message": "Submitted", "complaint_id": c.id}), 201

@bp.route("", methods=["GET"])
@auth_required
def list_route():
    # admin only
    role = request.user.get("role")
    if role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    status = request.args.get("status")
    items = list_complaints(status=status)
    res = []
    for c in items:
        res.append({
            "id": c.id,
            "sender_unique_id": c.sender_unique_id,
            "subject": c.subject,
            "message": c.message,
            "created_at": c.created_at,
            "status": c.status,
            "admin_response": c.admin_response
        })
    return jsonify({"items": res})

@bp.route("/<int:cid>", methods=["PUT"])
@auth_required
def update(cid):
    role = request.user.get("role")
    if role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json() or {}
    status = data.get("status")
    admin_response = data.get("admin_response")
    c = update_complaint(cid, status=status, admin_response=admin_response)
    if not c:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"message": "Updated"})
