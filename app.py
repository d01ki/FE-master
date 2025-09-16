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

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# アプリケーション設定
app.config.update({
    'DATABASE': 'fe_exam.db',
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

class User(UserMixin):
    def __init__(self, id, username, email=None, is_admin=False):
        self.id = id
        self.username = username
        self.email = email
        self.is_admin = is_admin

# データベース接続
def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
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

@login_manager.user_loader
def load_user(user_id):
    try:
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

# QuestionManagerクラス
class QuestionManager:
    def __init__(self):
        self._create_sample_questions()
    
    def _create_sample_questions(self):
        """サンプル問題を作成"""
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
            },
            {
                'question_text': 'オブジェクト指向の三大要素として正しいものはどれか。',
                'choices': ['継承・多態性・抽象化', 'カプセル化・継承・多態性', 'カプセル化・継承・抽象化', '継承・多態性・インターフェース'],
                'correct_answer': 'B',
                'explanation': 'オブジェクト指向の三大要素は、カプセル化（Encapsulation）、継承（Inheritance）、多態性（Polymorphism）です。',
                'genre': 'プログラミング',
                'difficulty': '基礎'
            },
            {
                'question_text': 'ウォーターフォール開発手法の特徴として正しいものはどれか。',
                'choices': ['各工程を並行して進める', '要求分析→設計→実装→テストの順に進める', '短期間で反復開発を行う', '顧客との対話を重視する'],
                'correct_answer': 'B',
                'explanation': 'ウォーターフォール開発手法は、要求分析→設計→実装→テスト→保守の順に段階的に進める開発手法です。',
                'genre': 'ソフトウェア工学',
                'difficulty': '基礎'
            }
        ]
        
        try:
            with get_db_connection() as conn:
                for question in sample_questions:
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
        except Exception as e:
            print(f"サンプル問題作成エラー: {e}")
    
    def get_random_question(self):
        try:
            with get_db_connection() as conn:
                question = conn.execute(
                    'SELECT * FROM questions ORDER BY RANDOM() LIMIT 1'
                ).fetchone()
                
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
            print(f"Random question error: {e}")
        return None
    
    def get_question(self, question_id):
        try:
            with get_db_connection() as conn:
                question = conn.execute(
                    'SELECT * FROM questions WHERE id = ?', (question_id,)
                ).fetchone()
                
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
            print(f"Get question error: {e}")
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
                conn.execute('''
                    INSERT INTO user_answers (question_id, user_answer, is_correct)
                    VALUES (?, ?, ?)
                ''', (question_id, user_answer, is_correct))
        except Exception as e:
            print(f"Save answer error: {e}")
    
    def get_questions_by_genre(self, genre):
        try:
            with get_db_connection() as conn:
                questions = conn.execute(
                    'SELECT * FROM questions WHERE genre = ?', (genre,)
                ).fetchall()
                
                return [{
                    'id': q['id'],
                    'question_text': q['question_text'],
                    'choices': json.loads(q['choices']),
                    'correct_answer': q['correct_answer'],
                    'explanation': q['explanation'],
                    'genre': q['genre'],
                    'difficulty': q['difficulty']
                } for q in questions]
        except Exception as e:
            print(f"Get questions by genre error: {e}")
        return []
    
    def get_available_genres(self):
        try:
            with get_db_connection() as conn:
                genres = conn.execute(
                    'SELECT DISTINCT genre FROM questions WHERE genre IS NOT NULL'
                ).fetchall()
                return [genre[0] for genre in genres if genre[0]]
        except Exception as e:
            print(f"Get genres error: {e}")
        return []
    
    def get_question_count_by_genre(self):
        try:
            with get_db_connection() as conn:
                counts = conn.execute('''
                    SELECT genre, COUNT(*) as count 
                    FROM questions 
                    WHERE genre IS NOT NULL 
                    GROUP BY genre
                ''').fetchall()
                return {count[0]: count[1] for count in counts}
        except Exception as e:
            print(f"Get question count error: {e}")
        return {}
    
    def get_total_questions(self):
        try:
            with get_db_connection() as conn:
                count = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
                return count
        except Exception as e:
            print(f"Get total questions error: {e}")
        return 0
    
    def get_random_questions(self, count):
        try:
            with get_db_connection() as conn:
                questions = conn.execute(
                    'SELECT * FROM questions ORDER BY RANDOM() LIMIT ?', (count,)
                ).fetchall()
                
                return [{
                    'id': q['id'],
                    'question_text': q['question_text'],
                    'choices': json.loads(q['choices']),
                    'correct_answer': q['correct_answer'],
                    'explanation': q['explanation'],
                    'genre': q['genre'],
                    'difficulty': q['difficulty']
                } for q in questions]
        except Exception as e:
            print(f"Get random questions error: {e}")
        return []

    def add_question(self, question_data):
        """管理者が問題を追加"""
        try:
            with get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO questions (question_text, choices, correct_answer, explanation, genre, difficulty)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    question_data['question_text'],
                    json.dumps(question_data['choices']),
                    question_data['correct_answer'],
                    question_data.get('explanation', ''),
                    question_data.get('genre', ''),
                    question_data.get('difficulty', '基礎')
                ))
                return True
        except Exception as e:
            print(f"Add question error: {e}")
            return False

# データベース初期化
def initialize_app():
    init_db()
    
    # デフォルト管理者作成
    try:
        admin_hash = generate_password_hash('admin123')
        with get_db_connection() as conn:
            try:
                conn.execute(
                    'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                    ('admin', admin_hash, 1)
                )
                print("✅ デフォルト管理者ユーザー（admin/admin123）を作成しました")
            except sqlite3.IntegrityError:
                pass  # 既に存在する場合
    except Exception as e:
        print(f"管理者作成エラー: {e}")

initialize_app()
question_manager = QuestionManager()

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
            with get_db_connection() as conn:
                user_data = conn.execute(
                    'SELECT id, username, email, password_hash, is_admin FROM users WHERE username = ? OR email = ?',
                    (username, username)
                ).fetchone()
                
                if user_data and check_password_hash(user_data[3], password):
                    user = User(user_data[0], user_data[1], user_data[2], user_data[4])
                    login_user(user, remember=remember)
                    flash(f'{user.username}でログインしました', 'success')
                    
                    next_page = request.args.get('next')
                    return redirect(next_page) if next_page else redirect(url_for('index'))
                else:
                    flash('ユーザー名またはパスワードが間違っています。', 'error')
        except Exception as e:
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
        with get_db_connection() as conn:
            stats = {
                'total_questions': conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0],
                'total_answers': conn.execute('SELECT COUNT(*) FROM user_answers').fetchone()[0],
                'correct_answers': conn.execute('SELECT COUNT(*) FROM user_answers WHERE is_correct = 1').fetchone()[0],
            }
            stats['accuracy_rate'] = round((stats['correct_answers'] / stats['total_answers'] * 100), 1) if stats['total_answers'] > 0 else 0
            
            stats['recent_history'] = [dict(row) for row in conn.execute('''
                SELECT q.question_text, ua.is_correct, ua.answered_at 
                FROM user_answers ua 
                JOIN questions q ON ua.question_id = q.id 
                ORDER BY ua.answered_at DESC LIMIT 10
            ''').fetchall()]
            
            stats['genre_stats'] = [dict(row) for row in conn.execute('''
                SELECT q.genre, COUNT(*) as total,
                       SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct
                FROM user_answers ua 
                JOIN questions q ON ua.question_id = q.id 
                GROUP BY q.genre
            ''').fetchall()]
        
        return render_template('dashboard.html', stats=stats)
    except:
        return render_template('dashboard.html', stats={
            'total_questions': 0, 'total_answers': 0, 'correct_answers': 0,
            'accuracy_rate': 0, 'recent_history': [], 'genre_stats': []
        })

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
    except:
        return jsonify({'error': '解答処理中にエラーが発生しました'}), 500

@app.route('/random')
@login_required
def random_question():
    question = question_manager.get_random_question()
    if not question:
        flash('問題が見つかりません。', 'error')
        return redirect(url_for('index'))
    return redirect(url_for('show_question', question_id=question['id']))

@app.route('/practice/<genre>')
@login_required
def practice_by_genre(genre):
    questions = question_manager.get_questions_by_genre(genre)
    if not questions:
        flash(f'ジャンル "{genre}" の問題が見つかりません。', 'error')
        return redirect(url_for('genre_practice'))
    random.shuffle(questions)
    return render_template('practice.html', questions=questions, genre=genre)

@app.route('/genre_practice')
@login_required
def genre_practice():
    genres = question_manager.get_available_genres()
    genre_counts = question_manager.get_question_count_by_genre()
    
    with get_db_connection() as conn:
        genre_stats = conn.execute('''
            SELECT q.genre, COUNT(*) as total,
                   SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct
            FROM user_answers ua 
            JOIN questions q ON ua.question_id = q.id 
            GROUP BY q.genre
        ''').fetchall()
    
    stats_dict = {stat[0]: {'total': stat[1], 'correct': stat[2]} for stat in genre_stats}
    
    genre_info = []
    for genre in genres:
        count = genre_counts.get(genre, 0)
        stat = stats_dict.get(genre, {'total': 0, 'correct': 0})
        accuracy = round((stat['correct'] / stat['total'] * 100), 1) if stat['total'] > 0 else 0
        
        genre_info.append({
            'name': genre,
            'count': count,
            'answered': stat['total'],
            'accuracy': accuracy
        })
    
    return render_template('genre_practice.html', genres=genre_info)

@app.route('/mock_exam')
@login_required
def mock_exam():
    total_questions = question_manager.get_total_questions()
    if total_questions > 0:
        exam_questions_count = min(total_questions, 20)
        questions = question_manager.get_random_questions(exam_questions_count)
        session['exam_start_time'] = datetime.now().isoformat()
        session['exam_questions'] = [q['id'] for q in questions]
        return render_template('mock_exam_practice.html', 
                             questions=questions, 
                             exam_info={'display_name': 'データベース問題'})
    else:
        flash('問題が登録されていません。', 'error')
        return redirect(url_for('index'))

@app.route('/history')
@login_required
def history():
    try:
        with get_db_connection() as conn:
            detailed_history = [dict(row) for row in conn.execute('''
                SELECT q.question_text, q.genre, ua.user_answer, ua.is_correct, ua.answered_at,
                       q.correct_answer, q.explanation
                FROM user_answers ua 
                JOIN questions q ON ua.question_id = q.id 
                ORDER BY ua.answered_at DESC LIMIT 50
            ''').fetchall()]
            
            daily_stats = [dict(row) for row in conn.execute('''
                SELECT DATE(answered_at) as date, COUNT(*) as total,
                       SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
                FROM user_answers 
                GROUP BY DATE(answered_at) 
                ORDER BY date DESC LIMIT 30
            ''').fetchall()]
            
            history_data = {'detailed_history': detailed_history, 'daily_stats': daily_stats}
        
        return render_template('history.html', history=history_data)
    except:
        return render_template('history.html', history={'detailed_history': [], 'daily_stats': []})

@app.route('/admin')
@admin_required
def admin():
    try:
        with get_db_connection() as conn:
            admin_data = {
                'question_count': conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0],
                'user_count': conn.execute('SELECT COUNT(*) FROM users').fetchone()[0],
                'genres': [row[0] for row in conn.execute('SELECT DISTINCT genre FROM questions').fetchall()]
            }
        return render_template('admin.html', data=admin_data)
    except:
        return render_template('admin.html', data={'question_count': 0, 'user_count': 0, 'genres': []})

@app.route('/admin/add_question', methods=['POST'])
@admin_required
def add_question():
    try:
        data = request.get_json()
        if question_manager.add_question(data):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '問題の追加に失敗しました'})
    except:
        return jsonify({'success': False, 'error': 'エラーが発生しました'})

# エラーハンドラ
@app.errorhandler(404)
def not_found_error(error):
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(error):
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
