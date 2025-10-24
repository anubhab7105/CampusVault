from flask import Flask, jsonify, request
from flask_cors import CORS
from models import db, Student

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Initialize DB
with app.app_context():
    db.create_all()

@app.route("/api/profile/<int:user_id>", methods=["GET"])
def get_profile(user_id):
    student = Student.query.get(user_id)
    if not student:
        return jsonify({"error": "User not found"}), 404
    return jsonify(student.serialize())

@app.route("/api/profile/<int:user_id>", methods=["PUT"])
def update_profile(user_id):
    student = Student.query.get(user_id)
    if not student:
        return jsonify({"error": "User not found"}), 404

    data = request.json
    for field in [
        "name", "email", "phone", "role", "college", "department",
        "degree", "year", "registration", "github", "linkedin", "bio"
    ]:
        if field in data:
            setattr(student, field, data[field])

    if data.get("password"):
        student.set_password(data["password"])

    db.session.commit()
    return jsonify({"message": "Profile updated successfully"})

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    if Student.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 400

    student = Student(
        name=data["name"],
        email=data["email"],
        phone=data.get("phone", ""),
        role=data.get("role", "student"),
        college=data.get("college", ""),
        department=data.get("department", ""),
        degree=data.get("degree", ""),
        year=data.get("year", ""),
        registration=data.get("registration", ""),
        github=data.get("github", ""),
        linkedin=data.get("linkedin", ""),
        bio=data.get("bio", "")
    )
    student.set_password(data["password"])
    db.session.add(student)
    db.session.commit()
    return jsonify({"message": "Registered successfully", "id": student.id}), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    student = Student.query.filter_by(email=data["email"]).first()
    if not student or not student.check_password(data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401
    return jsonify({"message": "Login successful", "id": student.id})

if __name__ == "__main__":
    app.run(debug=True)
