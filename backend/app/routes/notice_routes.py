from flask import Blueprint, request, jsonify
from app.models.db_models import Notice
from app.services.notice_service import list_notices, get_notice
from app.routes.upload_routes import auth_required

bp = Blueprint("notices", __name__, url_prefix="/api/notices")

@bp.route("", methods=["GET"])
@auth_required
def notices_list():
    page = int(request.args.get("page", "1"))
    per_page = int(request.args.get("per_page", "20"))
    items = list_notices(limit=per_page, offset=(page - 1) * per_page)
    res = []
    for n in items:
        res.append({
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "created_by": n.created_by,
            "created_at": n.created_at,
            "pinned": n.pinned,
            "upload_id": n.upload_id
        })
    return jsonify({"items": res})

@bp.route("/<int:nid>", methods=["GET"])
@auth_required
def get_notice_route(nid):
    n = get_notice(nid)
    if not n:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "id": n.id,
        "title": n.title,
        "content": n.content,
        "created_by": n.created_by,
        "created_at": n.created_at,
        "pinned": n.pinned,
        "upload_id": n.upload_id
    })
