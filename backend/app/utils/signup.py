from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash
import sqlite3

app = Flask(__name__)
CORS(app)  # Allows frontend requests

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect('campusvault.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            college_id TEXT NOT NULL,
            role TEXT NOT NULL,
            faculty_code TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---------- SIGNUP ROUTE ----------
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    college_id = data.get('colloegeid')   # same name as in your HTML
    role = data.get('role')
    faculty_code = data.get('faculty_code', None)

    # Basic validation
    if not all([name, email, password, college_id, role]):
        return jsonify({"error": "All required fields must be filled."}), 400

    # Faculty verification (optional)
    if role == "faculty" and faculty_code != "FACULTY2025":
        return jsonify({"error": "Invalid faculty verification code."}), 403

    # Hash password before saving
    hashed_password = generate_password_hash(password)

    try:
        conn = sqlite3.connect('campusvault.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (name, email, password, college_id, role, faculty_code)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, email, hashed_password, college_id, role, faculty_code))
        conn.commit()
        conn.close()
        return jsonify({"message": "Account created successfully!"}), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already registered."}), 409

# ---------- RUN SERVER ----------
if __name__ == '__main__':
    app.run(debug=True)
