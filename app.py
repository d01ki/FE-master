"""
基本情報技術者試験 学習アプリ（ログイン機能付き）
Flask + Flask-Login + SQLite/PostgreSQL + Tailwind CSS を使用した学習プラットフォーム
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
from utils.pdf_processor import PDFProcessor
from utils.database import init_db, get_db_connection
from utils.question_manager import QuestionManager

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# アプリケーション設定
app.config['DATABASE'] = 'fe_exam.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['JSON_FOLDER'] = 'json_questions'
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'fe2025admin')

# アップロードフォルダとJSONフォルダを作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['JSON_FOLDER'], exist_ok=True)

# Flask-Loginの初期化
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'このページにアクセスするにはログインが必要です。'

# ユーザーモデル
class User(UserMixin):
    def __init__(self, id, username, email=None, is_admin=False):
        self.id = id
        self.username = username
        self.email = email
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    try:
        with get_db_connection(app.config['DATABASE']) as conn:
            user_data = conn.execute(
                'SELECT id, username, email, is_admin FROM users WHERE id = ?', 
                (user_id,)
            ).fetchone()
            if user_data:
                return User(user_data[0], user_data[1], user_data[2], user_data[3])
    except:
        pass
    return None

# データベースの初期化
def init_database():
    if not os.path.exists(app.config['DATABASE']):
        print("データベースを初期化しています...")
        init_db(app.config['DATABASE'])
        
        # ユーザーテーブルも作成
        with get_db_connection(app.config['DATABASE']) as conn:
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
            
            # デフォルト管理者ユーザー作成
            admin_hash = generate_password_hash('admin123')
            try:
                conn.execute(
                    'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                    ('admin', admin_hash, 1)
                )
                print("デフォルト管理者ユーザー（admin/admin123）を作成しました")
            except sqlite3.IntegrityError:
                print("管理者ユーザーは既に存在します")
        
        # サンプル問題を自動作成
        try:
            processor = PDFProcessor()
            sample_questions = processor.create_sample_questions()
            question_manager = QuestionManager(app.config['DATABASE'])
            saved_count = question_manager.save_questions(sample_questions)
            print(f"サンプル問題 {saved_count}問を作成しました。")
        except Exception as e:
            print(f"サンプル問題作成中にエラーが発生しました: {e}")
    else:
        # 既存データベースにユーザーテーブルがない場合は追加
        try:
            with get_db_connection(app.config['DATABASE']) as conn:
                conn.execute('SELECT 1 FROM users LIMIT 1')
        except sqlite3.OperationalError:
            with get_db_connection(app.config['DATABASE']) as conn:
                conn.execute('''
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE,
                        password_hash TEXT NOT NULL,
                        is_admin INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # デフォルト管理者ユーザー作成
                admin_hash = generate_password_hash('admin123')
                conn.execute(
                    'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                    ('admin', admin_hash, 1)
                )
                print("ユーザーテーブルとデフォルト管理者ユーザーを追加しました")

init_database()

# QuestionManagerの初期化
question_manager = QuestionManager(app.config['DATABASE'])

# JSONフォルダの問題を自動読み込み
def load_json_questions_on_startup():
    """起動時にJSONフォルダの問題を自動読み込み"""
    try:
        if os.path.exists(app.config['JSON_FOLDER']):
            loaded_files = []
            total_questions = 0
            
            for filename in os.listdir(app.config['JSON_FOLDER']):
                if filename.endswith('.json'):
                    json_filepath = os.path.join(app.config['JSON_FOLDER'], filename)
                    try:
                        with open(json_filepath, 'r', encoding='utf-8') as json_file:
                            questions = json.load(json_file)
                        
                        saved_count = question_manager.save_questions(questions)
                        if saved_count > 0:
                            loaded_files.append({
                                'filename': filename,
                                'count': saved_count
                            })
                            total_questions += saved_count
                    except Exception as e:
                        print(f"ファイル {filename} の読み込みでエラー: {e}")
                        continue
            
            if loaded_files:
                print(f"JSONフォルダから {len(loaded_files)}個のファイルを自動読み込み、{total_questions}問をデータベースに追加しました。")
    except Exception as e:
        print(f"JSON自動読み込み中にエラー: {e}")

load_json_questions_on_startup()

def admin_required(f):
    """管理者認証デコレータ"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('管理者権限が必要です。', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def parse_filename_info(filename):
    """ファイル名から年度と期の情報を抽出"""
    pattern = r'(\d{4})r(\d{2})_[^_]+_[^_]+_(\w+)\.json'
    match = re.match(pattern, filename)
    if match:
        year = int(match.group(1))
        era_year = int(match.group(2))
        season = match.group(3)
        season_jp = "春期" if season == "spring" else "秋期" if season == "autumn" else season
        return {
            'year': year,
            'era_year': era_year,
            'season': season,
            'season_jp': season_jp,
            'display_name': f'{year}年{season_jp}'
        }
    return None

# ログイン・ログアウト関連ルート
@app.route('/login', methods=['GET', 'POST'])
def login():
    """ユーザーログイン"""
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
            with get_db_connection(app.config['DATABASE']) as conn:
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
    """新規ユーザー登録"""
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
            with get_db_connection(app.config['DATABASE']) as conn:
                existing = conn.execute(
                    'SELECT id FROM users WHERE username = ? OR (email = ? AND email != "")',
                    (username, email)
                ).fetchone()
                
                if existing:
                    flash('このユーザー名またはメールアドレスは既に使用されています。', 'error')
                    return render_template('auth/register.html')
                
                password_hash = generate_password_hash(password)
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
    """ログアウト"""
    logout_user()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('login'))

# 元の機能（ログイン必須に変更）
@app.route('/')
@login_required
def index():
    """メインページ - ダッシュボード表示"""
    try:
        with get_db_connection(app.config['DATABASE']) as conn:
            total_questions = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
            total_answers = conn.execute('SELECT COUNT(*) FROM user_answers').fetchone()[0]
            correct_answers = conn.execute('SELECT COUNT(*) FROM user_answers WHERE is_correct = 1').fetchone()[0]
            
            accuracy_rate = round((correct_answers / total_answers * 100), 1) if total_answers > 0 else 0
            
            recent_history = conn.execute('''
                SELECT q.question_text, ua.is_correct, ua.answered_at 
                FROM user_answers ua 
                JOIN questions q ON ua.question_id = q.id 
                ORDER BY ua.answered_at DESC 
                LIMIT 10
            ''').fetchall()
            
            genre_stats = conn.execute('''
                SELECT q.genre, 
                       COUNT(*) as total,
                       SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct
                FROM user_answers ua 
                JOIN questions q ON ua.question_id = q.id 
                GROUP BY q.genre
            ''').fetchall()
            
            stats = {
                'total_questions': total_questions,
                'total_answers': total_answers,
                'correct_answers': correct_answers,
                'accuracy_rate': accuracy_rate,
                'recent_history': [dict(row) for row in recent_history],
                'genre_stats': [dict(row) for row in genre_stats]
            }
        
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        app.logger.error(f"Dashboard error: {e}")
        stats = {
            'total_questions': 0,
            'total_answers': 0,
            'correct_answers': 0,
            'accuracy_rate': 0,
            'recent_history': [],
            'genre_stats': []
        }
        return render_template('dashboard.html', stats=stats)

@app.route('/questions/<int:question_id>')
@login_required
def show_question(question_id):
    """個別問題の表示"""
    try:
        question = question_manager.get_question(question_id)
        if not question:
            return render_template('error.html', message='問題が見つかりません'), 404
        
        return render_template('question.html', question=question)
    except Exception as e:
        app.logger.error(f"Show question error: {e}")
        return render_template('error.html', message='問題の表示中にエラーが発生しました'), 500

@app.route('/questions/<int:question_id>/answer', methods=['POST'])
@login_required
def submit_answer(question_id):
    """解答の提出と判定"""
    try:
        data = request.get_json()
        user_answer = data.get('answer')
        
        if not user_answer:
            return jsonify({'error': '解答が選択されていません'}), 400
        
        result = question_manager.check_answer(question_id, user_answer)
        question_manager.save_answer_history(question_id, user_answer, result['is_correct'])
        
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Submit answer error: {e}")
        return jsonify({'error': '解答処理中にエラーが発生しました'}), 500

@app.route('/practice/<genre>')
@login_required
def practice_by_genre(genre):
    """ジャンル別練習"""
    try:
        questions = question_manager.get_questions_by_genre(genre)
        
        if not questions:
            return render_template('error.html', message=f'ジャンル "{genre}" の問題が見つかりません'), 404
        
        random.shuffle(questions)
        
        return render_template('practice.html', questions=questions, genre=genre)
    except Exception as e:
        app.logger.error(f"Practice error: {e}")
        return render_template('error.html', message='練習問題の表示中にエラーが発生しました'), 500

@app.route('/genre_practice')
@login_required
def genre_practice():
    """ジャンル別演習メニュー"""
    try:
        genres = question_manager.get_available_genres()
        genre_counts = question_manager.get_question_count_by_genre()
        
        with get_db_connection(app.config['DATABASE']) as conn:
            genre_stats = conn.execute('''
                SELECT q.genre, 
                       COUNT(*) as total,
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
    except Exception as e:
        app.logger.error(f"Genre practice error: {e}")
        return render_template('error.html', message='ジャンル別演習の準備中にエラーが発生しました'), 500

@app.route('/mock_exam')
@login_required
def mock_exam():
    """模擬試験年度選択画面"""
    try:
        json_files = []
        if os.path.exists(app.config['JSON_FOLDER']):
            for filename in os.listdir(app.config['JSON_FOLDER']):
                if filename.endswith('.json'):
                    file_info = parse_filename_info(filename)
                    if file_info:
                        json_files.append({
                            'filename': filename,
                            'info': file_info
                        })
        
        json_files.sort(key=lambda x: (x['info']['year'], x['info']['season']), reverse=True)
        
        if not json_files:
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
                return render_template('error.html', message='問題が登録されていません。管理者に問題の登録を依頼してください。'), 404
        
        return render_template('mock_exam_select.html', exam_files=json_files)
    except Exception as e:
        app.logger.error(f"Mock exam error: {e}")
        return render_template('error.html', message='模擬試験の準備中にエラーが発生しました'), 500

@app.route('/random')
@login_required
def random_question():
    """ランダム問題への直接アクセス"""
    try:
        question = question_manager.get_random_question()
        if not question:
            flash('問題が見つかりません。管理者に問題の登録を依頼してください。', 'error')
            return redirect(url_for('index'))
        
        return redirect(url_for('show_question', question_id=question['id']))
    except Exception as e:
        app.logger.error(f"Random question error: {e}")
        flash('ランダム問題の表示中にエラーが発生しました。', 'error')
        return redirect(url_for('index'))

@app.route('/history')
@login_required
def history():
    """学習履歴の表示"""
    try:
        with get_db_connection(app.config['DATABASE']) as conn:
            detailed_history = conn.execute('''
                SELECT q.question_text, q.genre, ua.user_answer, ua.is_correct, ua.answered_at,
                       q.correct_answer, q.explanation
                FROM user_answers ua 
                JOIN questions q ON ua.question_id = q.id 
                ORDER BY ua.answered_at DESC 
                LIMIT 50
            ''').fetchall()
            
            daily_stats = conn.execute('''
                SELECT DATE(answered_at) as date, 
                       COUNT(*) as total,
                       SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
                FROM user_answers 
                GROUP BY DATE(answered_at) 
                ORDER BY date DESC 
                LIMIT 30
            ''').fetchall()
            
            history_data = {
                'detailed_history': [dict(row) for row in detailed_history],
                'daily_stats': [dict(row) for row in daily_stats]
            }
        
        return render_template('history.html', history=history_data)
    except Exception as e:
        app.logger.error(f"History error: {e}")
        return render_template('error.html', message='学習履歴の表示中にエラーが発生しました'), 500

# 管理者機能（元のまま）
@app.route('/admin')
@admin_required
def admin():
    """管理画面"""
    try:
        with get_db_connection(app.config['DATABASE']) as conn:
            question_count = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
            user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            genres = conn.execute('SELECT DISTINCT genre FROM questions').fetchall()
            
            admin_data = {
                'question_count': question_count,
                'user_count': user_count,
                'genres': [row[0] for row in genres]
            }
        
        return render_template('admin.html', data=admin_data)
    except Exception as e:
        app.logger.error(f"Admin error: {e}")
        return render_template('error.html', message='管理画面の表示中にエラーが発生しました'), 500

@app.route('/api/questions/random')
@login_required
def get_random_question():
    """ランダムな問題を1問取得するAPI"""
    try:
        question = question_manager.get_random_question()
        if not question:
            return jsonify({'error': '問題が見つかりません'}), 404
        
        return jsonify(question)
    except Exception as e:
        app.logger.error(f"Get random question error: {e}")
        return jsonify({'error': 'ランダム問題の取得中にエラーが発生しました'}), 500

@app.errorhandler(404)
def not_found_error(error):
    """404エラーハンドラ"""
    return render_template('error.html', message='ページが見つかりません'), 404

@app.errorhandler(500)
def internal_error(error):
    """500エラーハンドラ"""
    app.logger.error(f"Internal error: {error}")
    return render_template('error.html', message='内部サーバーエラーが発生しました'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
