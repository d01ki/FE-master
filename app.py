"""
基本情報技術者試験 学習アプリ（ログイン機能付き）
Flask + Flask-Login + SQLite/PostgreSQL + Tailwind CSS を使用した学習プラットフォーム
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import re
from datetime import datetime
import random

# データベース接続の分岐（PostgreSQL/SQLite）
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # PostgreSQL使用（本番環境）
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    def get_db_connection():
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    
    def init_db():
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # PostgreSQL用テーブル作成
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                question_text TEXT NOT NULL,
                choices TEXT NOT NULL,
                correct_answer VARCHAR(10) NOT NULL,
                explanation TEXT,
                genre VARCHAR(255),
                difficulty VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_answers (
                id SERIAL PRIMARY KEY,
                question_id INTEGER REFERENCES questions(id),
                user_answer VARCHAR(10) NOT NULL,
                is_correct BOOLEAN NOT NULL,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
else:
    # SQLite使用（開発環境）
    import sqlite3
    from utils.pdf_processor import PDFProcessor
    from utils.database import init_db as sqlite_init_db, get_db_connection as sqlite_get_db_connection
    from utils.question_manager import QuestionManager
    
    def get_db_connection():
        return sqlite_get_db_connection('fe_exam.db')
    
    def init_db():
        sqlite_init_db('fe_exam.db')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# アプリケーション設定
app.config.update({
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

@login_manager.user_loader
def load_user(user_id):
    try:
        if DATABASE_URL:
            # PostgreSQL
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('SELECT id, username, email, is_admin FROM users WHERE id = %s', (user_id,))
            user_data = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user_data:
                return User(user_data['id'], user_data['username'], user_data['email'], user_data['is_admin'])
        else:
            # SQLite
            with get_db_connection() as conn:
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
    init_db()  # テーブル作成
    
    # デフォルト管理者作成
    try:
        admin_hash = generate_password_hash('admin123')
        
        if DATABASE_URL:
            # PostgreSQL
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    'INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, %s)',
                    ('admin', admin_hash, True)
                )
                conn.commit()
                print("デフォルト管理者ユーザー（admin/admin123）を作成しました")
            except psycopg2.IntegrityError:
                conn.rollback()
                print("管理者ユーザーは既に存在します")
            cursor.close()
            conn.close()
        else:
            # SQLite
            with get_db_connection() as conn:
                # ユーザーテーブル作成
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
                
                try:
                    conn.execute(
                        'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                        ('admin', admin_hash, 1)
                    )
                    print("デフォルト管理者ユーザー（admin/admin123）を作成しました")
                except sqlite3.IntegrityError:
                    print("管理者ユーザーは既に存在します")
                
                # サンプル問題作成（SQLiteのみ）
                try:
                    processor = PDFProcessor()
                    sample_questions = processor.create_sample_questions()
                    question_manager = QuestionManager('fe_exam.db')
                    saved_count = question_manager.save_questions(sample_questions)
                    print(f"サンプル問題 {saved_count}問を作成しました。")
                except Exception as e:
                    print(f"サンプル問題作成エラー: {e}")
    except Exception as e:
        print(f"初期化エラー: {e}")

init_database()

if not DATABASE_URL:
    question_manager = QuestionManager('fe_exam.db')

# デコレータ
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
            if DATABASE_URL:
                # PostgreSQL
                conn = get_db_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(
                    'SELECT id, username, email, password_hash, is_admin FROM users WHERE username = %s OR email = %s',
                    (username, username)
                )
                user_data = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if user_data and check_password_hash(user_data['password_hash'], password):
                    user = User(user_data['id'], user_data['username'], user_data['email'], user_data['is_admin'])
                    login_user(user, remember=remember)
                    flash(f'ようこそ、{user.username}さん！', 'success')
                    
                    next_page = request.args.get('next')
                    return redirect(next_page) if next_page else redirect(url_for('index'))
                else:
                    flash('ユーザー名またはパスワードが間違っています。', 'error')
            else:
                # SQLite
                with get_db_connection() as conn:
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
            
            if DATABASE_URL:
                # PostgreSQL
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # 重複チェック
                cursor.execute(
                    'SELECT id FROM users WHERE username = %s OR (email = %s AND email != %s)',
                    (username, email, '')
                )
                existing = cursor.fetchone()
                
                if existing:
                    flash('このユーザー名またはメールアドレスは既に使用されています。', 'error')
                    cursor.close()
                    conn.close()
                    return render_template('auth/register.html')
                
                cursor.execute(
                    'INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)',
                    (username, email, password_hash)
                )
                conn.commit()
                cursor.close()
                conn.close()
            else:
                # SQLite
                with get_db_connection() as conn:
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
        
        if DATABASE_URL:
            # PostgreSQL
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute('SELECT COUNT(*) as count FROM questions')
            stats['total_questions'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM user_answers')
            stats['total_answers'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM user_answers WHERE is_correct = true')
            stats['correct_answers'] = cursor.fetchone()['count']
            
            cursor.close()
            conn.close()
        else:
            # SQLite
            with get_db_connection() as conn:
                stats['total_questions'] = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
                stats['total_answers'] = conn.execute('SELECT COUNT(*) FROM user_answers').fetchone()[0]
                stats['correct_answers'] = conn.execute('SELECT COUNT(*) FROM user_answers WHERE is_correct = 1').fetchone()[0]
        
        stats['accuracy_rate'] = round((stats['correct_answers'] / stats['total_answers'] * 100), 1) if stats['total_answers'] > 0 else 0
        
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        app.logger.error(f"Dashboard error: {e}")
        return render_template('dashboard.html', stats={'total_questions': 0, 'total_answers': 0, 'correct_answers': 0, 'accuracy_rate': 0, 'recent_history': [], 'genre_stats': []})

# 簡単なルート（PostgreSQL環境では最小限の機能）
@app.route('/random')
@login_required
def random_question():
    if not DATABASE_URL and 'question_manager' in globals():
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
    if not DATABASE_URL and 'question_manager' in globals():
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
        
        if DATABASE_URL:
            # PostgreSQL
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM questions')
            stats['question_count'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users')
            stats['user_count'] = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
        else:
            # SQLite
            with get_db_connection() as conn:
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
