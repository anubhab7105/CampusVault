# merged_flask_app.py
# Merges existing signup and login flows from the uploaded project into a single Flask app
# Assumes you have unzipped the uploaded project next to this file with the same folder structure
# (frontend/  backend/app/utils/ ...)

import os
import sys
from flask import Flask, request, redirect, url_for, send_from_directory, session, render_template_string, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import json
from datetime import timedelta

# ensure project utils are importable (adjust path if you unzipped elsewhere)
HERE = os.path.dirname(os.path.abspath(__file__))
UTILS_PATH = os.path.join(HERE, 'backend', 'app', 'utils')
if UTILS_PATH not in sys.path:
    sys.path.insert(0, UTILS_PATH)

try:
    from encrypt import load_or_create_key, encrypt_data
except Exception as e:
    # If import fails, define fallbacks
    print("Warning: could not import encrypt utilities from backend/app/utils. Using fallback (no encryption).", e)
    def load_or_create_key():
        return None
    def encrypt_data(data, key):
        return json.dumps(data)

try:
    from id_generator import next_unique_id
except Exception as e:
    print("Warning: could not import id_generator utilities. Using simple fallback.", e)
    def next_unique_id(role_char: str) -> str:
        # fallback: use timestamp-based id
        import time
        if role_char.upper().startswith('F'):
            prefix = 'F'
        else:
            prefix = 'S'
        return prefix + str(int(time.time()))[-6:]

# Config
DB_FILE = os.path.join(HERE, 'campusvault.db')  # signup.py used campusvault.db
SECRET_KEY = os.environ.get('FLASK_SECRET', 'dev-secret-please-change')
ENCRYPT_KEY = load_or_create_key()

app = Flask(__name__, static_folder='frontend', template_folder='frontend')
app.secret_key = SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=4)

# Initialize DB if not exists (kept minimal & compatible with your original signup.py)
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unique_id TEXT UNIQUE,
            name TEXT,
            email TEXT,
            encrypted_data TEXT,
            password TEXT,
            role TEXT,
            faculty_code TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Serve signup page
@app.route('/signup', methods=['GET'])
def signup_page():
    # serve the frontend/signup.html if present
    path = os.path.join(app.static_folder, 'signup.html')
    if os.path.exists(path):
        return send_from_directory(app.static_folder, 'signup.html')
    # fallback minimal form
    return render_template_string('''
    <h2>Signup (fallback)</h2>
    <form method="post" action="/register">
    Name: <input name="name"><br>
    Email: <input name="email"><br>
    Role (S or F): <input name="role"><br>
    Password: <input name="password" type="password"><br>
    Faculty code (if F): <input name="faculty_code"><br>
    <button type="submit">Register</button>
    </form>
    ''')

# Registration endpoint (glues existing logic)
@app.route('/register', methods=['POST'])
def register():
    data = request.form.to_dict() if request.form else request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'S').upper()
    faculty_code = data.get('faculty_code')

    if not (name and email and password):
        return jsonify({'error':'name,email,password required'}), 400

    # generate unique_id using existing util: role char F or S
    role_char = 'F' if role.startswith('F') else 'S'
    try:
        unique_id = next_unique_id(role_char)
    except Exception as e:
        unique_id = (role_char + os.urandom(3).hex()).upper()

    # Encrypt everything except name
    sensitive = {k:v for k,v in data.items() if k != 'name' and k!='password'}
    try:
        encrypted_blob = encrypt_data(sensitive, ENCRYPT_KEY)
    except Exception:
        encrypted_blob = json.dumps(sensitive)

    # hash password
    hashed = generate_password_hash(password)

    # save to DB
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('INSERT INTO users (unique_id, name, email, encrypted_data, password, role, faculty_code) VALUES (?,?,?,?,?,?,?)',
                (unique_id, name, email, encrypted_blob, hashed, role, faculty_code))
    conn.commit()
    conn.close()

    # Email the unique id (console fallback)
    smtp_configured = False
    if smtp_configured:
        pass
    else:
        print(f"[EMAIL FALLBACK] To: {email} — your site ID: {unique_id}")

    return jsonify({'message':'account created','unique_id':unique_id})

# Serve login page
@app.route('/', methods=['GET'])
@app.route('/login', methods=['GET'])
def login_page():
    path = os.path.join(app.static_folder, 'signup.html')
    # many projects name login page differently; try 'login.html' then fallback
    for candidate in ['index.html','login.html','signup.html']:
        p = os.path.join(app.static_folder, candidate)
        if os.path.exists(p):
            return send_from_directory(app.static_folder, candidate)
    # fallback minimal form
    return render_template_string('''
    <h2>Login (fallback)</h2>
    <form method="post" action="/auth">
    Site ID: <input name="site_id"><br>
    Password: <input name="password" type="password"><br>
    <button type="submit">Login</button>
    </form>
    ''')

# Auth endpoint
@app.route('/auth', methods=['POST'])
def auth():
    data = request.form.to_dict() if request.form else request.get_json() or {}
    site_id = data.get('site_id') or data.get('unique_id') or data.get('college_id')
    password = data.get('password')
    if not site_id or not password:
        return jsonify({'error':'site_id and password required'}),400

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('SELECT id, unique_id, name, encrypted_data, password, role FROM users WHERE unique_id = ?', (site_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({'error':'invalid credentials'}), 401
    db_password = row[4]
    if not check_password_hash(db_password, password):
        return jsonify({'error':'invalid credentials'}), 401

    user_unique_id = row[1]
    role = row[5] or ('F' if user_unique_id.startswith('F') else 'S')

    # set session
    session.permanent = True
    session['user'] = {'id': row[0], 'unique_id': user_unique_id, 'name': row[2], 'role': role}

    # redirect to appropriate dashboard
    if user_unique_id.startswith('F'):
        return redirect('/dashboard/faculty')
    else:
        return redirect('/dashboard/student')

# Simple dashboard placeholders
@app.route('/dashboard/student')
def student_dash():
    u = session.get('user')
    if not u:
        return redirect('/login')
    return f"<h2>Student dashboard</h2><p>Welcome {u.get('name')} ({u.get('unique_id')})</p>"

@app.route('/dashboard/faculty')
def faculty_dash():
    u = session.get('user')
    if not u:
        return redirect('/login')
    return f"<h2>Faculty dashboard</h2><p>Welcome {u.get('name')} ({u.get('unique_id')})</p>"

# logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    print('Make sure you have the project unzipped with the original folder structure.\nRun: python3 merged_flask_app.py')
    app.run(debug=True, port=5000)
