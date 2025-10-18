from flask import Flask, request, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import re
import os

# --------------------------------------------
# Flask app configuration
# --------------------------------------------
app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'users.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --------------------------------------------
# Database model
# --------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    college_id = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student' or 'faculty'

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


# --------------------------------------------
# Utility functions
# --------------------------------------------
def validate_password(password):
    """
    Password must have:
      - Minimum 8 characters
      - At least one uppercase letter
      - At least one lowercase letter
      - At least one digit
      - At least one special character
    """
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return "Password must contain at least one digit."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must contain at least one special character."
    return None


# --------------------------------------------
# Routes
# --------------------------------------------

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()

    # Extract fields
    email = data.get('email')
    password = data.get('password')
    college_id = data.get('college_id')
    role = data.get('role')

    # Validate input
    if not all([email, password, college_id, role]):
        return jsonify({"error": "All fields (email, password, college_id, role) are required."}), 400

    if role.lower() not in ["student", "faculty"]:
        return jsonify({"error": "Role must be either 'student' or 'faculty'."}), 400

    # Check if email exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Email already registered. Please log in."}), 400

    # Validate password strength
    password_error = validate_password(password)
    if password_error:
        return jsonify({"error": password_error}), 400

    # Hash password
    hashed_password = generate_password_hash(password)

    # Create user
    new_user = User(
        email=email,
        password_hash=hashed_password,
        college_id=college_id,
        role=role.lower()
    )
    db.session.add(new_user)
    db.session.commit()

    # Redirect to respective dashboard
    if role.lower() == "student":
        return redirect("/dashboard/student", code=302)
    else:
        return redirect("/dashboard/faculty", code=302)


# --------------------------------------------
# Initialize database
# --------------------------------------------
@app.before_first_request
def create_tables():
    db.create_all()


# --------------------------------------------
# Run server
# --------------------------------------------
if __name__ == "__main__":
    print("🚀 Signup API running on http://127.0.0.1:5000")
    app.run(debug=True)
