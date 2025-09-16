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
import random

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
    
    logger.info(f"Login attempt for: {username}")
    
    if not username or not password:
        flash('ユーザー名とパスワードを入力してください。', 'error')
        return render_template('auth/login.html')
    
    try:
        # Get user
        user_query = 'SELECT id, username, password_hash, is_admin FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT id, username, password_hash, is_admin FROM users WHERE username = ?'
        users = db_manager.execute_query(user_query, (username,))
        
        if users and check_password_hash(users[0]['password_hash'], password):
            # Clear any existing session
            session.clear()
            
            # Set session data
            user = users[0]
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            
            logger.info(f"✅ Login successful for {username}, redirecting to dashboard")
            
            # Use 302 redirect to dashboard
            return redirect(url_for('dashboard'))
        else:
            logger.warning(f"❌ Login failed for {username}")
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
        return redirect(url_for('login'))
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        flash('登録エラーが発生しました。', 'error')
        return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """ダッシュボード画面"""
    try:
        user_id = session.get('user_id')
        username = session.get('username')
        
        logger.info(f"Dashboard accessed by {username} (ID: {user_id})")
        
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
        except Exception as e:
            logger.warning(f"Error getting total questions: {e}")
        
        try:
            # ユーザーの回答数
            query = "SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s" if db_manager.db_type == 'postgresql' else "SELECT COUNT(*) as count FROM user_answers WHERE user_id = ?"
            result = db_manager.execute_query(query, (user_id,))
            if result:
                stats['total_answers'] = result[0]['count']
        except Exception as e:
            logger.warning(f"Error getting user answers: {e}")
        
        try:
            # 正解数
            if stats['total_answers'] > 0:
                query = "SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s AND is_correct = %s" if db_manager.db_type == 'postgresql' else "SELECT COUNT(*) as count FROM user_answers WHERE user_id = ? AND is_correct = ?"
                result = db_manager.execute_query(query, (user_id, True if db_manager.db_type == 'postgresql' else 1))
                if result:
                    stats['correct_answers'] = result[0]['count']
                    stats['accuracy_rate'] = round((stats['correct_answers'] / stats['total_answers']) * 100, 1)
        except Exception as e:
            logger.warning(f"Error getting correct answers: {e}")
        
        logger.info(f"Dashboard stats: {stats}")
        return render_template('dashboard.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        # エラーでもダッシュボードを表示
        stats = {'total_questions': 0, 'total_answers': 0, 'correct_answers': 0, 'accuracy_rate': 0}
        return render_template('dashboard.html', stats=stats)

@app.route('/random')
@login_required
def random_question():
    """ランダム問題"""
    try:
        # データベース種別に応じたランダム取得クエリ
        if db_manager.db_type == 'postgresql':
            result = db_manager.execute_query("SELECT id FROM questions ORDER BY RANDOM() LIMIT 1")
        else:
            # SQLiteの場合、全問題を取得してPythonでランダム選択
            all_questions = db_manager.execute_query("SELECT id FROM questions")
            if all_questions:
                result = [random.choice(all_questions)]
            else:
                result = []
        
        if not result:
            flash('問題が見つかりません。', 'warning')
            return redirect(url_for('dashboard'))
        return redirect(url_for('show_question', question_id=result[0]['id']))
    except Exception as e:
        logger.error(f"Random question error: {e}")
        flash('問題の取得中にエラーが発生しました。', 'error')
        return redirect(url_for('dashboard'))

@app.route('/question/<int:question_id>')
@login_required
def show_question(question_id):
    """問題表示"""
    try:
        query = "SELECT * FROM questions WHERE id = %s" if db_manager.db_type == 'postgresql' else "SELECT * FROM questions WHERE id = ?"
        question = db_manager.execute_query(query, (question_id,))
        
        if not question:
            flash('問題が見つかりません。', 'error')
            return redirect(url_for('dashboard'))
        
        question_data = question[0]
        choices = json.loads(question_data['choices']) if isinstance(question_data['choices'], str) else question_data['choices']
        return render_template('question.html', question=question_data, choices=choices)
    except Exception as e:
        logger.error(f"Question display error: {e}")
        flash('問題の表示中にエラーが発生しました。', 'error')
        return redirect(url_for('dashboard'))

@app.route('/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    """回答提出"""
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
        logger.error(f"Answer submission error: {e}")
        return jsonify({'error': '処理エラー'}), 500

@app.route('/genre_practice')
@login_required
def genre_practice():
    """ジャンル別演習"""
    try:
        genres = [row['genre'] for row in db_manager.execute_query("SELECT DISTINCT genre FROM questions ORDER BY genre")]
        return render_template('genre_practice.html', genres=genres)
    except Exception as e:
        logger.error(f"Genre practice error: {e}")
        return render_template('genre_practice.html', genres=[])

@app.route('/genre/<path:genre_name>')
@login_required
def genre_questions(genre_name):
    """ジャンル別問題一覧"""
    try:
        query = "SELECT id, question_text FROM questions WHERE genre = %s ORDER BY id" if db_manager.db_type == 'postgresql' else "SELECT id, question_text FROM questions WHERE genre = ? ORDER BY id"
        questions = db_manager.execute_query(query, (genre_name,))
        return render_template('problem_list.html', questions=questions, title=f'{genre_name}演習')
    except Exception as e:
        logger.error(f"Genre questions error: {e}")
        return render_template('problem_list.html', questions=[], title=f'{genre_name}演習')

@app.route('/mock_exam')
@login_required
def mock_exam():
    """模擬試験選択"""
    try:
        json_folder = 'json_questions'
        exam_files = []
        if os.path.exists(json_folder):
            for filename in os.listdir(json_folder):
                if filename.endswith('.json'):
                    exam_files.append(filename)
        return render_template('mock_exam_select.html', exam_files=exam_files)
    except Exception as e:
        logger.error(f"Mock exam error: {e}")
        return render_template('mock_exam_select.html', exam_files=[])

@app.route('/mock_exam/<path:filename>')
@login_required
def mock_exam_start(filename):
    """模擬試験開始"""
    try:
        json_folder = 'json_questions'
        json_filepath = os.path.join(json_folder, filename)
        
        if not os.path.exists(json_filepath):
            flash('試験ファイルが見つかりません', 'error')
            return redirect(url_for('mock_exam'))
        
        with open(json_filepath, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        session['current_exam'] = {
            'filename': filename,
            'questions': questions,
            'start_time': datetime.now().isoformat()
        }
        
        return render_template('mock_exam_practice.html', questions=questions, exam_filename=filename)
        
    except Exception as e:
        logger.error(f"Mock exam start error: {e}")
        flash(f'試験ファイルの読み込みに失敗しました: {str(e)}', 'error')
        return redirect(url_for('mock_exam'))

@app.route('/mock_exam/submit', methods=['POST'])
@login_required
def submit_mock_exam():
    """模擬試験提出"""
    try:
        data = request.get_json()
        answers = data.get('answers', {})
        user_id = session['user_id']
        
        if 'current_exam' not in session:
            return jsonify({'error': '試験セッションが見つかりません'}), 400
        
        exam_questions = session['current_exam']['questions']
        results = []
        correct_count = 0
        
        for i, question_data in enumerate(exam_questions):
            question_id_str = f"q{i}"
            user_answer = answers.get(question_id_str, '')
            is_correct = user_answer == question_data['correct_answer']
            
            if is_correct:
                correct_count += 1
            
            # Save to database if question exists
            try:
                db_question = db_manager.execute_query(
                    "SELECT id FROM questions WHERE question_text = %s" if db_manager.db_type == 'postgresql' else "SELECT id FROM questions WHERE question_text = ?", 
                    (question_data['question_text'],)
                )
                if db_question:
                    persistent_question_id = db_question[0]['id']
                    db_manager.execute_query(
                        "INSERT INTO user_answers (user_id, question_id, user_answer, is_correct) VALUES (%s, %s, %s, %s)" if db_manager.db_type == 'postgresql' else "INSERT INTO user_answers (user_id, question_id, user_answer, is_correct) VALUES (?, ?, ?, ?)",
                        (user_id, persistent_question_id, user_answer, is_correct)
                    )
            except:
                pass  # Skip if question not in DB

            results.append({
                'question_text': question_data['question_text'],
                'user_answer': user_answer,
                'correct_answer': question_data['correct_answer'],
                'is_correct': is_correct,
                'explanation': question_data.get('explanation', '')
            })
        
        score = round((correct_count / len(exam_questions)) * 100, 1) if exam_questions else 0
        session.pop('current_exam', None)
        
        return jsonify({
            'score': score,
            'correct_count': correct_count,
            'total_count': len(exam_questions),
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Submit mock exam error: {e}")
        return jsonify({'error': '採点処理中にエラーが発生しました'}), 500

@app.route('/history')
@login_required
def history():
    """学習履歴"""
    try:
        user_id = session['user_id']
        query = "SELECT q.question_text, ua.user_answer, ua.is_correct, ua.answered_at FROM user_answers ua JOIN questions q ON ua.question_id = q.id WHERE ua.user_id = %s ORDER BY ua.answered_at DESC LIMIT 50" if db_manager.db_type == 'postgresql' else "SELECT q.question_text, ua.user_answer, ua.is_correct, ua.answered_at FROM user_answers ua JOIN questions q ON ua.question_id = q.id WHERE ua.user_id = ? ORDER BY ua.answered_at DESC LIMIT 50"
        answers = db_manager.execute_query(query, (user_id,))
        return render_template('history.html', answers=answers)
    except Exception as e:
        logger.error(f"History error: {e}")
        return render_template('history.html', answers=[])

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
    logger.warning(f"404 error: {error}")
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.errorhandler(500)
def server_error(error):
    logger.error(f"500 error: {error}")
    return "サーバーエラーが発生しました。", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
