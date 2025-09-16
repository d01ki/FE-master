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
except ImportError:
    POSTGRESQL_AVAILABLE = False
    print("PostgreSQL driver not available - using SQLite only")

import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fe-exam-app-secret-key-change-in-production')

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and POSTGRESQL_AVAILABLE:
    app.config['DATABASE_TYPE'] = 'postgresql'
    app.config['DATABASE_URL'] = DATABASE_URL
    print("Using PostgreSQL database")
else:
    app.config['DATABASE_TYPE'] = 'sqlite'
    app.config['DATABASE'] = 'fe_exam.db'
    print("Using SQLite database")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Manager
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
        conn = self.get_connection()
        try:
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
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_database(self):
        if self.db_type == 'postgresql':
            self._init_postgresql()
        else:
            self._init_sqlite()
    
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
                choices JSON NOT NULL,
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
        
        for query in queries:
            try:
                self.execute_query(query)
            except Exception as e:
                logger.error(f"PostgreSQL init error: {e}")
    
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
        
        for query in queries:
            try:
                self.execute_query(query)
            except Exception as e:
                logger.error(f"SQLite init error: {e}")

# Question Manager
class QuestionManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def load_json_files(self):
        json_folder = 'json_questions'
        if not os.path.exists(json_folder):
            return {'total_files': 0, 'total_questions': 0, 'errors': []}
        
        total_files = 0
        total_questions = 0
        errors = []
        
        for filename in os.listdir(json_folder):
            if filename.endswith('.json'):
                filepath = os.path.join(json_folder, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        questions = json.load(f)
                    
                    result = self.save_questions(questions, filename)
                    total_files += 1
                    total_questions += result['saved_count']
                    
                except Exception as e:
                    errors.append(f"{filename}: {str(e)}")
        
        return {'total_files': total_files, 'total_questions': total_questions, 'errors': errors}
    
    def save_questions(self, questions, source_file=''):
        saved_count = 0
        errors = []
        
        for i, question in enumerate(questions):
            try:
                required_fields = ['question_text', 'choices', 'correct_answer']
                if not all(field in question for field in required_fields):
                    errors.append(f"Question {i+1}: Missing required fields")
                    continue
                
                question_id = question.get('question_id', f"Q{i+1:03d}_{source_file}")
                choices_data = json.dumps(question['choices'], ensure_ascii=False)
                
                existing = self.db.execute_query(
                    'SELECT id FROM questions WHERE question_id = %s' if self.db.db_type == 'postgresql' else 'SELECT id FROM questions WHERE question_id = ?',
                    (question_id,)
                )
                
                if not existing:
                    if self.db.db_type == 'postgresql':
                        self.db.execute_query("""
                            INSERT INTO questions (question_id, question_text, choices, correct_answer, explanation, genre) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            question_id, question['question_text'], choices_data,
                            question['correct_answer'], question.get('explanation', ''),
                            question.get('genre', 'その他')
                        ))
                    else:
                        self.db.execute_query("""
                            INSERT INTO questions (question_id, question_text, choices, correct_answer, explanation, genre) 
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            question_id, question['question_text'], choices_data,
                            question['correct_answer'], question.get('explanation', ''),
                            question.get('genre', 'その他')
                        ))
                
                saved_count += 1
                
            except Exception as e:
                errors.append(f"Question {i+1}: {str(e)}")
        
        return {'saved_count': saved_count, 'total_count': len(questions), 'errors': errors}

# Initialize components
db_manager = DatabaseManager(app.config)
question_manager = QuestionManager(db_manager)

# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('ログインが必要です。', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('管理者権限が必要です。', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Initialize database and admin user
def initialize_app():
    try:
        logger.info("Initializing database...")
        db_manager.init_database()
        
        # Check for existing admin with better debugging
        admin_check_query = 'SELECT id, username, is_admin FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT id, username, is_admin FROM users WHERE username = ?'
        existing_admin = db_manager.execute_query(admin_check_query, ('admin',))
        
        if existing_admin:
            logger.info(f"Admin user already exists: {existing_admin[0]}")
        else:
            logger.info("Creating default admin user...")
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
            
            logger.info("✅ Default admin created: admin/admin123")
            
            # Verify creation
            verify_admin = db_manager.execute_query(admin_check_query, ('admin',))
            if verify_admin:
                logger.info(f"✅ Admin verification successful: {verify_admin[0]}")
            else:
                logger.error("❌ Admin creation failed!")
        
        # Load questions
        result = question_manager.load_json_files()
        logger.info(f"Loaded {result['total_questions']} questions from {result['total_files']} files")
        
        # List all users for debugging
        all_users = db_manager.execute_query('SELECT id, username, is_admin FROM users')
        logger.info(f"All users in database: {all_users}")
        
    except Exception as e:
        logger.error(f"Init error: {e}")
        import traceback
        traceback.print_exc()

# Call initialization
initialize_app()

# Authentication routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('auth/login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        logger.info(f"Login attempt for user: {username}")
        
        if not username or not password:
            flash('ユーザー名とパスワードを入力してください。', 'error')
            return redirect(url_for('login'))
        
        user = db_manager.execute_query(
            'SELECT * FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT * FROM users WHERE username = ?',
            (username,)
        )
        
        if user:
            logger.info(f"User found: {user[0]['username']}, is_admin: {user[0]['is_admin']}")
            if check_password_hash(user[0]['password_hash'], password):
                session.clear()
                session['user_id'] = user[0]['id']
                session['username'] = user[0]['username']
                session['is_admin'] = bool(user[0]['is_admin'])
                flash('ログインしました。', 'success')
                logger.info(f"✅ Login successful for {username}")
                return redirect(url_for('dashboard'))
            else:
                logger.warning(f"❌ Password incorrect for {username}")
                flash('ユーザー名またはパスワードが正しくありません。', 'error')
        else:
            logger.warning(f"❌ User not found: {username}")
            flash('ユーザー名またはパスワードが正しくありません。', 'error')
            
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        confirm_password = request.form.get('confirm_password', '')
        
        if not username or not password:
            flash('ユーザー名とパスワードを入力してください。', 'error')
            return redirect(url_for('register'))
        
        if len(username) < 3:
            flash('ユーザー名は3文字以上で入力してください。', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash('パスワードは6文字以上で入力してください。', 'error')
            return redirect(url_for('register'))
            
        if password != confirm_password:
            flash('パスワードが一致しません。', 'error')
            return redirect(url_for('register'))

        existing_user = db_manager.execute_query(
            'SELECT id FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT id FROM users WHERE username = ?',
            (username,)
        )
        if existing_user:
            flash('このユーザー名は既に使用されています。', 'error')
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password)
        try:
            db_manager.execute_query(
                'INSERT INTO users (username, password_hash) VALUES (%s, %s)' if db_manager.db_type == 'postgresql' else 'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (username, password_hash)
            )
            flash('登録が完了しました。ログインしてください。', 'success')
            logger.info(f"✅ New user registered: {username}")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'登録エラー: {e}', 'error')
            logger.error(f"Registration error: {e}")
            return redirect(url_for('register'))

    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    username = session.get('username', 'Unknown')
    session.clear()
    flash('ログアウトしました。', 'info')
    logger.info(f"User logged out: {username}")
    return redirect(url_for('login'))

# Main application routes - GETのみ許可
@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    try:
        user_id = session['user_id']
        logger.info(f"Dashboard access by user_id: {user_id}")
        
        # Get stats with error handling
        total_questions = db_manager.execute_query("SELECT COUNT(*) as count FROM questions")[0]['count']
        user_answers_query = "SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s" if db_manager.db_type == 'postgresql' else "SELECT COUNT(*) as count FROM user_answers WHERE user_id = ?"
        total_answers = db_manager.execute_query(user_answers_query, (user_id,))[0]['count']
        
        correct_query = "SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s AND is_correct = %s" if db_manager.db_type == 'postgresql' else "SELECT COUNT(*) as count FROM user_answers WHERE user_id = ? AND is_correct = ?"
        correct_count = db_manager.execute_query(correct_query, (user_id, True if db_manager.db_type == 'postgresql' else 1))[0]['count']
        
        accuracy_rate = round((correct_count / total_answers) * 100, 1) if total_answers > 0 else 0
        
        stats = {
            'total_questions': total_questions,
            'total_answers': total_answers,
            'correct_answers': correct_count,
            'accuracy_rate': accuracy_rate
        }
        
        logger.info(f"Dashboard stats: {stats}")
        return render_template('dashboard.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('ダッシュボードの読み込み中にエラーが発生しました。', 'error')
        return redirect(url_for('login'))

@app.route('/random')
@login_required
def random_question():
    result = db_manager.execute_query("SELECT id FROM questions ORDER BY RANDOM() LIMIT 1")
    if not result:
        flash('問題が見つかりません。', 'warning')
        return redirect(url_for('dashboard'))
    return redirect(url_for('show_question', question_id=result[0]['id']))

@app.route('/question/<int:question_id>')
@login_required
def show_question(question_id):
    query = "SELECT * FROM questions WHERE id = %s" if db_manager.db_type == 'postgresql' else "SELECT * FROM questions WHERE id = ?"
    question = db_manager.execute_query(query, (question_id,))
    
    if not question:
        flash('問題が見つかりません。', 'error')
        return redirect(url_for('dashboard'))
    
    question_data = question[0]
    choices = json.loads(question_data['choices']) if isinstance(question_data['choices'], str) else question_data['choices']
    return render_template('question.html', question=question_data, choices=choices)

@app.route('/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    try:
        question_id = request.form.get('question_id', type=int)
        user_answer = request.form.get('answer')
        user_id = session['user_id']

        if not question_id or not user_answer:
            return jsonify({'error': '無効な回答です。'}), 400

        query = "SELECT correct_answer, explanation FROM questions WHERE id = %s" if db_manager.db_type == 'postgresql' else "SELECT correct_answer, explanation FROM questions WHERE id = ?"
        result = db_manager.execute_query(query, (question_id,))
        
        if not result:
            return jsonify({'error': '問題が見つかりません。'}), 404

        correct_answer = result[0]['correct_answer']
        explanation = result[0]['explanation']
        is_correct = (user_answer == correct_answer)

        insert_query = "INSERT INTO user_answers (user_id, question_id, user_answer, is_correct) VALUES (%s, %s, %s, %s)" if db_manager.db_type == 'postgresql' else "INSERT INTO user_answers (user_id, question_id, user_answer, is_correct) VALUES (?, ?, ?, ?)"
        db_manager.execute_query(insert_query, (user_id, question_id, user_answer, is_correct))

        return jsonify({
            'is_correct': is_correct,
            'correct_answer': correct_answer,
            'explanation': explanation or ''
        })
    except Exception as e:
        logger.error(f"Answer error: {e}")
        return jsonify({'error': '処理エラー'}), 500

# Health check endpoint
@app.route('/health')
def health():
    try:
        # Test database connection
        db_manager.execute_query("SELECT 1")
        return {'status': 'healthy', 'database': db_manager.db_type}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}, 500

# Debug endpoint
@app.route('/debug/users')
def debug_users():
    if not session.get('is_admin'):
        return {'error': 'Unauthorized'}, 401
    
    users = db_manager.execute_query('SELECT id, username, is_admin, created_at FROM users')
    return {'users': users, 'database_type': db_manager.db_type}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
