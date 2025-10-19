from flask import Blueprint, request, jsonify, current_app
from app.services.auth_service import create_user, authenticate_user
from app.models.db_models import db, User
from app.utils.security import create_jwt_token
from functools import wraps

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

def json_required(*fields):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            data = request.get_json() or {}
            for f in fields:
                if f not in data:
                    return jsonify({"error": f"Missing field: {f}"}), 400
            return fn(*args, **kwargs)
        return wrapper
    return decorator

@bp.route("/signup", methods=["POST"])
@json_required("name", "email", "password", "college_id", "role")
def signup():
    """
    Public signup route per user request:
    Body JSON:
    { name, email, password, college_id, role }  # role: 'student' or 'faculty'
    On success: creates user, emails credentials, returns user unique_id (but not password)
    """
    data = request.get_json()
    name = data["name"].strip()
    email = data["email"].strip().lower()
    password = data["password"]
    college_id = data["college_id"].strip()
    role = data["role"].strip().lower()
    if role not in ("student", "faculty"):
        return jsonify({"error": "role must be 'student' or 'faculty'"}), 400
    # check if email exists
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400
    try:
        user = create_user(name=name, email=email, password=password, college_id=college_id, role=role)
    except Exception as ex:
        current_app.logger.exception("Failed to create user")
        return jsonify({"error": "Failed to create user", "details": str(ex)}), 500
    return jsonify({"message": "User created", "unique_id": user.unique_id}), 201

@bp.route("/login", methods=["POST"])
@json_required("email", "password")
def login():
    data = request.get_json()
    email = data["email"].strip().lower()
    password = data["password"]
    auth = authenticate_user(email, password)
    if not auth:
        return jsonify({"error": "Invalid credentials"}), 401
    user = auth["user"]
    token = auth["token"]
    return jsonify({
        "token": token,
        "user": {
            "unique_id": user.unique_id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    })
