import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import json
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

# PostgreSQLの条件付きimport
try:
    import psycopg2
    POSTGRESQL_AVAILABLE = True
    print("✅ PostgreSQL driver available")
except ImportError:
    POSTGRESQL_AVAILABLE = False
    print("❌ PostgreSQL driver not available - using SQLite only")

import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fe-exam-app-secret-key-change-in-production')

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and POSTGRESQL_AVAILABLE:
    app.config['DATABASE_TYPE'] = 'postgresql'
    app.config['DATABASE_URL'] = DATABASE_URL
    print("✅ Using PostgreSQL database")
else:
    app.config['DATABASE_TYPE'] = 'sqlite'
    app.config['DATABASE'] = 'fe_exam.db'
    print("✅ Using SQLite database")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, config):
        self.db_type = config['DATABASE_TYPE']
        self.config = config
        
    def get_connection(self):
        if self.db_type == 'postgresql':
            conn = psycopg2.connect(self.config['DATABASE_URL'])
            conn.autocommit = False
            return conn
        else:
            conn = sqlite3.connect(self.config['DATABASE'])
            conn.row_factory = sqlite3.Row
            return conn
    
    def execute_query(self, query, params=None):
        conn = None
        try:
            conn = self.get_connection()
            if self.db_type == 'postgresql':
                cur = conn.cursor()
                cur.execute(query, params or ())
                if query.strip().upper().startswith(('SELECT', 'WITH')):
                    result = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
                    result = [dict(zip(columns, row)) for row in result]
                else:
                    result = cur.rowcount
                    conn.commit()
                cur.close()
            else:
                cur = conn.cursor()
                cur.execute(query, params or ())
                if query.strip().upper().startswith(('SELECT', 'WITH')):
                    result = [dict(row) for row in cur.fetchall()]
                else:
                    result = cur.rowcount
                    conn.commit()
                cur.close()
            return result
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Query error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def init_database(self):
        try:
            if self.db_type == 'postgresql':
                self._init_postgresql()
            else:
                self._init_sqlite()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Database init failed: {e}")
            raise
    
    def _init_postgresql(self):
        queries = [
            """CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                question_id VARCHAR(50) UNIQUE NOT NULL,
                question_text TEXT NOT NULL,
                choices TEXT NOT NULL,
                correct_answer VARCHAR(10) NOT NULL,
                explanation TEXT,
                genre VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS user_answers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                question_id INTEGER REFERENCES questions(id),
                user_answer VARCHAR(10) NOT NULL,
                is_correct BOOLEAN NOT NULL,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        ]
        
        for query in queries:
            self.execute_query(query)
    
    def _init_sqlite(self):
        queries = [
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id TEXT UNIQUE NOT NULL,
                question_text TEXT NOT NULL,
                choices TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                explanation TEXT,
                genre TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS user_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_id INTEGER,
                user_answer TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                answered_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        ]
        
        for query in queries:
            self.execute_query(query)

# Initialize components
db_manager = DatabaseManager(app.config)

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('ログインが必要です。', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Initialize database and create admin user
def initialize_app():
    try:
        db_manager.init_database()
        
        # Create admin user if not exists
        admin_check = 'SELECT id FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT id FROM users WHERE username = ?'
        existing_admin = db_manager.execute_query(admin_check, ('admin',))
        
        if not existing_admin:
            admin_hash = generate_password_hash('admin123')
            if db_manager.db_type == 'postgresql':
                db_manager.execute_query(
                    'INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, %s)',
                    ('admin', admin_hash, True)
                )
            else:
                db_manager.execute_query(
                    'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                    ('admin', admin_hash, 1)
                )
            logger.info("Admin user created")
        
    except Exception as e:
        logger.error(f"Init failed: {e}")

# Initialize app
initialize_app()

# Routes
@app.route('/')
def index():
    """常にログイン画面を表示"""
    return render_template('auth/login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('auth/login.html')
    
    # POST request - process login
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if not username or not password:
        flash('ユーザー名とパスワードを入力してください。', 'error')
        return render_template('auth/login.html')
    
    try:
        # Get user
        user_query = 'SELECT id, username, password_hash, is_admin FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT id, username, password_hash, is_admin FROM users WHERE username = ?'
        users = db_manager.execute_query(user_query, (username,))
        
        if users and check_password_hash(users[0]['password_hash'], password):
            # Login success
            user = users[0]
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            
            logger.info(f"Login success: {username}")
            
            # Redirect to dashboard immediately
            return redirect('/dashboard')
        else:
            flash('ユーザー名またはパスワードが正しくありません。', 'error')
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        flash('ログインエラーが発生しました。', 'error')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('auth/register.html')
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    # Validation
    if not username or not password:
        flash('ユーザー名とパスワードを入力してください。', 'error')
        return render_template('auth/register.html')
    
    if len(username) < 3:
        flash('ユーザー名は3文字以上で入力してください。', 'error')
        return render_template('auth/register.html')
    
    if len(password) < 6:
        flash('パスワードは6文字以上で入力してください。', 'error')
        return render_template('auth/register.html')
        
    if password != confirm_password:
        flash('パスワードが一致しません。', 'error')
        return render_template('auth/register.html')

    try:
        # Check existing user
        existing = db_manager.execute_query(
            'SELECT id FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT id FROM users WHERE username = ?',
            (username,)
        )
        if existing:
            flash('このユーザー名は既に使用されています。', 'error')
            return render_template('auth/register.html')

        # Create user
        password_hash = generate_password_hash(password)
        db_manager.execute_query(
            'INSERT INTO users (username, password_hash) VALUES (%s, %s)' if db_manager.db_type == 'postgresql' else 'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            (username, password_hash)
        )
        
        flash('登録が完了しました。ログインしてください。', 'success')
        return redirect('/login')
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        flash('登録エラーが発生しました。', 'error')
        return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('ログアウトしました。', 'info')
    return redirect('/login')

@app.route('/dashboard')
@login_required
def dashboard():
    """シンプルなダッシュボード"""
    try:
        user_id = session.get('user_id')
        
        # デフォルト統計
        stats = {
            'total_questions': 0,
            'total_answers': 0,
            'correct_answers': 0,
            'accuracy_rate': 0
        }
        
        # 安全に統計を取得
        try:
            # 総問題数
            result = db_manager.execute_query("SELECT COUNT(*) as count FROM questions")
            if result:
                stats['total_questions'] = result[0]['count']
        except:
            pass
        
        try:
            # ユーザーの回答数
            query = "SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s" if db_manager.db_type == 'postgresql' else "SELECT COUNT(*) as count FROM user_answers WHERE user_id = ?"
            result = db_manager.execute_query(query, (user_id,))
            if result:
                stats['total_answers'] = result[0]['count']
        except:
            pass
        
        try:
            # 正解数
            if stats['total_answers'] > 0:
                query = "SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s AND is_correct = %s" if db_manager.db_type == 'postgresql' else "SELECT COUNT(*) as count FROM user_answers WHERE user_id = ? AND is_correct = ?"
                result = db_manager.execute_query(query, (user_id, True if db_manager.db_type == 'postgresql' else 1))
                if result:
                    stats['correct_answers'] = result[0]['count']
                    stats['accuracy_rate'] = round((stats['correct_answers'] / stats['total_answers']) * 100, 1)
        except:
            pass
        
        return render_template('dashboard.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        # エラーでもダッシュボードを表示
        stats = {'total_questions': 0, 'total_answers': 0, 'correct_answers': 0, 'accuracy_rate': 0}
        return render_template('dashboard.html', stats=stats)

@app.route('/health')
def health():
    try:
        db_manager.execute_query("SELECT 1")
        return {'status': 'ok', 'database': db_manager.db_type}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}, 500

@app.route('/debug')
def debug():
    return {
        'database': db_manager.db_type,
        'session': dict(session),
        'logged_in': 'user_id' in session
    }

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return redirect('/login')

@app.errorhandler(500)
def server_error(error):
    logger.error(f"500 error: {error}")
    return "サーバーエラーが発生しました。", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
