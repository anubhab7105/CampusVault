from flask import Flask, request, jsonify, send_from_directory, g
import sqlite3, os, datetime, bcrypt

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, 'static_uploads')
DB_PATH = os.path.join(BASE_DIR, '..', 'online_library.sqlite3')

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
app.config['DB_PATH'] = DB_PATH
app.config['SECRET_KEY'] = 'change-me-in-prod'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DB_PATH'], check_same_thread=False)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        unique_id TEXT UNIQUE,
        name TEXT,
        email TEXT UNIQUE,
        password_hash TEXT,
        role TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS uploads (
        id INTEGER PRIMARY KEY,
        faculty_unique_id TEXT,
        filename TEXT,
        title TEXT,
        description TEXT,
        uploaded_at TEXT
    );
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY,
        upload_id INTEGER,
        title TEXT,
        content TEXT,
        created_by TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY,
        sender_unique_id TEXT,
        subject TEXT,
        message TEXT,
        created_at TEXT,
        status TEXT DEFAULT 'open'
    );
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY,
        sender_unique_id TEXT,
        receiver_unique_id TEXT,
        message TEXT,
        context_type TEXT,
        context_id INTEGER,
        created_at TEXT
    );
    ''')
    db.commit()

def generate_unique_id(role):
    db = get_db()
    cur = db.cursor()
    prefix = 'F' if role=='faculty' else ('S' if role=='student' else 'A')
    cur.execute("SELECT unique_id FROM users WHERE unique_id LIKE ? ORDER BY id DESC LIMIT 1", (prefix + '%',))
    row = cur.fetchone()
    if row and row['unique_id']:
        try:
            num = int(row['unique_id'][1:]) + 1
        except:
            num = 1
    else:
        num = 1
    return f"{prefix}{num:06d}"

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json or {}
    name = data.get('name') or 'Unknown'
    email = data.get('email')
    password = data.get('password')
    role = data.get('role','student')
    if not email or not password:
        return jsonify({'error':'email & password required'}), 400
    db = get_db()
    cur = db.cursor()
    try:
        unique_id = generate_unique_id(role)
        pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("INSERT INTO users (unique_id,name,email,password_hash,role,created_at) VALUES (?,?,?,?,?,?)",
                    (unique_id,name,email,pw,role,datetime.datetime.utcnow().isoformat()))
        db.commit()
        return jsonify({'ok':True,'unique_id':unique_id})
    except Exception as e:
        return jsonify({'error':str(e)}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    email = data.get('email'); password = data.get('password')
    if not email or not password:
        return jsonify({'error':'email & password required'}), 400
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE email=?",(email,))
    row = cur.fetchone()
    if not row:
        return jsonify({'error':'invalid'}), 401
    stored = row['password_hash']
    try:
        ok = bcrypt.checkpw(password.encode('utf-8'), stored.encode('utf-8'))
    except Exception:
        return jsonify({'error':'password check error'}), 500
    if ok:
        # NOTE: demo simple response: return user info (in prod use secure sessions/JWT)
        return jsonify({'ok':True,'unique_id':row['unique_id'],'role':row['role'],'name':row['name']})
    return jsonify({'error':'invalid'}), 401

@app.route('/api/uploads', methods=['GET','POST'])
def uploads():
    db = get_db(); cur = db.cursor()
    if request.method=='GET':
        cur.execute("SELECT id,faculty_unique_id,filename,title,uploaded_at FROM uploads ORDER BY uploaded_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
        return jsonify(rows)
    # POST - file upload (faculty only in real app; demo allows any)
    if 'file' not in request.files:
        return jsonify({'error':'no file'}), 400
    f = request.files['file']
    title = request.form.get('title') or f.filename
    safe_name = f.filename.replace(' ','_')
    ts = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
    outname = f"{ts}_{safe_name}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], outname)
    f.save(save_path)
    # For demo, we record a faculty_unique_id placeholder
    faculty_id = request.form.get('faculty_unique_id') or 'F000001'
    cur.execute("INSERT INTO uploads (faculty_unique_id,filename,title,uploaded_at) VALUES (?,?,?,?)",
                (faculty_id,outname,title,datetime.datetime.utcnow().isoformat()))
    upload_id = cur.lastrowid
    # create a notice entry automatically
    cur.execute("INSERT INTO notices (upload_id,title,content,created_by,created_at) VALUES (?,?,?,?,?)",
                (upload_id,f"New upload: {title}", f"{title} uploaded by {faculty_id}", faculty_id, datetime.datetime.utcnow().isoformat()))
    db.commit()
    return jsonify({'ok':True,'id':upload_id,'filename':outname,'title':title})

@app.route('/api/notices', methods=['GET'])
def notices():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT id,upload_id,title,content,created_by,created_at FROM notices ORDER BY created_at DESC LIMIT 50")
    return jsonify([dict(r) for r in cur.fetchall()])

@app.route('/api/complaints', methods=['POST','GET'])
def complaints():
    db = get_db(); cur = db.cursor()
    if request.method=='POST':
        data = request.json or {}
        subject = data.get('subject'); message = data.get('message')
        sender = data.get('sender_unique_id') or 'S000001'
        cur.execute("INSERT INTO complaints (sender_unique_id,subject,message,created_at) VALUES (?,?,?,?)",
                    (sender,subject,message,datetime.datetime.utcnow().isoformat()))
        db.commit()
        return jsonify({'ok':True,'id':cur.lastrowid})
    cur.execute("SELECT * FROM complaints ORDER BY created_at DESC")
    return jsonify([dict(r) for r in cur.fetchall()])

@app.route('/api/chat/history', methods=['GET'])
def chat_history():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT id,sender_unique_id,receiver_unique_id,message,context_type,context_id,created_at FROM chat_messages ORDER BY id DESC LIMIT 200")
    rows = [dict(r) for r in cur.fetchall()]
    return jsonify(list(reversed(rows)))

@app.route('/api/chat/send', methods=['POST'])
def chat_send():
    data = request.json or {}
    sender = data.get('sender_unique_id') or 'S000001'
    receiver = data.get('to_unique_id')  # nullable
    message = data.get('message') or ''
    context_type = data.get('context_type')
    context_id = data.get('context_id')
    db = get_db(); cur = db.cursor()
    cur.execute("INSERT INTO chat_messages (sender_unique_id,receiver_unique_id,message,context_type,context_id,created_at) VALUES (?,?,?,?,?,?)",
                (sender,receiver,message,context_type,context_id,datetime.datetime.utcnow().isoformat()))
    db.commit()
    return jsonify({'ok':True,'id':cur.lastrowid})

@app.route('/uploads/<path:filename>')
def serve_file(filename):
    # serve uploaded files (demo). In production protect this route.
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    init_db()
    # create a demo admin and demo users if not exist
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT * FROM users LIMIT 1")
    if not cur.fetchone():
        pw = bcrypt.hashpw('adminpass'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("INSERT INTO users (unique_id,name,email,password_hash,role,created_at) VALUES (?,?,?,?,?,?)",
                    ('A000001','Admin','admin@college.edu',pw,'admin',datetime.datetime.utcnow().isoformat()))
        pw2 = bcrypt.hashpw('facpass'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("INSERT INTO users (unique_id,name,email,password_hash,role,created_at) VALUES (?,?,?,?,?,?)",
                    ('F000001','Prof Demo','prof@college.edu',pw2,'faculty',datetime.datetime.utcnow().isoformat()))
        pw3 = bcrypt.hashpw('studpass'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("INSERT INTO users (unique_id,name,email,password_hash,role,created_at) VALUES (?,?,?,?,?,?)",
                    ('S000001','Student Demo','student@college.edu',pw3,'student',datetime.datetime.utcnow().isoformat()))
        db.commit()
    print('Starting Flask dev server on http://127.0.0.1:8000')
    app.run(host='0.0.0.0', port=8000, debug=True)
