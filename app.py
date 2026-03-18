from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='.')
app.secret_key = 'super-secret-key-password-system' # Em produção, usar algo seguro
CORS(app)

DATABASE = 'database.db'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
ALLOWED_EXTENSIONS_IMG = {'png', 'jpg', 'jpeg', 'svg'}

# Create upload folder if not exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

import socket

def init_db():
    conn = get_db_connection()
    # Passwords table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            number INTEGER NOT NULL,
            guiche TEXT,
            patient_name TEXT,
            patient_cpf TEXT,
            patient_birth TEXT,
            destination_service TEXT,
            status TEXT DEFAULT 'PENDING',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            called_at DATETIME
        )
    ''')
    # Users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'operator'
        )
    ''')
    # Settings table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Default settings
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('print_mode', 'simulate')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('printer_ip', '192.168.1.100')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('service_rooms', 'Serviço Social, Farmácia, Consultório Médico, Sala de Vacina, Ouvidoria')")
    
    # Create default admin if not exists
    admin = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if not admin:
        conn.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            ('admin', generate_password_hash('admin123', method='pbkdf2:sha256'), 'admin')
        )
    
    conn.commit()
    conn.close()

def get_config_value(key, default=None):
    conn = get_db_connection()
    row = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    conn.close()
    return row['value'] if row else default

def print_thermal_ticket(ticket):
    mode = get_config_value('print_mode', 'simulate')
    if mode != 'network':
        return False
    
    ip = get_config_value('printer_ip')
    if not ip:
        return False

    try:
        # ESC/POS commands
        # INIT: \x1b\x40
        # CENTER: \x1b\x61\x01
        # LARGE FONT: \x1d\x21\x11
        # FEED & CUT: \x1d\x56\x42\x00
        
        types = {'G': 'GERAL', 'P': 'PREFERENCIAL', 'O': 'OUVIDORIA'}
        t_type = types.get(ticket['type'], ticket['type'])
        t_num = f"{ticket['type']}{ticket['number']:03d}"
        t_date = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        raw = b"\x1b\x40" # Initialize
        raw += b"\x1b\x61\x01" # Center
        raw += b"PREFEITURA DE PAULO AFONSO\n\n"
        raw += b"\x1d\x21\x11" # Double size
        raw += f"SENHA: {t_num}\n\n".encode('ascii')
        raw += b"\x1d\x21\x00" # Normal size
        raw += f"TIPO: {t_type}\n".encode('ascii')
        raw += f"DATA: {t_date}\n\n".encode('ascii')
        raw += b"Por favor, aguarde ser chamado.\n\n\n\n"
        raw += b"\x1d\x56\x42\x00" # Cut paper

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((ip, 9100)) # Default port for thermal prints
            s.sendall(raw)
        return True
    except Exception as e:
        print(f"Erro na impressora ({ip}): {e}")
        return False

init_db()

# AUTH HELPERS
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ROUTES
@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/<path:path>')
def serve_static(path):
    # If the file exists in current dir, serve it. Otherwise let it fail.
    return send_from_directory('.', path)

# AUTH API
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({
            'id': user['id'],
            'username': user['username'],
            'role': user['role']
        })
    
    return jsonify({'error': 'Credenciais inválidas'}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'})

@app.route('/api/auth/me', methods=['GET'])
def me():
    if 'user_id' in session:
        return jsonify({
            'id': session['user_id'],
            'username': session['username'],
            'role': session['role']
        })
    return jsonify({'error': 'Not logged in'}), 401

# USERS API
@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    conn = get_db_connection()
    users = conn.execute('SELECT id, username, role FROM users').fetchall()
    conn.close()
    return jsonify([dict(row) for row in users])

@app.route('/api/users', methods=['POST'])
@login_required
def create_user():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'operator')
    
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            (username, generate_password_hash(password, method='pbkdf2:sha256'), role)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Usuário já existe'}), 400
    finally:
        conn.close()
    
    return jsonify({'message': 'Usuário criado'})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Usuário removido'})

# FILE UPLOAD
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_IMG

@app.route('/api/config/logo', methods=['POST'])
@login_required
def upload_logo():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
    if file and allowed_image(file.filename):
        try:
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"system_logo.{ext}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            print(f"DEBUG: Saving logo to {filepath}")
            
            # Ensure directory exists one more time
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
                
            file.save(filepath)
            print("DEBUG: Logo saved successfully to disk")
            
            # Update settings in DB
            val = f"/uploads/{filename}"
            conn = get_db_connection()
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('system_logo', ?)", (val,))
            conn.commit()
            conn.close()
            
            return jsonify({'message': 'Logo atualizada com sucesso', 'url': val})
        except Exception as e:
            print(f"ERROR UPLOADING LOGO: {str(e)}")
            return jsonify({'error': f"Erro interno: {str(e)}"}), 500
            
    return jsonify({'error': 'Extensão não permitida'}), 400

@app.route('/api/config/upload-video', methods=['POST'])
@login_required
def upload_video():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({'filename': filename})
    return jsonify({'error': 'Formato não permitido'}), 400

# SETTINGS API
@app.route('/api/config/settings', methods=['GET'])
@login_required
def get_settings():
    conn = get_db_connection()
    rows = conn.execute('SELECT key, value FROM settings').fetchall()
    conn.close()
    return jsonify({row['key']: row['value'] for row in rows})

@app.route('/api/config/settings', methods=['POST'])
@login_required
def update_settings():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    
    data = request.json
    conn = get_db_connection()
    for key, value in data.items():
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Configurações atualizadas'})

@app.route('/api/public-settings', methods=['GET'])
def get_public_settings():
    conn = get_db_connection()
    # Safely get required keys
    keys = ('print_mode', 'service_rooms', 'system_logo')
    placeholders = ','.join('?' * len(keys))
    query = f"SELECT key, value FROM settings WHERE key IN ({placeholders})"
    rows = conn.execute(query, keys).fetchall()
    conn.close()
    
    settings = {row['key']: row['value'] for row in rows}
    # Ensure defaults if missing
    if 'print_mode' not in settings: settings['print_mode'] = 'simulate'
    if 'service_rooms' not in settings: settings['service_rooms'] = ''
    if 'system_logo' not in settings: settings['system_logo'] = 'logo.png'
    
    return jsonify(settings)

# PREVIOUS PASSWORDS API (PROTECTED)
@app.route('/api/passwords', methods=['POST'])
def create_password(): # Keep public for totem
    data = request.json
    p_type = data.get('type')
    conn = get_db_connection()
    last = conn.execute('SELECT MAX(number) as last_num FROM passwords WHERE type = ? AND date(created_at) = date("now", "localtime")', (p_type,)).fetchone()
    next_num = (last['last_num'] or 0) + 1
    cursor = conn.execute(
        'INSERT INTO passwords (type, number, created_at) VALUES (?, ?, ?)',
        (p_type, next_num, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    new_id = cursor.lastrowid
    conn.commit()
    password = conn.execute('SELECT * FROM passwords WHERE id = ?', (new_id,)).fetchone()
    conn.close()
    
    # Try thermal print if enabled
    password_dict = dict(password)
    print_thermal_ticket(password_dict)
    
    return jsonify(password_dict)

@app.route('/api/passwords/<int:p_id>/forward', methods=['PATCH'])
@login_required
def forward_password(p_id):
    data = request.json
    conn = get_db_connection()
    conn.execute('''
        UPDATE passwords 
        SET patient_name = ?, patient_cpf = ?, patient_birth = ?, 
            destination_service = ?, status = 'FORWARDED'
        WHERE id = ?
    ''', (data.get('name'), data.get('cpf'), data.get('birth'), data.get('service'), p_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Encaminhado com sucesso'})

@app.route('/api/service-queue', methods=['GET'])
def get_service_queue():
    service = request.args.get('service')
    conn = get_db_connection()
    # Allow FORWARDED and CALLED_SPECIALIST so they stay in the specialist's list
    query = "SELECT * FROM passwords WHERE status IN ('FORWARDED', 'CALLED_SPECIALIST')"
    params = []
    if service:
        query += " AND destination_service = ?"
        params.append(service)
    
    query += " ORDER BY created_at ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/passwords/<int:p_id>/call-specialist', methods=['PATCH'])
@login_required
def call_specialist(p_id):
    conn = get_db_connection()
    conn.execute("UPDATE passwords SET status = 'CALLED_SPECIALIST', called_at = datetime('now', 'localtime') WHERE id = ?", (p_id,))
    password = conn.execute("SELECT * FROM passwords WHERE id = ?", (p_id,)).fetchone()
    conn.commit()
    conn.close()
    return jsonify(dict(password))

@app.route('/api/passwords/<int:p_id>/complete', methods=['PATCH'])
@login_required
def complete_password(p_id):
    conn = get_db_connection()
    conn.execute("UPDATE passwords SET status = 'COMPLETED', served_at = datetime('now', 'localtime') WHERE id = ?", (p_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Atendimento concluído'})

@app.route('/api/passwords/<int:p_id>/call', methods=['PATCH'])
@login_required
def call_password(p_id):
    data = request.json
    guiche = data.get('guiche')
    conn = get_db_connection()
    conn.execute(
        'UPDATE passwords SET called_at = ?, guiche = ? WHERE id = ?',
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), guiche, p_id)
    )
    conn.commit()
    password = conn.execute('SELECT * FROM passwords WHERE id = ?', (p_id,)).fetchone()
    conn.close()
    return jsonify(dict(password))

@app.route('/api/queue', methods=['GET'])
def get_queue(): # Public for syncing
    conn = get_db_connection()
    queue = conn.execute('SELECT * FROM passwords WHERE called_at IS NULL AND date(created_at) = date("now", "localtime") ORDER BY id ASC').fetchall()
    conn.close()
    return jsonify([dict(row) for row in queue])

@app.route('/api/history', methods=['GET'])
def get_history():
    conn = get_db_connection()
    history = conn.execute('SELECT * FROM passwords WHERE called_at IS NOT NULL AND date(created_at) = date("now", "localtime") ORDER BY called_at DESC LIMIT 10').fetchall()
    conn.close()
    return jsonify([dict(row) for row in history])

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    conn = get_db_connection()
    totals = conn.execute('SELECT type, COUNT(*) as count FROM passwords WHERE date(created_at) = date("now", "localtime") GROUP BY type').fetchall()
    avg_wait = conn.execute('''
        SELECT AVG(strftime('%s', called_at) - strftime('%s', created_at)) as avg_seconds
        FROM passwords 
        WHERE called_at IS NOT NULL AND date(created_at) = date("now", "localtime")
    ''').fetchone()
    hourly = conn.execute("SELECT strftime('%H', created_at) as hour, COUNT(*) as count FROM passwords WHERE date(created_at) = date('now', 'localtime') GROUP BY hour").fetchall()
    by_service = conn.execute("SELECT destination_service, COUNT(*) as count FROM passwords WHERE destination_service IS NOT NULL AND date(created_at) = date('now', 'localtime') GROUP BY destination_service").fetchall()
    conn.close()
    return jsonify({
        'totals': {row['type']: row['count'] for row in totals},
        'avg_wait_seconds': avg_wait['avg_seconds'] or 0,
        'hourly': {row['hour']: row['count'] for row in hourly},
        'by_service': {row['destination_service']: row['count'] for row in by_service}
    })

@app.route('/api/reports', methods=['GET'])
@login_required
def get_reports_data():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    p_type = request.args.get('type')
    service = request.args.get('service')
    
    query = "SELECT * FROM passwords WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND date(created_at) >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date(created_at) <= ?"
        params.append(end_date)
    if p_type:
        query += " AND type = ?"
        params.append(p_type)
    if service:
        query += " AND destination_service = ?"
        params.append(service)
        
    query += " ORDER BY created_at DESC LIMIT 1000"
    
    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in rows])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4001, debug=True)
