# PostgreSQL環境で動作するためのアプリケーション設定
import os
import psycopg2
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import json
import sqlite3
import logging
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fe-exam-app-secret-key-change-in-production')

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # PostgreSQL設定（Render用）
    app.config['DATABASE_TYPE'] = 'postgresql'
    app.config['DATABASE_URL'] = DATABASE_URL
    print("Using PostgreSQL database")
else:
    # SQLite設定（開発用）
    app.config['DATABASE_TYPE'] = 'sqlite'
    app.config['DATABASE'] = 'fe_exam.db'
    print("Using SQLite database")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """データベース操作を管理するクラス"""
    
    def __init__(self):
        self.db_type = app.config['DATABASE_TYPE']
        
    def get_connection(self):
        """データベース接続を取得"""
        if self.db_type == 'postgresql':
            conn = psycopg2.connect(app.config['DATABASE_URL'])
            conn.autocommit = False
            return conn
        else:
            conn = sqlite3.connect(app.config['DATABASE'])
            conn.row_factory = sqlite3.Row
            return conn
    
    def execute_query(self, query, params=None):
        """クエリを実行して結果を返す"""
        conn = self.get_connection()
        try:
            if self.db_type == 'postgresql':
                cur = conn.cursor()
                cur.execute(query, params or ())
                if query.strip().upper().startswith(('SELECT', 'WITH')):
                    result = cur.fetchall()
                    # PostgreSQLの結果をdictに変換
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
        """データベースを初期化"""
        if self.db_type == 'postgresql':
            self._init_postgresql()
        else:
            self._init_sqlite()
    
    def _init_postgresql(self):
        """PostgreSQL用のテーブル作成"""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                question_id VARCHAR(50) UNIQUE NOT NULL,
                question_text TEXT NOT NULL,
                choices JSON NOT NULL,
                correct_answer VARCHAR(10) NOT NULL,
                explanation TEXT,
                genre VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_answers (
                id SERIAL PRIMARY KEY,
                question_id INTEGER REFERENCES questions(id),
                user_answer VARCHAR(10) NOT NULL,
                is_correct BOOLEAN NOT NULL,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_questions_genre ON questions(genre)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_user_answers_question_id ON user_answers(question_id)
            """,
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for query in queries:
            try:
                self.execute_query(query)
                logger.info("PostgreSQL table created/updated successfully")
            except Exception as e:
                logger.error(f"Error creating PostgreSQL table: {e}")
    
    def _init_sqlite(self):
        """SQLite用のテーブル作成"""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id TEXT UNIQUE NOT NULL,
                question_text TEXT NOT NULL,
                choices TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                explanation TEXT,
                genre TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER,
                user_answer TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                answered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_id) REFERENCES questions (id)
            )
            """
        ]
        
        for query in queries:
            try:
                self.execute_query(query)
                logger.info("SQLite table created/updated successfully")
            except Exception as e:
                logger.error(f"Error creating SQLite table: {e}")

# データベースマネージャーのインスタンス化
db_manager = DatabaseManager()

class QuestionManager:
    """問題管理クラス"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def save_questions(self, questions, source_file=''):
        """問題をデータベースに保存"""
        if not isinstance(questions, list):
            raise ValueError("Questions must be a list")
        
        saved_count = 0
        errors = []
        
        for i, question in enumerate(questions):
            try:
                # 必須フィールドの検証
                required_fields = ['question_text', 'choices', 'correct_answer']
                missing_fields = [field for field in required_fields if field not in question]
                if missing_fields:
                    errors.append(f"Question {i+1}: Missing fields {missing_fields}")
                    continue
                
                # question_idの自動生成
                question_id = question.get('question_id', f"Q{i+1:03d}_{source_file}")
                
                # choicesの処理
                if self.db.db_type == 'postgresql':
                    choices_data = json.dumps(question['choices'], ensure_ascii=False)
                else:
                    choices_data = json.dumps(question['choices'], ensure_ascii=False)
                
                # 重複チェック
                existing = self.db.execute_query(
                    'SELECT id FROM questions WHERE question_id = %s' if self.db.db_type == 'postgresql' else 'SELECT id FROM questions WHERE question_id = ?',
                    (question_id,)
                )
                
                if existing:
                    # 更新
                    if self.db.db_type == 'postgresql':
                        self.db.execute_query("""
                            UPDATE questions 
                            SET question_text = %s, choices = %s, correct_answer = %s, 
                                explanation = %s, genre = %s
                            WHERE question_id = %s
                        """, (
                            question['question_text'],
                            choices_data,
                            question['correct_answer'],
                            question.get('explanation', ''),
                            question.get('genre', 'その他'),
                            question_id
                        ))
                    else:
                        self.db.execute_query("""
                            UPDATE questions 
                            SET question_text = ?, choices = ?, correct_answer = ?, 
                                explanation = ?, genre = ?
                            WHERE question_id = ?
                        """, (
                            question['question_text'],
                            choices_data,
                            question['correct_answer'],
                            question.get('explanation', ''),
                            question.get('genre', 'その他'),
                            question_id
                        ))
                else:
                    # 新規追加
                    if self.db.db_type == 'postgresql':
                        self.db.execute_query("""
                            INSERT INTO questions 
                            (question_id, question_text, choices, correct_answer, explanation, genre) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            question_id,
                            question['question_text'],
                            choices_data,
                            question['correct_answer'],
                            question.get('explanation', ''),
                            question.get('genre', 'その他')
                        ))
                    else:
                        self.db.execute_query("""
                            INSERT INTO questions 
                            (question_id, question_text, choices, correct_answer, explanation, genre) 
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            question_id,
                            question['question_text'],
                            choices_data,
                            question['correct_answer'],
                            question.get('explanation', ''),
                            question.get('genre', 'その他')
                        ))
                
                saved_count += 1
                
            except Exception as e:
                errors.append(f"Question {i+1}: {str(e)}")
                logger.error(f"Error saving question {i+1}: {e}")
        
        return {
            'saved_count': saved_count,
            'total_count': len(questions),
            'errors': errors
        }
    
    def load_json_files(self):
        """JSONファイルを自動読み込み"""
        json_folder = 'json_questions'
        if not os.path.exists(json_folder):
            logger.warning(f"JSON folder not found: {json_folder}")
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
                    
                    if result['errors']:
                        errors.extend([f"{filename}: {error}" for error in result['errors']])
                    
                    logger.info(f"Loaded {result['saved_count']} questions from {filename}")
                    
                except Exception as e:
                    errors.append(f"{filename}: {str(e)}")
                    logger.error(f"Error loading {filename}: {e}")
        
        return {
            'total_files': total_files,
            'total_questions': total_questions,
            'errors': errors
        }

# 問題マネージャーのインスタンス化
question_manager = QuestionManager(db_manager)

# アプリケーション初期化
@app.before_first_request
def initialize_app():
    """アプリケーション初期化"""
    try:
        # データベース初期化
        db_manager.init_database()
        logger.info("Database initialized successfully")
        
        # JSONファイル自動読み込み
        result = question_manager.load_json_files()
        logger.info(f"Auto-loaded {result['total_questions']} questions from {result['total_files']} files")
        
        if result['errors']:
            for error in result['errors']:
                logger.warning(f"JSON loading warning: {error}")
                
    except Exception as e:
        logger.error(f"Application initialization error: {e}")

# 以下、ルート定義は既存のapp.pyと同じ...
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('このページにアクセスするにはログインが必要です。', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """ホームページ"""
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """ダッシュボード"""
    user_id = session['user_id']
    
    # 統計情報を取得
    total_questions_query = "SELECT COUNT(*) as count FROM questions"
    total_questions = db_manager.execute_query(total_questions_query)[0]['count']
    
    user_answers_query = "SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s" if db_manager.db_type == 'postgresql' else "SELECT COUNT(*) as count FROM user_answers WHERE user_id = ?"
    total_answers = db_manager.execute_query(user_answers_query, (user_id,))[0]['count']
    
    correct_answers_query = "SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s AND is_correct = TRUE" if db_manager.db_type == 'postgresql' else "SELECT COUNT(*) as count FROM user_answers WHERE user_id = ? AND is_correct = 1"
    correct_answers = db_manager.execute_query(correct_answers_query, (user_id,))[0]['count']
    
    accuracy_rate = 0
    if total_answers > 0:
        accuracy_rate = round((correct_answers / total_answers) * 100, 1)
        
    stats = {
        'total_questions': total_questions,
        'total_answers': total_answers,
        'correct_answers': correct_answers,
        'accuracy_rate': accuracy_rate
    }
    
    return render_template('dashboard.html', stats=stats)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """ユーザー登録"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('ユーザー名とパスワードを入力してください。', 'error')
            return redirect(url_for('register'))

        # ユーザー名の重複チェック
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
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'登録中にエラーが発生しました: {e}', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ログイン"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = db_manager.execute_query(
            'SELECT * FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT * FROM users WHERE username = ?',
            (username,)
        )
        
        if user and check_password_hash(user[0]['password_hash'], password):
            session.clear()
            session['user_id'] = user[0]['id']
            session['username'] = user[0]['username']
            session['is_admin'] = user[0]['is_admin']
            flash('ログインしました。', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('ユーザー名またはパスワードが正しくありません。', 'error')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    """ログアウト"""
    session.clear()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('index'))

# --- 機能ルート ---

@app.route('/random')
@login_required
def random_question():
    """ランダム問題ページ"""
    # データベースからランダムに1問取得
    query = "SELECT id FROM questions ORDER BY RANDOM() LIMIT 1" if db_manager.db_type == 'sqlite' else "SELECT id FROM questions ORDER BY RANDOM() LIMIT 1"
    result = db_manager.execute_query(query)
    
    if not result:
        flash('問題が見つかりません。データベースに問題が登録されているか確認してください。', 'warning')
        return redirect(url_for('dashboard'))
        
    question_id = result[0]['id']
    return redirect(url_for('show_question', question_id=question_id))

@app.route('/question/<int:question_id>', methods=['GET', 'POST'])
@login_required
def show_question(question_id):
    """個別問題の表示と回答"""
    query = "SELECT * FROM questions WHERE id = %s" if db_manager.db_type == 'postgresql' else "SELECT * FROM questions WHERE id = ?"
    question = db_manager.execute_query(query, (question_id,))
    
    if not question:
        flash('指定された問題が見つかりません。', 'error')
        return redirect(url_for('dashboard'))
    
    # DBから取得したquestionはリスト内の辞書なので、最初の要素を取り出す
    question_data = question[0]
    
    # choicesがJSON文字列の場合、Pythonオブジェクトに変換
    if isinstance(question_data['choices'], str):
        choices = json.loads(question_data['choices'])
    else:
        choices = question_data['choices']

    return render_template('question.html', question=question_data, choices=choices)

@app.route('/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    """回答を提出し、採点する"""
    try:
        question_id = request.form.get('question_id', type=int)
        user_answer = request.form.get('answer')
        user_id = session['user_id']

        if not question_id or not user_answer:
            flash('無効な回答です。', 'error')
            return redirect(url_for('dashboard'))

        # 正解を取得
        query = "SELECT correct_answer, explanation FROM questions WHERE id = %s" if db_manager.db_type == 'postgresql' else "SELECT correct_answer, explanation FROM questions WHERE id = ?"
        result = db_manager.execute_query(query, (question_id,))
        if not result:
            flash('問題が見つかりません。', 'error')
            return redirect(url_for('dashboard'))

        correct_answer = result[0]['correct_answer']
        explanation = result[0]['explanation']
        is_correct = (user_answer == correct_answer)

        # 回答履歴を保存
        insert_query = """
            INSERT INTO user_answers (user_id, question_id, user_answer, is_correct)
            VALUES (%s, %s, %s, %s)
        """ if db_manager.db_type == 'postgresql' else """
            INSERT INTO user_answers (user_id, question_id, user_answer, is_correct)
            VALUES (?, ?, ?, ?)
        """
        db_manager.execute_query(insert_query, (user_id, question_id, user_answer, is_correct))

        flash(f'正解は「{correct_answer}」です。' + ('正解！' if is_correct else '不正解'), 'info')
        return render_template('result.html', is_correct=is_correct, explanation=explanation, question_id=question_id)

    except Exception as e:
        logger.error(f"Answer submission error: {e}")
        flash('回答の処理中にエラーが発生しました。', 'error')
        return redirect(url_for('dashboard'))

@app.route('/history')
@login_required
def history():
    """学習履歴ページ"""
    user_id = session['user_id']
    query = """ 
        SELECT q.question_text, ua.user_answer, ua.is_correct, ua.answered_at
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.id
        WHERE ua.user_id = %s
        ORDER BY ua.answered_at DESC
        LIMIT 50
    """ if db_manager.db_type == 'postgresql' else """
        SELECT q.question_text, ua.user_answer, ua.is_correct, ua.answered_at
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.id
        WHERE ua.user_id = ?
        ORDER BY ua.answered_at DESC
        LIMIT 50
    """
    answers = db_manager.execute_query(query, (user_id,))
    return render_template('history.html', answers=answers)

@app.route('/genre_practice')
@login_required
def genre_practice():
    """ジャンル選択ページ"""
    query = "SELECT DISTINCT genre FROM questions ORDER BY genre"
    genres = [row['genre'] for row in db_manager.execute_query(query)]
    return render_template('genre_practice.html', genres=genres)

@app.route('/genre/<path:genre_name>')
@login_required
def genre_questions(genre_name):
    """ジャンル別の問題一覧ページ"""
    query = "SELECT id, question_text FROM questions WHERE genre = %s ORDER BY id" if db_manager.db_type == 'postgresql' else "SELECT id, question_text FROM questions WHERE genre = ? ORDER BY id"
    questions = db_manager.execute_query(query, (genre_name,))
    return render_template('problem_list.html', questions=questions, title=f'{genre_name}演習')

    return render_template('mock_exam_select.html', exam_files=exam_files)

@app.route('/mock_exam/<path:filename>')
@login_required
def mock_exam_start(filename):
    """指定年度の模擬試験開始"""
    try:
        json_folder = 'json_questions'
        json_filepath = os.path.join(json_folder, filename)
        
        if not os.path.exists(json_filepath):
            flash('試験ファイルが見つかりません', 'error')
            return redirect(url_for('mock_exam'))
        
        with open(json_filepath, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        # セッションに試験情報を保存
        session['current_exam'] = {
            'filename': filename,
            'questions': questions,
            'start_time': datetime.now().isoformat()
        }
        
        return render_template('mock_exam_practice.html', 
                             questions=questions, 
                             exam_filename=filename)
        
    except Exception as e:
        logger.error(f"Mock exam start error: {e}")
        flash(f'試験ファイルの読み込みに失敗しました: {str(e)}', 'error')
        return redirect(url_for('mock_exam'))

@app.route('/mock_exam/submit', methods=['POST'])
@login_required
def submit_mock_exam():
    """模擬試験の採点"""
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
            question_id_str = f"q{i}" # フロントエンドで question_id の代わりにインデックスが使われていると仮定
            user_answer = answers.get(question_id_str, '')
            is_correct = user_answer == question_data['correct_answer']
            
            if is_correct:
                correct_count += 1
            
            # DBから永続的なquestion IDを取得、なければスキップ
            db_question = db_manager.execute_query("SELECT id FROM questions WHERE question_text = %s", (question_data['question_text'],))
            if db_question:
                persistent_question_id = db_question[0]['id']
                # 回答履歴を保存
                db_manager.execute_query(
                    "INSERT INTO user_answers (user_id, question_id, user_answer, is_correct) VALUES (%s, %s, %s, %s)",
                    (user_id, persistent_question_id, user_answer, is_correct)
                )

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


# --- 管理者機能ルート ---

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('管理者権限が必要です。', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@admin_required
def admin_dashboard():
    """管理者ダッシュボード"""
    # 問題数のカウント
    total_questions = db_manager.execute_query("SELECT COUNT(*) as count FROM questions")[0]['count']
    
    # JSONファイルの情報を取得
    json_folder = 'json_questions'
    json_files_info = []
    if os.path.exists(json_folder):
        for filename in os.listdir(json_folder):
            if filename.endswith('.json'):
                filepath = os.path.join(json_folder, filename)
                try:
                    mtime = os.path.getmtime(filepath)
                    last_modified = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                    json_files_info.append({
                        'name': filename,
                        'last_modified': last_modified
                    })
                except OSError:
                    # ファイルが存在しない場合などのエラー処理
                    continue
    
    return render_template('admin.html', 
                           total_questions=total_questions, 
                           json_files=json_files_info)

@app.route('/admin/delete_json/<filename>', methods=['POST'])
@admin_required
def delete_json_file(filename):
    """JSONファイルを削除する"""
    try:
        json_folder = 'json_questions'
        filepath = os.path.join(json_folder, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            flash(f'{filename} を削除しました。', 'success')
        else:
            flash(f'{filename} が見つかりません。', 'error')
    except Exception as e:
        logger.error(f"Error deleting JSON file {filename}: {e}")
        flash(f'ファイルの削除中にエラーが発生しました: {e}', 'error')
    return redirect(url_for('admin_dashboard'))

# mock_exam_start と submit_mock_exam は missing_routes.py から移植するが、
# session と db_manager を使うように修正が必要。
# 今回は一旦基本的な機能のみ実装し、後ほど対応する。

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
