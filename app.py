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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, config):
        self.db_type = config['DATABASE_TYPE']
        self.config = config
        logger.info(f"DatabaseManager initialized with {self.db_type}")
        
    def get_connection(self):
        try:
            if self.db_type == 'postgresql':
                conn = psycopg2.connect(self.config['DATABASE_URL'])
                conn.autocommit = False
                return conn
            else:
                conn = sqlite3.connect(self.config['DATABASE'])
                conn.row_factory = sqlite3.Row
                return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
    
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
            logger.error(f"Query execution error: {e} | Query: {query} | Params: {params}")
            raise
        finally:
            if conn:
                conn.close()
    
    def init_database(self):
        logger.info("Initializing database...")
        try:
            if self.db_type == 'postgresql':
                self._init_postgresql()
            else:
                self._init_sqlite()
            logger.info("✅ Database initialization completed")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
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
            )""",
            "CREATE INDEX IF NOT EXISTS idx_questions_genre ON questions(genre)",
            "CREATE INDEX IF NOT EXISTS idx_user_answers_user_id ON user_answers(user_id)"
        ]
        
        for i, query in enumerate(queries):
            try:
                self.execute_query(query)
                logger.info(f"✅ PostgreSQL query {i+1}/{len(queries)} executed")
            except Exception as e:
                logger.error(f"❌ PostgreSQL query {i+1} failed: {e}")
                raise
    
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
                answered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (question_id) REFERENCES questions (id)
            )"""
        ]
        
        for i, query in enumerate(queries):
            try:
                self.execute_query(query)
                logger.info(f"✅ SQLite query {i+1}/{len(queries)} executed")
            except Exception as e:
                logger.error(f"❌ SQLite query {i+1} failed: {e}")
                raise

# Initialize components
try:
    db_manager = DatabaseManager(app.config)
    logger.info("✅ DatabaseManager created")
except Exception as e:
    logger.error(f"❌ Failed to create DatabaseManager: {e}")
    raise

# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning("Unauthorized access attempt - redirecting to login")
            flash('ログインが必要です。', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            logger.warning("Admin access attempt without privileges")
            flash('管理者権限が必要です。', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Initialize database and create admin user
def initialize_app():
    try:
        logger.info("🚀 Starting application initialization...")
        
        # Initialize database
        db_manager.init_database()
        
        # Create admin user
        logger.info("Checking for admin user...")
        admin_check_query = 'SELECT id, username, is_admin FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT id, username, is_admin FROM users WHERE username = ?'
        existing_admin = db_manager.execute_query(admin_check_query, ('admin',))
        
        if not existing_admin:
            logger.info("Creating admin user...")
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
            
            logger.info("✅ Admin user created: admin/admin123")
        else:
            logger.info(f"✅ Admin user exists: {existing_admin[0]}")
        
        # Load questions (with safe error handling)
        try:
            json_folder = 'json_questions'
            if os.path.exists(json_folder):
                total_files = 0
                for filename in os.listdir(json_folder):
                    if filename.endswith('.json'):
                        total_files += 1
                logger.info(f"Found {total_files} JSON files")
            else:
                logger.info("No json_questions folder found")
        except Exception as e:
            logger.warning(f"Question loading error (non-critical): {e}")
        
        logger.info("🎉 Application initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"💥 Application initialization failed: {e}")
        import traceback
        traceback.print_exc()
        raise

# Initialize the application
try:
    initialize_app()
except Exception as e:
    logger.error(f"Failed to initialize app: {e}")
    # Continue anyway to allow debugging

# Routes
@app.route('/')
def index():
    try:
        logger.info("Index route accessed")
        if 'user_id' in session:
            logger.info(f"User {session.get('username')} already logged in, redirecting to dashboard")
            return redirect(url_for('dashboard'))
        return render_template('auth/login.html')
    except Exception as e:
        logger.error(f"Index route error: {e}")
        return f"Error: {e}", 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        logger.info(f"Login route accessed - Method: {request.method}")
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            logger.info(f"Login attempt for username: '{username}'")
            
            if not username or not password:
                logger.warning("Empty username or password")
                flash('ユーザー名とパスワードを入力してください。', 'error')
                return render_template('auth/login.html')
            
            try:
                # Get user from database
                user_query = 'SELECT id, username, password_hash, is_admin FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT id, username, password_hash, is_admin FROM users WHERE username = ?'
                user_result = db_manager.execute_query(user_query, (username,))
                
                logger.info(f"Database query result: {len(user_result) if user_result else 0} users found")
                
                if user_result and len(user_result) > 0:
                    user = user_result[0]
                    logger.info(f"User found: {user['username']}, is_admin: {user['is_admin']}")
                    
                    if check_password_hash(user['password_hash'], password):
                        # Login successful
                        session.clear()
                        session['user_id'] = user['id']
                        session['username'] = user['username']
                        session['is_admin'] = bool(user['is_admin'])
                        
                        logger.info(f"✅ Login successful for {username} (ID: {user['id']})")
                        flash('ログインしました。', 'success')
                        return redirect(url_for('dashboard'))
                    else:
                        logger.warning(f"❌ Password incorrect for {username}")
                        flash('ユーザー名またはパスワードが正しくありません。', 'error')
                else:
                    logger.warning(f"❌ User not found: {username}")
                    flash('ユーザー名またはパスワードが正しくありません。', 'error')
                    
            except Exception as e:
                logger.error(f"Database error during login: {e}")
                flash('ログイン処理中にエラーが発生しました。', 'error')
        
        return render_template('auth/login.html')
        
    except Exception as e:
        logger.error(f"Login route error: {e}")
        return f"Login Error: {e}", 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            logger.info(f"Registration attempt for username: '{username}'")
            
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
                # Check for existing user
                existing_user = db_manager.execute_query(
                    'SELECT id FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT id FROM users WHERE username = ?',
                    (username,)
                )
                if existing_user:
                    flash('このユーザー名は既に使用されています。', 'error')
                    return render_template('auth/register.html')

                # Create new user
                password_hash = generate_password_hash(password)
                db_manager.execute_query(
                    'INSERT INTO users (username, password_hash) VALUES (%s, %s)' if db_manager.db_type == 'postgresql' else 'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                    (username, password_hash)
                )
                
                logger.info(f"✅ New user registered: {username}")
                flash('登録が完了しました。ログインしてください。', 'success')
                return redirect(url_for('login'))
                
            except Exception as e:
                logger.error(f"Registration database error: {e}")
                flash('登録中にエラーが発生しました。', 'error')

        return render_template('auth/register.html')
        
    except Exception as e:
        logger.error(f"Register route error: {e}")
        return f"Registration Error: {e}", 500

@app.route('/logout')
def logout():
    try:
        username = session.get('username', 'Unknown')
        session.clear()
        logger.info(f"User logged out: {username}")
        flash('ログアウトしました。', 'info')
        return redirect(url_for('login'))
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        user_id = session.get('user_id')
        username = session.get('username')
        logger.info(f"Dashboard accessed by user {username} (ID: {user_id})")
        
        # Initialize stats with safe defaults
        stats = {
            'total_questions': 0,
            'total_answers': 0,
            'correct_answers': 0,
            'accuracy_rate': 0
        }
        
        try:
            # Get total questions
            total_questions_result = db_manager.execute_query("SELECT COUNT(*) as count FROM questions")
            if total_questions_result:
                stats['total_questions'] = total_questions_result[0]['count']
                
            # Get user answers
            user_answers_query = "SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s" if db_manager.db_type == 'postgresql' else "SELECT COUNT(*) as count FROM user_answers WHERE user_id = ?"
            total_answers_result = db_manager.execute_query(user_answers_query, (user_id,))
            if total_answers_result:
                stats['total_answers'] = total_answers_result[0]['count']
                
            # Get correct answers
            if stats['total_answers'] > 0:
                correct_query = "SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s AND is_correct = %s" if db_manager.db_type == 'postgresql' else "SELECT COUNT(*) as count FROM user_answers WHERE user_id = ? AND is_correct = ?"
                correct_result = db_manager.execute_query(correct_query, (user_id, True if db_manager.db_type == 'postgresql' else 1))
                if correct_result:
                    stats['correct_answers'] = correct_result[0]['count']
                    stats['accuracy_rate'] = round((stats['correct_answers'] / stats['total_answers']) * 100, 1)
                    
        except Exception as e:
            logger.warning(f"Stats calculation error (using defaults): {e}")
        
        logger.info(f"Dashboard stats for {username}: {stats}")
        return render_template('dashboard.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        import traceback
        traceback.print_exc()
        return f"Dashboard Error: {e}", 500

@app.route('/health')
def health():
    try:
        # Test database connection
        test_result = db_manager.execute_query("SELECT 1 as test")
        return {
            'status': 'healthy', 
            'database': db_manager.db_type,
            'test_query': 'success' if test_result else 'failed'
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {'status': 'error', 'error': str(e)}, 500

@app.route('/debug')
def debug_info():
    try:
        info = {
            'database_type': db_manager.db_type,
            'session': dict(session),
            'postgresql_available': POSTGRESQL_AVAILABLE,
            'database_url_set': bool(os.environ.get('DATABASE_URL'))
        }
        
        if session.get('is_admin'):
            try:
                users = db_manager.execute_query('SELECT id, username, is_admin, created_at FROM users')
                info['users'] = users
            except:
                info['users'] = 'Error retrieving users'
                
        return info
    except Exception as e:
        return {'error': str(e)}, 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('auth/login.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return f"Internal Server Error: {error}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Starting Flask app on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
