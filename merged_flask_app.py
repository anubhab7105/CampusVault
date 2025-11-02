# merged_flask_app.py
# Merges signup/login flows into a single Flask app (dev-ready)
import os
import sys
import sqlite3
import json
import time
from datetime import timedelta
from flask import (
    Flask, request, redirect, url_for, send_from_directory,
    session, render_template_string, render_template, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------------
# Utilities import (optional)
# -------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
UTILS_PATH = os.path.join(HERE, 'backend', 'app', 'utils')
if UTILS_PATH not in sys.path:
    sys.path.insert(0, UTILS_PATH)

try:
    from encrypt import load_or_create_key, encrypt_data
except Exception as e:
    # fallback: no encryption, but keep API
    print("Warning: couldn't import encrypt utilities — using fallback (no encryption).", e)
    def load_or_create_key():
        return None
    def encrypt_data(data, key):
        return json.dumps(data)

# -------------------------
# Lazy import for id_generator to avoid circular import issues
# -------------------------
def _try_import_next_unique_id():
    try:
        from id_generator import next_unique_id as _nuid
        return _nuid
    except Exception as e:
        # print a concise message; fallback will be used when needed
        print("Warning: could not import id_generator — will use fallback when needed.", e)
        return None

_next_unique_id_func = _try_import_next_unique_id()

def next_unique_id(role_char: str) -> str:
    """
    Tries the real id_generator.next_unique_id if available,
    otherwise uses the fallback implementation.
    """
    if _next_unique_id_func:
        try:
            return _next_unique_id_func(role_char)
        except Exception as e:
            print("Warning: id_generator.next_unique_id raised; falling back.", e)
    # fallback implementation: deterministic-ish short id
    prefix = 'F' if str(role_char).upper().startswith('F') else 'S'
    return f"{prefix}{int(time.time()) % 1000000:06d}"

# -------------------------
# Paths & Flask initialization
# -------------------------
FRONTEND_PATH = os.path.join(HERE, 'frontend')                    # static files root
TEMPLATE_PATH = os.path.join(FRONTEND_PATH, 'templates')         # templates root (your current layout)

# Check .env contents (simple validator) so Python-dotenv warnings can be acted on
ENV_PATH = os.path.join(HERE, '.env')
if os.path.exists(ENV_PATH):
    try:
        with open(ENV_PATH, 'r', encoding='utf-8') as f:
            lines = [ln.rstrip('\n') for ln in f.readlines()]
        bad_lines = []
        for i, ln in enumerate(lines, start=1):
            s = ln.strip()
            # ignore empty lines and comments
            if not s or s.startswith('#'):
                continue
            if '=' not in s:
                bad_lines.append((i, ln))
        if bad_lines:
            print("Warning: .env contains lines that are not KEY=VALUE. Fix or rename .env to silence this.")
            for ln_no, ln_text in bad_lines:
                print(f"  line {ln_no}: {ln_text}")
    except Exception as e:
        print("Warning: could not read .env for validation.", e)

# Debug prints so you can see what's being used at startup
print("CWD:", os.getcwd())
print("HERE:", HERE)
print("FRONTEND_PATH:", FRONTEND_PATH)
print("TEMPLATE_PATH:", TEMPLATE_PATH)
print("frontend exists?:", os.path.exists(FRONTEND_PATH))
print("templates exists?:", os.path.exists(TEMPLATE_PATH))
if os.path.exists(FRONTEND_PATH):
    print("frontend dir listing (top-level):")
    try:
        for entry in sorted(os.listdir(FRONTEND_PATH)):
            print("  ", entry)
    except Exception:
        pass
if os.path.exists(TEMPLATE_PATH):
    print("templates dir listing (top-level):")
    try:
        for entry in sorted(os.listdir(TEMPLATE_PATH)):
            print("  ", entry)
    except Exception:
        pass

# -------------------------
# Config
# -------------------------
DB_FILE = os.path.join(HERE, 'campusvault.db')
SECRET_KEY = os.environ.get('FLASK_SECRET', 'dev-secret-please-change')
ENCRYPT_KEY = load_or_create_key()

# initialize Flask with absolute paths:
# - static_folder serves JS/CSS/images from frontend/
# - template_folder points to frontend/templates/
app = Flask(__name__, static_folder=FRONTEND_PATH, template_folder=TEMPLATE_PATH)
app.secret_key = SECRET_KEY
app.config.update({
    'PERMANENT_SESSION_LIFETIME': timedelta(hours=4),
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',   # consider 'Strict' if suitable
    # 'SESSION_COOKIE_SECURE': True,    # enable in production (requires HTTPS)
})

# -------------------------
# DB init
# -------------------------
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute('''
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
        # Optionally enforce email uniqueness:
        # cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        conn.commit()

init_db()

# -------------------------
# Helper: open connection (row access if needed)
# -------------------------
def get_db_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = None
    return conn

# -------------------------
# Serve signup page
# -------------------------
@app.route('/signup', methods=['GET'])
def signup_page():
    # Render from template folder if present
    signup_template = os.path.join(app.template_folder or TEMPLATE_PATH, 'signup.html')
    if os.path.exists(signup_template):
        return render_template('signup.html')
    # Fallback: check static_folder (in case template was put at frontend/)
    static_candidate = os.path.join(app.static_folder or FRONTEND_PATH, 'signup.html')
    if os.path.exists(static_candidate):
        return send_from_directory(app.static_folder, 'signup.html')
    # final fallback HTML
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

# -------------------------
# Registration endpoint
# -------------------------
@app.route('/register', methods=['POST'])
def register():
    # Accept form or JSON
    data = request.form.to_dict() if request.form else (request.get_json() or {})
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password')
    role_raw = (data.get('role') or 'S').strip().upper()
    faculty_code = data.get('faculty_code') or None

    if not (name and email and password):
        return jsonify({'error': 'name, email, and password are required'}), 400

    # Normalize role to 'F' or 'S'
    role = 'F' if role_raw.startswith('F') else 'S'

    # Generate unique_id (try util then fallback)
    role_char = 'F' if role == 'F' else 'S'
    try:
        unique_id = next_unique_id(role_char)
    except Exception:
        unique_id = (role_char + os.urandom(3).hex()).upper()

    # Sensitive data to encrypt (exclude plain name & password)
    sensitive = {k: v for k, v in data.items() if k not in ('name', 'password')}
    try:
        encrypted_blob = encrypt_data(sensitive, ENCRYPT_KEY)
    except Exception:
        encrypted_blob = json.dumps(sensitive)

    hashed = generate_password_hash(password)

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                'INSERT INTO users (unique_id, name, email, encrypted_data, password, role, faculty_code) VALUES (?,?,?,?,?,?,?)',
                (unique_id, name, email, encrypted_blob, hashed, role, faculty_code)
            )
            conn.commit()
    except sqlite3.IntegrityError as ie:
        # could be duplicate unique_id or (if enabled) duplicate email
        return jsonify({'error': 'account could not be created (duplicate?)', 'details': str(ie)}), 409
    except Exception as e:
        return jsonify({'error': 'internal server error', 'details': str(e)}), 500

    # DEV fallback for email sending
    smtp_configured = False
    if smtp_configured:
        # put email-send logic here
        pass
    else:
        print(f"[EMAIL FALLBACK] To: {email} — your site ID: {unique_id}")

    return jsonify({'message': 'account created', 'unique_id': unique_id}), 201

# -------------------------
# Root redirect to signup (explicit)
# -------------------------
@app.route('/', methods=['GET'])
def root():
    return redirect('/signup')

# -------------------------
# Serve login page (index/login)
# -------------------------
@app.route('/login', methods=['GET'])
def login_page():
    # try common template filenames in the templates folder first
    candidates = ['signup.html', 'index.html', 'login.html', 'sign_in.html']
    for candidate in candidates:
        template_candidate = os.path.join(app.template_folder or TEMPLATE_PATH, candidate)
        if os.path.exists(template_candidate):
            return render_template(candidate)

    # fallback to static folder (in case template was placed at frontend/)
    for candidate in candidates:
        static_candidate = os.path.join(app.static_folder or FRONTEND_PATH, candidate)
        if os.path.exists(static_candidate):
            return send_from_directory(app.static_folder, candidate)

    # final fallback HTML
    return render_template_string('''
    <h2>Login (fallback)</h2>
    <form method="post" action="/auth">
      Site ID: <input name="site_id"><br>
      Password: <input name="password" type="password"><br>
      <button type="submit">Login</button>
    </form>
    ''')

# -------------------------
# Auth endpoint
# -------------------------
@app.route('/auth', methods=['POST'])
def auth():
    data = request.form.to_dict() if request.form else (request.get_json() or {})
    site_id = (data.get('site_id') or data.get('unique_id') or data.get('college_id') or '').strip()
    password = data.get('password')

    if not site_id or not password:
        return jsonify({'error': 'site_id and password required'}), 400

    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute('SELECT id, unique_id, name, encrypted_data, password, role FROM users WHERE unique_id = ?', (site_id,))
        row = cur.fetchone()
        conn.close()
    except Exception as e:
        return jsonify({'error': 'internal server error', 'details': str(e)}), 500

    if not row:
        return jsonify({'error': 'invalid credentials'}), 401

    db_password = row[4]
    if not check_password_hash(db_password, password):
        return jsonify({'error': 'invalid credentials'}), 401

    user_unique_id = row[1]
    role = row[5] or ('F' if str(user_unique_id).startswith('F') else 'S')

    session.permanent = True
    session['user'] = {'id': row[0], 'unique_id': user_unique_id, 'name': row[2], 'role': role}

    # redirect to dashboard (simple behavior)
    if str(user_unique_id).startswith('F'):
        return redirect('/dashboard/faculty')
    else:
        return redirect('/dashboard/student')

# -------------------------
# Simple dashboards
# -------------------------
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

# -------------------------
# logout
# -------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# -------------------------
# Run
# -------------------------
if __name__ == '__main__':
    print('Run: python3 merged_flask_app.py')
    # debug True is fine for local dev, but disable in production
    app.run(debug=True, port=5000)
