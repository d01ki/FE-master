"""
基本情報技術者試験 学習アプリ（PostgreSQL + ログイン機能付き）
Flask + Flask-Login + PostgreSQL を使用した学習プラットフォーム
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

# PostgreSQL オプショナルインポート
try:
    import psycopg2
    import psycopg2.extras
    HAS_POSTGRESQL = True
except ImportError:
    HAS_POSTGRESQL = False
    print("PostgreSQL support not available. Using SQLite fallback.")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# アプリケーション設定
app.config.update({
    'DATABASE_URL': os.environ.get('DATABASE_URL', 'sqlite:///fe_exam.db'),
    'UPLOAD_FOLDER': 'uploads',
    'JSON_FOLDER': 'json_questions'
})

# フォルダ作成
for folder in [app.config['UPLOAD_FOLDER'], app.config['JSON_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

# Flask-Login設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'このページにアクセスするにはログインが必要です。'
login_manager.login_message_category = 'info'

class User(UserMixin):
    def __init__(self, id, username, email=None, is_admin=False):
        self.id = id
        self.username = username
        self.email = email
        self.is_admin = is_admin

# データベース接続（PostgreSQL優先、フォールバックでSQLite）
def get_db_connection():
    database_url = app.config.get('DATABASE_URL')
    
    # PostgreSQL接続を試行
    if (HAS_POSTGRESQL and database_url and 
        (database_url.startswith('postgresql://') or database_url.startswith('postgres://'))):
        try:
            # postgres://をpostgresql://に変換（Heroku対応）
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            conn = psycopg2.connect(database_url)
            conn.cursor_factory = psycopg2.extras.RealDictCursor
            return conn
        except Exception as e:
            print(f"PostgreSQL接続エラー: {e}")
            print("SQLiteにフォールバック中...")
    
    # SQLite接続（フォールバック）
    conn = sqlite3.connect('fe_exam.db')
    conn.row_factory = sqlite3.Row
    return conn

def is_postgresql():
    """現在PostgreSQLを使用しているかどうかを判定"""
    database_url = app.config.get('DATABASE_URL')
    return (HAS_POSTGRESQL and database_url and 
            (database_url.startswith('postgresql://') or database_url.startswith('postgres://')))

def init_db():
    """データベース初期化"""
    if is_postgresql():
        # PostgreSQL用テーブル作成
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # ユーザーテーブル
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            username VARCHAR(50) UNIQUE NOT NULL,
                            email VARCHAR(100) UNIQUE,
                            password_hash VARCHAR(255) NOT NULL,
                            is_admin BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    
                    # 問題テーブル
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS questions (
                            id SERIAL PRIMARY KEY,
                            question_text TEXT NOT NULL,
                            choices TEXT NOT NULL,
                            correct_answer VARCHAR(10) NOT NULL,
                            explanation TEXT,
                            genre VARCHAR(100),
                            difficulty VARCHAR(50),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    
                    # 回答履歴テーブル
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS user_answers (
                            id SERIAL PRIMARY KEY,
                            question_id INTEGER REFERENCES questions(id),
                            user_answer VARCHAR(10) NOT NULL,
                            is_correct BOOLEAN NOT NULL,
                            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                conn.commit()
                print("✅ PostgreSQLテーブルを初期化しました")
        except Exception as e:
            print(f"PostgreSQL初期化エラー: {e}")
    else:
        # SQLite用テーブル作成
        with get_db_connection() as conn:
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
            print("✅ SQLiteテーブルを初期化しました")

@login_manager.user_loader
def load_user(user_id):
    try:
        with get_db_connection() as conn:
            if is_postgresql():
                # PostgreSQL
                with conn.cursor() as cur:
                    cur.execute('SELECT id, username, email, is_admin FROM users WHERE id = %s', (user_id,))
                    user_data = cur.fetchone()
            else:
                # SQLite
                user_data = conn.execute(
                    'SELECT id, username, email, is_admin FROM users WHERE id = ?', 
                    (user_id,)
                ).fetchone()
                
            if user_data:
                return User(user_data['id'], user_data['username'], user_data['email'], user_data['is_admin'])
    except Exception as e:
        print(f"ユーザーロードエラー: {e}")
    return None

def admin_required(f):
    """管理者権限デコレータ"""
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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        if not username or not password:
            flash('ユーザー名とパスワードを入力してください。', 'error')
            return render_template('auth/login.html')
        
        try:
            with get_db_connection() as conn:
                if is_postgresql():
                    # PostgreSQL
                    with conn.cursor() as cur:
                        cur.execute('''
                            SELECT id, username, email, password_hash, is_admin 
                            FROM users WHERE username = %s OR email = %s
                        ''', (username, username))
                        user_data = cur.fetchone()
                else:
                    # SQLite
                    user_data = conn.execute('''
                        SELECT id, username, email, password_hash, is_admin 
                        FROM users WHERE username = ? OR email = ?
                    ''', (username, username)).fetchone()
                
                if user_data and check_password_hash(user_data['password_hash'], password):
                    user = User(user_data['id'], user_data['username'], user_data['email'], user_data['is_admin'])
                    login_user(user, remember=remember)
                    flash(f'ようこそ、{user.username}さん！', 'success')
                    
                    next_page = request.args.get('next')
                    return redirect(next_page) if next_page else redirect(url_for('index'))
                else:
                    flash('ユーザー名またはパスワードが間違っています。', 'error')
        except Exception as e:
            flash('ログイン処理中にエラーが発生しました。', 'error')
            print(f"ログインエラー: {e}")
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
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
            with get_db_connection() as conn:
                # 既存ユーザーチェック
                if is_postgresql():
                    # PostgreSQL
                    with conn.cursor() as cur:
                        cur.execute('''
                            SELECT id FROM users 
                            WHERE username = %s OR (email = %s AND email != '')
                        ''', (username, email))
                        existing = cur.fetchone()
                        
                        if existing:
                            flash('このユーザー名またはメールアドレスは既に使用されています。', 'error')
                            return render_template('auth/register.html')
                        
                        cur.execute('''
                            INSERT INTO users (username, email, password_hash) 
                            VALUES (%s, %s, %s)
                        ''', (username, email, password_hash))
                    conn.commit()
                else:
                    # SQLite
                    existing = conn.execute('''
                        SELECT id FROM users 
                        WHERE username = ? OR (email = ? AND email != '')
                    ''', (username, email)).fetchone()
                    
                    if existing:
                        flash('このユーザー名またはメールアドレスは既に使用されています。', 'error')
                        return render_template('auth/register.html')
                    
                    conn.execute('''
                        INSERT INTO users (username, email, password_hash) 
                        VALUES (?, ?, ?)
                    ''', (username, email, password_hash))
                
                flash('登録が完了しました！ログインしてください。', 'success')
                return redirect(url_for('login'))
                
        except Exception as e:
            flash('登録中にエラーが発生しました。再度お試しください。', 'error')
            print(f"登録エラー: {e}")
    
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    flash(f'{username}さん、お疲れさまでした。', 'info')
    return redirect(url_for('login'))

# メインルート
@app.route('/')
@login_required
def index():
    """ダッシュボード"""
    try:
        with get_db_connection() as conn:
            if is_postgresql():
                # PostgreSQL
                with conn.cursor() as cur:
                    cur.execute('SELECT COUNT(*) as count FROM questions')
                    total_questions = cur.fetchone()['count']
                    
                    cur.execute('SELECT COUNT(*) as count FROM user_answers')
                    total_answers = cur.fetchone()['count']
                    
                    cur.execute('SELECT COUNT(*) as count FROM user_answers WHERE is_correct = true')
                    correct_answers = cur.fetchone()['count']
                    
                    cur.execute('''
                        SELECT q.question_text, ua.is_correct, ua.answered_at 
                        FROM user_answers ua 
                        JOIN questions q ON ua.question_id = q.id 
                        ORDER BY ua.answered_at DESC LIMIT 10
                    ''')
                    recent_history = cur.fetchall()
                    
                    cur.execute('''
                        SELECT q.genre, COUNT(*) as total,
                               SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) as correct
                        FROM user_answers ua 
                        JOIN questions q ON ua.question_id = q.id 
                        GROUP BY q.genre
                    ''')
                    genre_stats = cur.fetchall()
            else:
                # SQLite
                total_questions = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
                total_answers = conn.execute('SELECT COUNT(*) FROM user_answers').fetchone()[0]
                correct_answers = conn.execute('SELECT COUNT(*) FROM user_answers WHERE is_correct = 1').fetchone()[0]
                
                recent_history = [dict(row) for row in conn.execute('''
                    SELECT q.question_text, ua.is_correct, ua.answered_at 
                    FROM user_answers ua 
                    JOIN questions q ON ua.question_id = q.id 
                    ORDER BY ua.answered_at DESC LIMIT 10
                ''').fetchall()]
                
                genre_stats = [dict(row) for row in conn.execute('''
                    SELECT q.genre, COUNT(*) as total,
                           SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct
                    FROM user_answers ua 
                    JOIN questions q ON ua.question_id = q.id 
                    GROUP BY q.genre
                ''').fetchall()]
            
            stats = {
                'total_questions': total_questions,
                'total_answers': total_answers,
                'correct_answers': correct_answers,
                'accuracy_rate': round((correct_answers / total_answers * 100), 1) if total_answers > 0 else 0,
                'recent_history': recent_history if is_postgresql() else recent_history,
                'genre_stats': genre_stats if is_postgresql() else genre_stats
            }
        
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        print(f"ダッシュボードエラー: {e}")
        return render_template('dashboard.html', stats={
            'total_questions': 0, 'total_answers': 0, 'correct_answers': 0,
            'accuracy_rate': 0, 'recent_history': [], 'genre_stats': []
        })

# 問題管理クラス
class QuestionManager:
    def get_random_question(self):
        try:
            with get_db_connection() as conn:
                if is_postgresql():
                    # PostgreSQL
                    with conn.cursor() as cur:
                        cur.execute('SELECT * FROM questions ORDER BY RANDOM() LIMIT 1')
                        question = cur.fetchone()
                else:
                    # SQLite
                    question = conn.execute('SELECT * FROM questions ORDER BY RANDOM() LIMIT 1').fetchone()
                
                if question:
                    return {
                        'id': question['id'],
                        'question_text': question['question_text'],
                        'choices': json.loads(question['choices']),
                        'correct_answer': question['correct_answer'],
                        'explanation': question['explanation'],
                        'genre': question['genre'],
                        'difficulty': question['difficulty']
                    }
        except Exception as e:
            print(f"ランダム問題取得エラー: {e}")
        return None
    
    def get_question(self, question_id):
        try:
            with get_db_connection() as conn:
                if is_postgresql():
                    # PostgreSQL
                    with conn.cursor() as cur:
                        cur.execute('SELECT * FROM questions WHERE id = %s', (question_id,))
                        question = cur.fetchone()
                else:
                    # SQLite
                    question = conn.execute('SELECT * FROM questions WHERE id = ?', (question_id,)).fetchone()
                
                if question:
                    return {
                        'id': question['id'],
                        'question_text': question['question_text'],
                        'choices': json.loads(question['choices']),
                        'correct_answer': question['correct_answer'],
                        'explanation': question['explanation'],
                        'genre': question['genre'],
                        'difficulty': question['difficulty']
                    }
        except Exception as e:
            print(f"問題取得エラー: {e}")
        return None
    
    def check_answer(self, question_id, user_answer):
        question = self.get_question(question_id)
        if question:
            is_correct = user_answer == question['correct_answer']
            return {
                'is_correct': is_correct,
                'correct_answer': question['correct_answer'],
                'explanation': question['explanation']
            }
        return {'is_correct': False, 'correct_answer': '', 'explanation': ''}
    
    def save_answer_history(self, question_id, user_answer, is_correct):
        try:
            with get_db_connection() as conn:
                if is_postgresql():
                    # PostgreSQL
                    with conn.cursor() as cur:
                        cur.execute('''
                            INSERT INTO user_answers (question_id, user_answer, is_correct) 
                            VALUES (%s, %s, %s)
                        ''', (question_id, user_answer, is_correct))
                    conn.commit()
                else:
                    # SQLite
                    conn.execute('''
                        INSERT INTO user_answers (question_id, user_answer, is_correct) 
                        VALUES (?, ?, ?)
                    ''', (question_id, user_answer, is_correct))
        except Exception as e:
            print(f"回答履歴保存エラー: {e}")

# 初期化処理
def initialize_app():
    init_db()
    
    # サンプル問題作成
    sample_questions = [
        {
            'question_text': 'スタック（Stack）について正しい説明はどれか。',
            'choices': ['FIFO（First In First Out）の原則で動作する', 'LIFO（Last In First Out）の原則で動作する', 'ランダムアクセスが可能である', '要素の追加はできるが削除はできない'],
            'correct_answer': 'B',
            'explanation': 'スタック（Stack）は、LIFO（Last In First Out、後入れ先出し）の原則で動作するデータ構造です。',
            'genre': 'アルゴリズム・データ構造',
            'difficulty': '基礎'
        },
        {
            'question_text': 'データベースの正規化の目的として正しいものはどれか。',
            'choices': ['データの冗長性を排除し、データの一貫性を保つ', 'データの処理速度を向上させる', 'データベースのファイルサイズを小さくする', 'セキュリティを向上させる'],
            'correct_answer': 'A',
            'explanation': '正規化の主な目的は、データの冗長性（重複）を排除し、データの一貫性と整合性を保つことです。',
            'genre': 'データベース',
            'difficulty': '基礎'
        },
        {
            'question_text': 'OSI参照モデルの第3層（ネットワーク層）の主な機能はどれか。',
            'choices': ['物理的な信号の伝送', 'データフレームの作成', 'パケットのルーティング', 'アプリケーションとの通信'],
            'correct_answer': 'C',
            'explanation': 'ネットワーク層は、パケットのルーティング、つまり送信先までの最適な経路を決定する機能を持ちます。',
            'genre': 'ネットワーク',
            'difficulty': '基礎'
        }
    ]
    
    try:
        with get_db_connection() as conn:
            for question in sample_questions:
                if is_postgresql():
                    # PostgreSQL
                    with conn.cursor() as cur:
                        cur.execute('SELECT id FROM questions WHERE question_text = %s', (question['question_text'],))
                        existing = cur.fetchone()
                        
                        if not existing:
                            cur.execute('''
                                INSERT INTO questions (question_text, choices, correct_answer, explanation, genre, difficulty)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            ''', (
                                question['question_text'],
                                json.dumps(question['choices']),
                                question['correct_answer'],
                                question['explanation'],
                                question['genre'],
                                question['difficulty']
                            ))
                    conn.commit()
                else:
                    # SQLite
                    existing = conn.execute(
                        'SELECT id FROM questions WHERE question_text = ?',
                        (question['question_text'],)
                    ).fetchone()
                    
                    if not existing:
                        conn.execute('''
                            INSERT INTO questions (question_text, choices, correct_answer, explanation, genre, difficulty)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            question['question_text'],
                            json.dumps(question['choices']),
                            question['correct_answer'],
                            question['explanation'],
                            question['genre'],
                            question['difficulty']
                        ))
        
        print("✅ サンプル問題を作成しました")
    except Exception as e:
        print(f"サンプル問題作成エラー: {e}")
    
    # デフォルト管理者作成
    try:
        admin_hash = generate_password_hash('admin123')
        with get_db_connection() as conn:
            if is_postgresql():
                # PostgreSQL
                try:
                    with conn.cursor() as cur:
                        cur.execute('''
                            INSERT INTO users (username, password_hash, is_admin) 
                            VALUES (%s, %s, %s)
                        ''', ('admin', admin_hash, True))
                    conn.commit()
                    print("✅ デフォルト管理者ユーザー（admin/admin123）を作成しました")
                except psycopg2.IntegrityError:
                    conn.rollback()
                    pass  # 既に存在する場合
            else:
                # SQLite
                try:
                    conn.execute('''
                        INSERT INTO users (username, password_hash, is_admin) 
                        VALUES (?, ?, ?)
                    ''', ('admin', admin_hash, 1))
                    print("✅ デフォルト管理者ユーザー（admin/admin123）を作成しました")
                except sqlite3.IntegrityError:
                    pass  # 既に存在する場合
    except Exception as e:
        print(f"管理者作成エラー: {e}")

# グローバルインスタンス
question_manager = QuestionManager()

# 問題関連ルート
@app.route('/questions/<int:question_id>')
@login_required
def show_question(question_id):
    question = question_manager.get_question(question_id)
    if not question:
        flash('問題が見つかりません。', 'error')
        return redirect(url_for('index'))
    return render_template('question.html', question=question)

@app.route('/questions/<int:question_id>/answer', methods=['POST'])
@login_required
def submit_answer(question_id):
    try:
        data = request.get_json()
        user_answer = data.get('answer')
        
        if not user_answer:
            return jsonify({'error': '解答が選択されていません'}), 400
        
        result = question_manager.check_answer(question_id, user_answer)
        question_manager.save_answer_history(question_id, user_answer, result['is_correct'])
        
        return jsonify(result)
    except Exception as e:
        print(f"解答提出エラー: {e}")
        return jsonify({'error': '解答処理中にエラーが発生しました'}), 500

@app.route('/random')
@login_required
def random_question():
    question = question_manager.get_random_question()
    if not question:
        flash('問題が見つかりません。', 'error')
        return redirect(url_for('index'))
    return redirect(url_for('show_question', question_id=question['id']))

@app.route('/mock_exam')
@login_required
def mock_exam():
    flash('模擬試験機能は開発中です。', 'info')
    return redirect(url_for('index'))

@app.route('/genre_practice')
@login_required
def genre_practice():
    flash('ジャンル別練習機能は開発中です。', 'info')
    return redirect(url_for('index'))

@app.route('/history')
@login_required
def history():
    flash('学習履歴機能は開発中です。', 'info')
    return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin():
    try:
        with get_db_connection() as conn:
            if is_postgresql():
                # PostgreSQL
                with conn.cursor() as cur:
                    cur.execute('SELECT COUNT(*) as count FROM questions')
                    question_count = cur.fetchone()['count']
                    cur.execute('SELECT COUNT(*) as count FROM users')
                    user_count = cur.fetchone()['count']
                    cur.execute('SELECT DISTINCT genre FROM questions WHERE genre IS NOT NULL')
                    genres = [row['genre'] for row in cur.fetchall()]
            else:
                # SQLite
                question_count = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
                user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
                genres = [row[0] for row in conn.execute('SELECT DISTINCT genre FROM questions WHERE genre IS NOT NULL').fetchall()]
            
            admin_data = {
                'question_count': question_count,
                'user_count': user_count,
                'genres': genres
            }
        
        return render_template('admin.html', data=admin_data)
    except Exception as e:
        print(f"管理画面エラー: {e}")
        return render_template('admin.html', data={'question_count': 0, 'user_count': 0, 'genres': []})

# エラーハンドラ
@app.errorhandler(404)
def not_found_error(error):
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(error):
    print(f"500エラー: {error}")
    return redirect(url_for('index'))

# アプリケーション初期化
initialize_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
