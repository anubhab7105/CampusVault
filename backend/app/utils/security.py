import os
import random
import bcrypt
import jwt
import datetime
from functools import wraps
from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campusvault.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Security constants
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "supersecretadmintoken")
JWT_SECRET = os.environ.get("JWT_SECRET", "supersecretjwt")
JWT_EXP_MINUTES = 60
PRIVATE_KEY_FILE = "private_key.pem"
PUBLIC_KEY_FILE = "public_key.pem"

# RSA key setup
def load_or_generate_keys():
    if os.path.exists(PRIVATE_KEY_FILE) and os.path.exists(PUBLIC_KEY_FILE):
        with open(PRIVATE_KEY_FILE, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(PUBLIC_KEY_FILE, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
        print("Loaded existing RSA keys.")
    else:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        with open(PRIVATE_KEY_FILE, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        with open(PUBLIC_KEY_FILE, "wb") as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        print("Generated and saved new RSA keys.")
    return private_key, public_key

private_key, public_key = load_or_generate_keys()

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.LargeBinary, nullable=False)
    email = db.Column(db.LargeBinary, nullable=False)
    password = db.Column(db.LargeBinary, nullable=False)
    colloegeid = db.Column(db.LargeBinary, nullable=False)
    role = db.Column(db.LargeBinary, nullable=False)
    faculty_code = db.Column(db.LargeBinary, nullable=True)

with app.app_context():
    db.create_all()

# Helpers
def encrypt_data(plaintext: str) -> bytes:
    return public_key.encrypt(
        plaintext.encode(),
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(),
                     label=None)
    )

def decrypt_data(ciphertext: bytes) -> str:
    return private_key.decrypt(
        ciphertext,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(),
                     label=None)
    ).decode()

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def generate_unique_site_id(role):
    prefix = "F" if role.lower() == "faculty" else "S"
    while True:
        candidate = f"{prefix}{random.randint(100000, 999999)}"
        if not User.query.filter_by(site_id=candidate).first():
            return candidate

# JWT
def generate_jwt(site_id, role):
    payload = {
        "site_id": site_id,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXP_MINUTES)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        abort(401, description="Token expired")
    except jwt.InvalidTokenError:
        abort(401, description="Invalid token")

# Decorators for route protection
def jwt_required(role_required=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                abort(401, description="Missing or invalid JWT")
            token = auth_header.split(" ")[1]
            decoded = verify_jwt(token)
            if role_required and decoded["role"].lower() != role_required.lower():
                abort(403, description="Access denied: insufficient privileges")
            request.user = decoded
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Registration route
@app.route('/register', methods=['POST'])
def register():
    role = request.form.get("role", "student")
    site_id = generate_unique_site_id(role)
    password = request.form.get("password", "")
    hashed_password = hash_password(password)

    user = User(
        site_id=site_id,
        name=encrypt_data(request.form.get("name", "")),
        email=encrypt_data(request.form.get("email", "")),
        password=encrypt_data(hashed_password),
        colloegeid=encrypt_data(request.form.get("colloegeid", "")),
        role=encrypt_data(role),
        faculty_code=encrypt_data(request.form.get("faculty_code", "")) 
                      if role.lower() == "faculty" else None
    )

    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Account created successfully", "site_id": site_id}), 201

# Login route
@app.route('/login', methods=['POST'])
def login():
    email = request.form.get("email", "").lower()
    password = request.form.get("password", "")

    for user in User.query.all():
        decrypted_email = decrypt_data(user.email).lower()
        if decrypted_email == email:
            stored_hash = decrypt_data(user.password)
            if verify_password(password, stored_hash):
                role = decrypt_data(user.role)
                token = generate_jwt(user.site_id, role)
                return jsonify({"message": "Login successful", "site_id": user.site_id, "role": role, "token": token}), 200
            return jsonify({"error": "Invalid password"}), 401
    return jsonify({"error": "Account not found"}), 404

# Role-protected routes
@app.route('/student/dashboard', methods=['GET'])
@jwt_required(role_required="student")
def student_dashboard():
    user = request.user
    return jsonify({"message": f"Welcome Student {user['site_id']}! This area is for students only."})

@app.route('/faculty/dashboard', methods=['GET'])
@jwt_required(role_required="faculty")
def faculty_dashboard():
    user = request.user
    return jsonify({"message": f"Welcome Faculty {user['site_id']}! This area is restricted to faculty members."})

@app.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    user = request.user
    return jsonify({"message": f"Welcome {user['role']} {user['site_id']}! Your access token is valid."})

# Admin endpoints
@app.route('/admin/view_user/<site_id>', methods=['GET'])
def view_user(site_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or auth_header != f"Bearer {ADMIN_TOKEN}":
        abort(403, description="Forbidden: Invalid admin token")

    user = User.query.filter_by(site_id=site_id).first()
    if not user:
        abort(404, description="User not found")

    return jsonify({
        "site_id": user.site_id,
        "name": decrypt_data(user.name),
        "email": decrypt_data(user.email),
        "hashed_password": decrypt_data(user.password),
        "colloegeid": decrypt_data(user.colloegeid),
        "role": decrypt_data(user.role),
        "faculty_code": decrypt_data(user.faculty_code) if user.faculty_code else None
    })

@app.route('/admin/users', methods=['GET'])
def list_users():
    auth_header = request.headers.get("Authorization")
    if not auth_header or auth_header != f"Bearer {ADMIN_TOKEN}":
        abort(403, description="Forbidden: Invalid admin token")

    users = User.query.all()
    return jsonify({"users": [{"site_id": u.site_id, "role": decrypt_data(u.role)} for u in users]})

if __name__ == "__main__":
    app.run(debug=True)
