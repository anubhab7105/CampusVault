from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
CORS(app)  # Allow frontend JS to access backend API

# ---------- Database Setup ----------
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            siteid TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# ---------- Signup ----------
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    siteid = data.get('siteid')
    password = data.get('password')

    if not siteid or not password:
        return jsonify({"error": "All fields are required"}), 400

    hashed_pw = generate_password_hash(password)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users (siteid, password) VALUES (?, ?)", (siteid, hashed_pw))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "User ID already exists"}), 400

    conn.close()
    return jsonify({"message": "Signup successful!"}), 201

# ---------- Login ----------
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    siteid = data.get('siteid')
    password = data.get('password')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE siteid = ?", (siteid,))
    user = c.fetchone()
    conn.close()

    if user and check_password_hash(user[0], password):
        return jsonify({"message": "Login successful!"}), 200
    else:
        return jsonify({"error": "Invalid User ID or Password"}), 401


# ---------- Initialize ----------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
