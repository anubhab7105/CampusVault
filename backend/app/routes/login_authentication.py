from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth_bp = Blueprint('auth', __name__)

# Login API
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    siteid = data.get('siteid')
    password = data.get('password')

    user = User.query.filter_by(siteid=siteid).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

    return jsonify({"success": True, "message": "Login successful!"})

# Signup API
@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    siteid = data.get('siteid')
    password = generate_password_hash(data.get('password'))

    if User.query.filter_by(siteid=siteid).first():
        return jsonify({"success": False, "message": "User already exists!"}), 409

    new_user = User(siteid=siteid, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"success": True, "message": "Signup successful!"})
