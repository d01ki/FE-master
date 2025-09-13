"""
基本情報技術者試験 学習アプリ
Flask + PostgreSQL + Tailwind CSS を使用した学習プラットフォーム
ユーザー認証機能付き
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import psycopg2
import psycopg2.extras
import json
import os
import re
from datetime import datetime
import random
import bcrypt
from functools import wraps
from utils.pdf_processor import PDFProcessor
from utils.database_pg import init_db, get_db_connection
from utils.question_manager_pg import QuestionManager

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Login Manager設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'ログインが必要です。'
login_manager.login_message_category = 'info'

# アプリケーション設定
app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/fe_exam_db')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['JSON_FOLDER'] = 'json_questions'
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'fe2025admin')

# フォルダを作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['JSON_FOLDER'], exist_ok=True)

# データベースの初期化
try:
    print("データベースを初期化しています...")
    init_db(app.config['DATABASE_URL'])
    print("データベース初期化完了")
except Exception as e:
    print(f"データベース初期化エラー: {e}")

# QuestionManagerの初期化
question_manager = QuestionManager(app.config['DATABASE_URL'])

class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    try:
        with get_db_connection(app.config['DATABASE_URL']) as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('SELECT id, username, email FROM users WHERE id = %s', (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                return User(user_data['id'], user_data['username'], user_data['email'])
    except Exception as e:
        app.logger.error(f"User load error: {e}")
    return None

def admin_required(f):
    """管理者認証デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin_login'))
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

@app.route('/')
def index():
    """メインページ - ダッシュボード表示"""
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        
        with get_db_connection(app.config['DATABASE_URL']) as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute('SELECT COUNT(*) as count FROM questions')
            total_questions = cursor.fetchone()['count']
            
            if user_id:
                cursor.execute('SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s', (user_id,))
                total_answers = cursor.fetchone()['count']
                
                cursor.execute('SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s AND is_correct = true', (user_id,))
                correct_answers = cursor.fetchone()['count']
                
                accuracy_rate = round((correct_answers / total_answers * 100), 1) if total_answers > 0 else 0
                
                cursor.execute('''
                    SELECT q.question_text, ua.is_correct, ua.answered_at 
                    FROM user_answers ua 
                    JOIN questions q ON ua.question_id = q.id 
                    WHERE ua.user_id = %s
                    ORDER BY ua.answered_at DESC 
                    LIMIT 10
                ''', (user_id,))
                recent_history = cursor.fetchall()
                
                cursor.execute('''
                    SELECT q.genre, 
                           COUNT(*) as total,
                           SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) as correct
                    FROM user_answers ua 
                    JOIN questions q ON ua.question_id = q.id 
                    WHERE ua.user_id = %s
                    GROUP BY q.genre
                ''', (user_id,))
                genre_stats = cursor.fetchall()
            else:
                total_answers = 0
                correct_answers = 0
                accuracy_rate = 0
                recent_history = []
                genre_stats = []
            
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    """ユーザー登録"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # バリデーション
        if not username or not email or not password:
            flash('すべてのフィールドを入力してください', 'error')
            return render_template('register.html')
        
        if password != password_confirm:
            flash('パスワードが一致しません', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('パスワードは6文字以上で入力してください', 'error')
            return render_template('register.html')
        
        try:
            with get_db_connection(app.config['DATABASE_URL']) as conn:
                cursor = conn.cursor()
                
                # ユーザー名とメールの重複チェック
                cursor.execute('SELECT id FROM users WHERE username = %s OR email = %s', (username, email))
                if cursor.fetchone():
                    flash('ユーザー名またはメールアドレスがすでに使用されています', 'error')
                    return render_template('register.html')
                
                # パスワードハッシュ化
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # ユーザー作成
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, created_at)
                    VALUES (%s, %s, %s, %s) RETURNING id
                ''', (username, email, password_hash, datetime.now()))
                
                user_id = cursor.fetchone()[0]
                conn.commit()
                
                # 自動ログイン
                user = User(user_id, username, email)
                login_user(user)
                
                flash('アカウントが作成されました', 'success')
                return redirect(url_for('index'))
                
        except Exception as e:
            app.logger.error(f"Registration error: {e}")
            flash('登録処理中にエラーが発生しました', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ユーザーログイン"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('ユーザー名とパスワードを入力してください', 'error')
            return render_template('login.html')
        
        try:
            with get_db_connection(app.config['DATABASE_URL']) as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('SELECT id, username, email, password_hash FROM users WHERE username = %s OR email = %s', (username, username))
                user_data = cursor.fetchone()
                
                if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
                    user = User(user_data['id'], user_data['username'], user_data['email'])
                    login_user(user, remember=True)
                    
                    next_page = request.args.get('next')
                    if next_page:
                        return redirect(next_page)
                    
                    flash(f'ようこそ、{user_data["username"]}さん', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('ユーザー名またはパスワードが正しくありません', 'error')
                    
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            flash('ログイン処理中にエラーが発生しました', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def user_logout():
    """ユーザーログアウト"""
    logout_user()
    flash('ログアウトしました', 'info')
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """管理者ログイン"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == app.config['ADMIN_PASSWORD']:
            session['admin_authenticated'] = True
            flash('管理者認証に成功しました', 'success')
            return redirect(url_for('admin'))
        else:
            flash('パスワードが正しくありません', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """管理者ログアウト"""
    session.pop('admin_authenticated', None)
    flash('管理者ログアウトしました', 'info')
    return redirect(url_for('index'))

@app.route('/questions/<int:question_id>')
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
        question_manager.save_answer_history(question_id, user_answer, result['is_correct'], current_user.id)
        
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
def genre_practice():
    """ジャンル別演習メニュー"""
    try:
        genres = question_manager.get_available_genres()
        genre_counts = question_manager.get_question_count_by_genre()
        
        user_id = current_user.id if current_user.is_authenticated else None
        
        with get_db_connection(app.config['DATABASE_URL']) as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            if user_id:
                cursor.execute('''
                    SELECT q.genre, 
                           COUNT(*) as total,
                           SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) as correct
                    FROM user_answers ua 
                    JOIN questions q ON ua.question_id = q.id 
                    WHERE ua.user_id = %s
                    GROUP BY q.genre
                ''', (user_id,))
                genre_stats = cursor.fetchall()
            else:
                genre_stats = []
        
        stats_dict = {stat['genre']: {'total': stat['total'], 'correct': stat['correct']} for stat in genre_stats}
        
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
                return render_template('error.html', message='問題が登録されていません。'), 404
        
        return render_template('mock_exam_select.html', exam_files=json_files)
    except Exception as e:
        app.logger.error(f"Mock exam error: {e}")
        return render_template('error.html', message='模擬試験の準備中にエラーが発生しました'), 500

@app.route('/history')
@login_required
def history():
    """学習履歴の表示"""
    try:
        user_id = current_user.id
        
        with get_db_connection(app.config['DATABASE_URL']) as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute('''
                SELECT q.question_text, q.genre, ua.user_answer, ua.is_correct, ua.answered_at,
                       q.correct_answer, q.explanation
                FROM user_answers ua 
                JOIN questions q ON ua.question_id = q.id 
                WHERE ua.user_id = %s
                ORDER BY ua.answered_at DESC 
                LIMIT 50
            ''', (user_id,))
            detailed_history = cursor.fetchall()
            
            cursor.execute('''
                SELECT DATE(answered_at) as date, 
                       COUNT(*) as total,
                       SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END) as correct
                FROM user_answers 
                WHERE user_id = %s
                GROUP BY DATE(answered_at) 
                ORDER BY date DESC 
                LIMIT 30
            ''', (user_id,))
            daily_stats = cursor.fetchall()
            
            history_data = {
                'detailed_history': [dict(row) for row in detailed_history],
                'daily_stats': [dict(row) for row in daily_stats]
            }
        
        return render_template('history.html', history=history_data)
    except Exception as e:
        app.logger.error(f"History error: {e}")
        return render_template('error.html', message='学習履歴の表示中にエラーが発生しました'), 500

@app.route('/admin')
@admin_required
def admin():
    """管理画面"""
    try:
        with get_db_connection(app.config['DATABASE_URL']) as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute('SELECT COUNT(*) as count FROM questions')
            question_count = cursor.fetchone()['count']
            
            cursor.execute('SELECT DISTINCT genre FROM questions')
            genres = [row['genre'] for row in cursor.fetchall()]
            
            cursor.execute('SELECT COUNT(*) as count FROM users')
            user_count = cursor.fetchone()['count']
            
            json_files = []
            if os.path.exists(app.config['JSON_FOLDER']):
                for filename in os.listdir(app.config['JSON_FOLDER']):
                    if filename.endswith('.json'):
                        filepath = os.path.join(app.config['JSON_FOLDER'], filename)
                        if os.path.exists(filepath):
                            file_size = os.path.getsize(filepath)
                            file_info = parse_filename_info(filename)
                            
                            json_files.append({
                                'filename': filename,
                                'size': file_size,
                                'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M'),
                                'info': file_info
                            })
            
            json_files.sort(key=lambda x: (x['info']['year'], x['info']['season']) if x['info'] else (0, ''), reverse=True)
            
            admin_data = {
                'question_count': question_count,
                'user_count': user_count,
                'genres': genres,
                'json_files': json_files
            }
        
        return render_template('admin.html', data=admin_data)
    except Exception as e:
        app.logger.error(f"Admin error: {e}")
        return render_template('error.html', message='管理画面の表示中にエラーが発生しました'), 500

@app.route('/admin/upload_json', methods=['POST'])
@admin_required
def upload_json():
    """JSON問題ファイルのアップロードと処理"""
    try:
        if 'json_file' not in request.files:
            return jsonify({'success': False, 'error': 'JSONファイルが選択されていません'}), 400
        
        file = request.files['json_file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'ファイルが選択されていません'}), 400
        
        if not file.filename.lower().endswith('.json'):
            return jsonify({'success': False, 'error': 'JSONファイルを選択してください'}), 400
        
        try:
            content = file.read().decode('utf-8')
            questions = json.loads(content)
        except UnicodeDecodeError:
            return jsonify({'success': False, 'error': 'ファイルの文字エンコーディングが正しくありません。'}), 400
        except json.JSONDecodeError as e:
            return jsonify({'success': False, 'error': f'JSONファイルの形式が正しくありません: {str(e)}'}), 400
        
        if not isinstance(questions, list):
            return jsonify({'success': False, 'error': 'JSONファイルは問題の配列である必要があります'}), 400
        
        if len(questions) == 0:
            return jsonify({'success': False, 'error': 'JSONファイルに問題が含まれていません'}), 400
        
        # バリデーション
        for i, question in enumerate(questions):
            required_fields = ['question_text', 'choices', 'correct_answer']
            for field in required_fields:
                if field not in question:
                    return jsonify({'success': False, 'error': f'問題{i+1}: 必須フィールド "{field}" がありません'}), 400
            
            if 'question_id' not in question:
                question['question_id'] = f"問{i+1}"
            if 'genre' not in question:
                question['genre'] = 'その他'
            if 'explanation' not in question:
                question['explanation'] = ''
        
        file_info = parse_filename_info(file.filename)
        
        # JSONファイル保存
        json_filepath = os.path.join(app.config['JSON_FOLDER'], file.filename)
        with open(json_filepath, 'w', encoding='utf-8') as json_file:
            json.dump(questions, json_file, ensure_ascii=False, indent=2)
        
        # データベースに保存
        saved_count = question_manager.save_questions(questions)
        
        message = f'{len(questions)}問の問題をJSONファイルとデータベースに正常に保存しました'
        if file_info:
            message += f' ({file_info["display_name"]})'
        
        return jsonify({
            'success': True,
            'message': message,
            'count': len(questions),
            'saved_to_db': saved_count,
            'json_file': file.filename,
            'file_info': file_info
        })
        
    except Exception as e:
        app.logger.error(f"Upload JSON error: {e}")
        return jsonify({'success': False, 'error': f'JSON処理中にエラーが発生しました: {str(e)}'}), 500

@app.route('/admin/reset_database', methods=['POST'])
@admin_required
def reset_database():
    """データベースの初期化"""
    try:
        with get_db_connection(app.config['DATABASE_URL']) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_answers')
            cursor.execute('DELETE FROM questions')
            conn.commit()
        
        return jsonify({'message': 'データベースを初期化しました'})
        
    except Exception as e:
        app.logger.error(f"Reset database error: {e}")
        return jsonify({'error': f'データベース初期化中にエラーが発生しました: {str(e)}'}), 500

@app.route('/api/questions/random')
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
