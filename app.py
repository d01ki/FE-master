"""
基本情報技術者試験 学習アプリ（ログイン機能付き）
Flask + Flask-Login + SQLite を使用した学習プラットフォーム
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import json
import os
import re
from datetime import datetime
import random

# utilsモジュールのインポート（存在する場合のみ）
try:
    from utils.pdf_processor import PDFProcessor
    from utils.database import init_db, get_db_connection
    from utils.question_manager import QuestionManager
    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False
    print("Warning: utils modules not available. Running with minimal functionality.")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# アプリケーション設定
app.config.update({
    'DATABASE': 'fe_exam.db',
    'UPLOAD_FOLDER': 'uploads',
    'JSON_FOLDER': 'json_questions',
    'ADMIN_PASSWORD': os.environ.get('ADMIN_PASSWORD', 'fe2025admin')
})

# フォルダ作成
for folder in [app.config['UPLOAD_FOLDER'], app.config['JSON_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

# Flask-Login設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'このページにアクセスするにはログインが必要です。'

class User(UserMixin):
    def __init__(self, id, username, email=None, is_admin=False):
        self.id = id
        self.username = username
        self.email = email
        self.is_admin = is_admin

# 簡易データベース接続関数
def simple_get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def simple_init_db(db_path):
    with simple_get_db_connection(db_path) as conn:
        # ユーザーテーブル
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 問題テーブル
        conn.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT NOT NULL,
                choices TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                explanation TEXT,
                genre TEXT,
                difficulty TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 回答履歴テーブル
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER,
                user_answer TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_id) REFERENCES questions (id)
            )
        ''')

@login_manager.user_loader
def load_user(user_id):
    try:
        with simple_get_db_connection(app.config['DATABASE']) as conn:
            user_data = conn.execute(
                'SELECT id, username, email, is_admin FROM users WHERE id = ?', 
                (user_id,)
            ).fetchone()
            if user_data:
                return User(user_data[0], user_data[1], user_data[2], user_data[3])
    except:
        pass
    return None

# データベース初期化
def init_database():
    if UTILS_AVAILABLE:
        try:
            if not os.path.exists(app.config['DATABASE']):
                init_db(app.config['DATABASE'])
            question_manager = QuestionManager(app.config['DATABASE'])
            return question_manager
        except Exception as e:
            print(f"Utils initialization failed: {e}")
    
    # フォールバック：簡易初期化
    simple_init_db(app.config['DATABASE'])
    
    # デフォルト管理者作成
    try:
        admin_hash = generate_password_hash('admin123')
        with simple_get_db_connection(app.config['DATABASE']) as conn:
            try:
                conn.execute(
                    'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                    ('admin', admin_hash, 1)
                )
                print("デフォルト管理者ユーザー（admin/admin123）を作成しました")
            except sqlite3.IntegrityError:
                print("管理者ユーザーは既に存在します")
    except Exception as e:
        print(f"管理者作成エラー: {e}")
    
    return None

question_manager = init_database()

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('管理者権限が必要です。', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 認証ルート
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        if not username or not password:
            flash('ユーザー名とパスワードを入力してください。', 'error')
            return render_template('auth/login.html')
        
        try:
            with simple_get_db_connection(app.config['DATABASE']) as conn:
                user_data = conn.execute(
                    'SELECT id, username, email, password_hash, is_admin FROM users WHERE username = ? OR email = ?',
                    (username, username)
                ).fetchone()
                
                if user_data and check_password_hash(user_data[3], password):
                    user = User(user_data[0], user_data[1], user_data[2], user_data[4])
                    login_user(user, remember=remember)
                    flash(f'ようこそ、{user.username}さん！', 'success')
                    
                    next_page = request.args.get('next')
                    return redirect(next_page) if next_page else redirect(url_for('index'))
                else:
                    flash('ユーザー名またはパスワードが間違っています。', 'error')
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            flash('ログイン処理中にエラーが発生しました。', 'error')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email', '')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # バリデーション
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
            password_hash = generate_password_hash(password)
            with simple_get_db_connection(app.config['DATABASE']) as conn:
                existing = conn.execute(
                    'SELECT id FROM users WHERE username = ? OR (email = ? AND email != "")',
                    (username, email)
                ).fetchone()
                
                if existing:
                    flash('このユーザー名またはメールアドレスは既に使用されています。', 'error')
                    return render_template('auth/register.html')
                
                conn.execute(
                    'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                    (username, email, password_hash)
                )
                
                flash('登録が完了しました！ログインしてください。', 'success')
                return redirect(url_for('login'))
                
        except Exception as e:
            app.logger.error(f"Registration error: {e}")
            flash('登録中にエラーが発生しました。再度お試しください。', 'error')
    
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('login'))

# メインルート
@app.route('/')
@login_required
def index():
    try:
        stats = {'total_questions': 0, 'total_answers': 0, 'correct_answers': 0, 'accuracy_rate': 0, 'recent_history': [], 'genre_stats': []}
        
        with simple_get_db_connection(app.config['DATABASE']) as conn:
            stats['total_questions'] = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
            stats['total_answers'] = conn.execute('SELECT COUNT(*) FROM user_answers').fetchone()[0]
            stats['correct_answers'] = conn.execute('SELECT COUNT(*) FROM user_answers WHERE is_correct = 1').fetchone()[0]
        
        stats['accuracy_rate'] = round((stats['correct_answers'] / stats['total_answers'] * 100), 1) if stats['total_answers'] > 0 else 0
        
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        app.logger.error(f"Dashboard error: {e}")
        return render_template('dashboard.html', stats={'total_questions': 0, 'total_answers': 0, 'correct_answers': 0, 'accuracy_rate': 0, 'recent_history': [], 'genre_stats': []})

# 簡単なルート
@app.route('/random')
@login_required
def random_question():
    if question_manager:
        try:
            question = question_manager.get_random_question()
            if question:
                return redirect(url_for('show_question', question_id=question['id']))
        except:
            pass
    
    flash('問題が見つかりません。', 'error')
    return redirect(url_for('index'))

@app.route('/questions/<int:question_id>')
@login_required
def show_question(question_id):
    if question_manager:
        try:
            question = question_manager.get_question(question_id)
            if question:
                return render_template('question.html', question=question)
        except:
            pass
    
    return render_template('error.html', message='問題が見つかりません'), 404

@app.route('/genre_practice')
@login_required
def genre_practice():
    return render_template('error.html', message='この機能は準備中です'), 404

@app.route('/mock_exam')
@login_required
def mock_exam():
    return render_template('error.html', message='この機能は準備中です'), 404

@app.route('/history')
@login_required
def history():
    return render_template('error.html', message='この機能は準備中です'), 404

@app.route('/admin')
@admin_required
def admin():
    try:
        stats = {'question_count': 0, 'user_count': 0, 'genres': []}
        
        with simple_get_db_connection(app.config['DATABASE']) as conn:
            stats['question_count'] = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
            stats['user_count'] = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        
        return render_template('admin.html', data=stats)
    except Exception as e:
        app.logger.error(f"Admin error: {e}")
        return render_template('error.html', message='管理画面の表示中にエラーが発生しました'), 500

# エラーハンドラ
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', message='ページが見つかりません'), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal error: {error}")
    return render_template('error.html', message='内部サーバーエラーが発生しました'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
