from flask import Blueprint, request, jsonify, current_app
from app.models.db_models import db, User
from app.utils.security import decode_jwt_token
from functools import wraps

bp = Blueprint("users", __name__, url_prefix="/api/users")

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

@bp.route("/<unique_id>", methods=["GET"])
@auth_required
def get_user(unique_id):
    # allow admin or self
    caller = request.user.get("sub")
    role = request.user.get("role")
    if caller != unique_id and role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    user = User.query.filter_by(unique_id=unique_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "unique_id": user.unique_id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at,
        "is_active": user.is_active,
        "extra_json": user.extra_json
    })

@bp.route("/<unique_id>", methods=["PUT"])
@auth_required
def edit_user(unique_id):
    caller = request.user.get("sub")
    role = request.user.get("role")
    if caller != unique_id and role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json() or {}
    user = User.query.filter_by(unique_id=unique_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    # allow editing name, extra_json only here (password via separate endpoint)
    if "name" in data:
        user.name = data["name"]
    if "extra_json" in data:
        user.extra_json = data["extra_json"]
    db.session.commit()
    return jsonify({"message": "Updated"})
