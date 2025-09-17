"""
基本情報技術者試験 学習アプリ - メインアプリケーション
Flask + PostgreSQL/SQLite + ユーザー認証を使用した学習プラットフォーム
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import os
import re
import json
import random
from datetime import datetime

# 分割されたモジュールのインポート
from database import DatabaseManager
from auth import login_required, admin_required, init_auth_routes
from question_manager import QuestionManager
from utils import parse_filename_info, is_postgresql, get_db_connection

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# データベース設定
DATABASE_URL = os.environ.get('DATABASE_URL')
DATABASE_TYPE = 'postgresql' if DATABASE_URL else 'sqlite'

app.config.update({
    'DATABASE_URL': DATABASE_URL,
    'DATABASE': 'fe_exam.db',
    'DATABASE_TYPE': DATABASE_TYPE,
    'UPLOAD_FOLDER': 'uploads',
    'JSON_FOLDER': 'json_questions',
    'ADMIN_PASSWORD': os.environ.get('ADMIN_PASSWORD', 'fe2025admin')
})

# フォルダ作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['JSON_FOLDER'], exist_ok=True)

# データベースマネージャーの初期化
db_manager = DatabaseManager(app.config)
db_manager.init_database()

# QuestionManagerの初期化
question_manager = QuestionManager(db_manager)

# 認証システムの初期化
init_auth_routes(app, db_manager)

# JSONフォルダの問題を自動読み込み
def load_json_questions_on_startup():
    """起動時にJSONフォルダの問題を自動読み込み"""
    try:
        if os.path.exists(app.config['JSON_FOLDER']):
            # 既存の問題数をチェック
            existing_count = db_manager.execute_query('SELECT COUNT(*) as count FROM questions')
            existing_total = existing_count[0]['count'] if existing_count else 0
            
            if existing_total == 0:
                print("📚 JSON問題ファイルを読み込み中...")
                
                loaded_files = []
                total_questions = 0
                
                for filename in os.listdir(app.config['JSON_FOLDER']):
                    if filename.endswith('.json'):
                        json_filepath = os.path.join(app.config['JSON_FOLDER'], filename)
                        try:
                            with open(json_filepath, 'r', encoding='utf-8') as json_file:
                                questions = json.load(json_file)
                            
                            print(f"   📄 {filename}: {len(questions)}問を読み込み中...")
                            result = question_manager.save_questions(questions, filename)
                            if result['saved_count'] > 0:
                                loaded_files.append({
                                    'filename': filename,
                                    'file_questions': len(questions),
                                    'saved_count': result['saved_count']
                                })
                                total_questions += result['saved_count']
                        except Exception as e:
                            print(f"❌ ファイル {filename} の読み込みでエラー: {e}")
                            continue
                
                if loaded_files:
                    print(f"\n✅ JSONフォルダから {len(loaded_files)}個のファイルを自動読み込み完了")
                    for file_info in loaded_files:
                        print(f"   📄 {file_info['filename']}: {file_info['file_questions']}問 → DB保存: {file_info['saved_count']}問")
                    print(f"🎯 合計: {total_questions}問をデータベースに追加しました\n")
                else:
                    print("⚠️  JSONフォルダにファイルがないか、読み込みに失敗しました。")
            else:
                print(f"📊 データベースに既に {existing_total}問の問題が登録されています。")
    except Exception as e:
        print(f"❌ JSON自動読み込み中にエラー: {e}")

# アプリ起動時の処理
load_json_questions_on_startup()

# ========== ルート定義 ==========

@app.route('/')
def index():
    """ルートアクセス - ログイン済みならダッシュボード、未ログインならログインページ"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """メインページ - ダッシュボード表示（ログイン後）"""
    try:
        user_id = session['user_id']
        
        # 基本統計を取得
        total_questions = db_manager.execute_query('SELECT COUNT(*) as count FROM questions')
        total_q_count = total_questions[0]['count'] if total_questions else 0
        
        user_answers = db_manager.execute_query(
            'SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s' if db_manager.db_type == 'postgresql' else 'SELECT COUNT(*) as count FROM user_answers WHERE user_id = ?',
            (user_id,)
        )
        answered_count = user_answers[0]['count'] if user_answers else 0
        
        # SQLiteとPostgreSQLで条件文を分ける
        if db_manager.db_type == 'postgresql':
            correct_answers = db_manager.execute_query(
                'SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s AND is_correct = %s',
                (user_id, True)
            )
        else:
            correct_answers = db_manager.execute_query(
                'SELECT COUNT(*) as count FROM user_answers WHERE user_id = ? AND is_correct = 1',
                (user_id,)
            )
        correct_count = correct_answers[0]['count'] if correct_answers else 0
        
        accuracy_rate = round((correct_count / answered_count * 100), 1) if answered_count > 0 else 0
        
        # 最近の履歴
        recent_history = db_manager.execute_query('''
            SELECT q.question_text, ua.is_correct, ua.answered_at 
            FROM user_answers ua 
            JOIN questions q ON ua.question_id = q.id 
            WHERE ua.user_id = %s
            ORDER BY ua.answered_at DESC 
            LIMIT 10
        ''' if db_manager.db_type == 'postgresql' else '''
            SELECT q.question_text, ua.is_correct, ua.answered_at 
            FROM user_answers ua 
            JOIN questions q ON ua.question_id = q.id 
            WHERE ua.user_id = ?
            ORDER BY ua.answered_at DESC 
            LIMIT 10
        ''', (user_id,))
        
        # ジャンル別統計
        if db_manager.db_type == 'postgresql':
            genre_stats = db_manager.execute_query('''
                SELECT q.genre, 
                       COUNT(*) as total,
                       SUM(CASE WHEN ua.is_correct = %s THEN 1 ELSE 0 END) as correct
                FROM user_answers ua 
                JOIN questions q ON ua.question_id = q.id 
                WHERE ua.user_id = %s AND q.genre IS NOT NULL
                GROUP BY q.genre
            ''', (True, user_id))
        else:
            genre_stats = db_manager.execute_query('''
                SELECT q.genre, 
                       COUNT(*) as total,
                       SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct
                FROM user_answers ua 
                JOIN questions q ON ua.question_id = q.id 
                WHERE ua.user_id = ? AND q.genre IS NOT NULL
                GROUP BY q.genre
            ''', (user_id,))
        
        stats = {
            'total_questions': total_q_count,
            'total_answers': answered_count,
            'correct_answers': correct_count,
            'accuracy_rate': accuracy_rate,
            'recent_history': recent_history or [],
            'genre_stats': genre_stats or []
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
            flash('問題が見つかりません', 'error')
            return redirect(url_for('dashboard'))
        
        return render_template('question.html', question=question)
    except Exception as e:
        app.logger.error(f"Show question error: {e}")
        flash('問題の表示中にエラーが発生しました', 'error')
        return redirect(url_for('dashboard'))

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
        question_manager.save_answer_history(question_id, user_answer, result['is_correct'], session['user_id'])
        
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Submit answer error: {e}")
        return jsonify({'error': '解答処理中にエラーが発生しました'}), 500

@app.route('/random')
@login_required
def random_question():
    """ランダム問題表示"""
    try:
        question = question_manager.get_random_question()
        if not question:
            flash('問題が見つかりません。管理者に問い合わせてください。', 'error')
            return redirect(url_for('dashboard'))
        
        return render_template('question.html', question=question)
    except Exception as e:
        app.logger.error(f"Random question error: {e}")
        flash('ランダム問題の表示中にエラーが発生しました。', 'error')
        return redirect(url_for('dashboard'))

@app.route('/genre_practice')
@login_required
def genre_practice():
    """ジャンル別演習メニュー"""
    try:
        genres = question_manager.get_available_genres()
        genre_counts = question_manager.get_question_count_by_genre()
        
        user_id = session['user_id']
        if db_manager.db_type == 'postgresql':
            genre_stats = db_manager.execute_query('''
                SELECT q.genre, 
                       COUNT(*) as total,
                       SUM(CASE WHEN ua.is_correct = %s THEN 1 ELSE 0 END) as correct
                FROM user_answers ua 
                JOIN questions q ON ua.question_id = q.id 
                WHERE ua.user_id = %s AND q.genre IS NOT NULL
                GROUP BY q.genre
            ''', (True, user_id))
        else:
            genre_stats = db_manager.execute_query('''
                SELECT q.genre, 
                       COUNT(*) as total,
                       SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct
                FROM user_answers ua 
                JOIN questions q ON ua.question_id = q.id 
                WHERE ua.user_id = ? AND q.genre IS NOT NULL
                GROUP BY q.genre
            ''', (user_id,))
        
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
        flash('ジャンル別演習の準備中にエラーが発生しました', 'error')
        return redirect(url_for('dashboard'))

@app.route('/practice/<genre>')
@login_required
def practice_by_genre(genre):
    """ジャンル別練習問題表示"""
    try:
        question = question_manager.get_random_question_by_genre(genre)
        if not question:
            flash(f'ジャンル "{genre}" の問題が見つかりません', 'error')
            return redirect(url_for('genre_practice'))
        
        return render_template('question.html', question=question, genre=genre)
    except Exception as e:
        app.logger.error(f"Practice by genre error: {e}")
        flash('ジャンル別問題の表示中にエラーが発生しました', 'error')
        return redirect(url_for('genre_practice'))

@app.route('/mock_exam')
@login_required
def mock_exam():
    """模擬試験選択画面"""
    try:
        json_files = []
        if os.path.exists(app.config['JSON_FOLDER']):
            for filename in os.listdir(app.config['JSON_FOLDER']):
                if filename.endswith('.json'):
                    file_info = parse_filename_info(filename)
                    if file_info:
                        # 問題数を取得
                        json_filepath = os.path.join(app.config['JSON_FOLDER'], filename)
                        try:
                            with open(json_filepath, 'r', encoding='utf-8') as f:
                                questions = json.load(f)
                            file_info['question_count'] = len(questions)
                        except:
                            file_info['question_count'] = 0
                        
                        json_files.append({
                            'filename': filename,
                            'info': file_info
                        })
        
        json_files.sort(key=lambda x: (x['info']['year'], x['info']['season']), reverse=True)
        
        return render_template('mock_exam.html', exam_files=json_files)
    except Exception as e:
        app.logger.error(f"Mock exam error: {e}")
        return render_template('mock_exam.html', exam_files=[])

@app.route('/mock_exam/<filename>')
@login_required
def mock_exam_start(filename):
    """指定年度の模擬試験開始"""
    try:
        file_info = parse_filename_info(filename)
        if not file_info:
            flash('無効な試験ファイルです', 'error')
            return redirect(url_for('mock_exam'))
        
        json_filepath = os.path.join(app.config['JSON_FOLDER'], filename)
        if not os.path.exists(json_filepath):
            flash('試験ファイルが見つかりません', 'error')
            return redirect(url_for('mock_exam'))
        
        with open(json_filepath, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        # 20問に制限
        if len(questions) > 20:
            questions = random.sample(questions, 20)
        
        return render_template('mock_exam_practice.html', 
                             questions=questions, 
                             exam_info=file_info)
        
    except Exception as e:
        app.logger.error(f"Mock exam start error: {e}")
        flash(f'試験ファイルの読み込みに失敗しました: {str(e)}', 'error')
        return redirect(url_for('mock_exam'))

@app.route('/mock_exam/submit', methods=['POST'])
@login_required
def submit_mock_exam():
    """模擬試験の採点"""
    try:
        data = request.get_json()
        answers = data.get('answers', {})
        
        # 簡単な採点（実際には提出された問題に対する正解データが必要）
        total_count = len(answers)
        correct_count = 0
        
        # 仮の採点処理
        for answer in answers.values():
            # 実際の実装では問題データとの照合が必要
            if random.choice([True, False]):  # 仮の正解判定
                correct_count += 1
        
        score = round((correct_count / total_count) * 100, 1) if total_count > 0 else 0
        
        return jsonify({
            'score': score,
            'correct_count': correct_count,
            'total_count': total_count
        })
        
    except Exception as e:
        app.logger.error(f"Submit mock exam error: {e}")
        return jsonify({'error': '採点処理中にエラーが発生しました'}), 500

@app.route('/history')
@login_required
def history():
    """学習履歴の表示"""
    try:
        user_id = session['user_id']
        
        # 詳細履歴
        detailed_history = db_manager.execute_query('''
            SELECT q.question_text, q.genre, ua.user_answer, ua.is_correct, ua.answered_at,
                   q.correct_answer, q.explanation
            FROM user_answers ua 
            JOIN questions q ON ua.question_id = q.id 
            WHERE ua.user_id = %s
            ORDER BY ua.answered_at DESC 
            LIMIT 50
        ''' if db_manager.db_type == 'postgresql' else '''
            SELECT q.question_text, q.genre, ua.user_answer, ua.is_correct, ua.answered_at,
                   q.correct_answer, q.explanation
            FROM user_answers ua 
            JOIN questions q ON ua.question_id = q.id 
            WHERE ua.user_id = ?
            ORDER BY ua.answered_at DESC 
            LIMIT 50
        ''', (user_id,))
        
        # 日別統計
        if db_manager.db_type == 'postgresql':
            daily_stats = db_manager.execute_query('''
                SELECT DATE(answered_at) as date, 
                       COUNT(*) as total,
                       SUM(CASE WHEN is_correct = %s THEN 1 ELSE 0 END) as correct
                FROM user_answers 
                WHERE user_id = %s
                GROUP BY DATE(answered_at) 
                ORDER BY date DESC 
                LIMIT 30
            ''', (True, user_id))
        else:
            daily_stats = db_manager.execute_query('''
                SELECT DATE(answered_at) as date, 
                       COUNT(*) as total,
                       SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
                FROM user_answers 
                WHERE user_id = ?
                GROUP BY DATE(answered_at) 
                ORDER BY date DESC 
                LIMIT 30
            ''', (user_id,))
        
        history_data = {
            'detailed_history': detailed_history or [],
            'daily_stats': daily_stats or []
        }
        
        return render_template('history.html', history=history_data)
    except Exception as e:
        app.logger.error(f"History error: {e}")
        return render_template('history.html', history={'detailed_history': [], 'daily_stats': []})

@app.route('/admin')
@admin_required
def admin():
    """管理画面"""
    try:
        # 問題数とジャンル
        question_count = db_manager.execute_query('SELECT COUNT(*) as count FROM questions')
        total_questions = question_count[0]['count'] if question_count else 0
        
        genres = db_manager.execute_query('SELECT DISTINCT genre FROM questions WHERE genre IS NOT NULL')
        genre_list = [g['genre'] for g in genres] if genres else []
        
        # JSONファイル情報
        json_files = []
        if os.path.exists(app.config['JSON_FOLDER']):
            for filename in os.listdir(app.config['JSON_FOLDER']):
                if filename.endswith('.json'):
                    filepath = os.path.join(app.config['JSON_FOLDER'], filename)
                    if os.path.exists(filepath):
                        file_size = os.path.getsize(filepath)
                        file_info = parse_filename_info(filename)
                        
                        # JSONファイルから問題数を取得
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                questions = json.load(f)
                            file_question_count = len(questions)
                        except:
                            file_question_count = 0
                        
                        json_files.append({
                            'filename': filename,
                            'size': file_size,
                            'question_count': file_question_count,
                            'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M'),
                            'info': file_info
                        })
        
        json_files.sort(key=lambda x: (x['info']['year'], x['info']['season']) if x['info'] else (0, ''), reverse=True)
        
        admin_data = {
            'question_count': total_questions,
            'genres': genre_list,
            'json_files': json_files
        }
        
        return render_template('admin.html', data=admin_data)
    except Exception as e:
        app.logger.error(f"Admin error: {e}")
        return render_template('admin.html', data={'question_count': 0, 'genres': [], 'json_files': []})

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
        
        # JSONファイルを保存
        json_filepath = os.path.join(app.config['JSON_FOLDER'], file.filename)
        with open(json_filepath, 'w', encoding='utf-8') as json_file:
            json.dump(questions, json_file, ensure_ascii=False, indent=2)
        
        # データベースに保存
        result = question_manager.save_questions(questions, file.filename)
        
        file_info = parse_filename_info(file.filename)
        message = f'{len(questions)}問の問題をJSONファイルとデータベースに保存しました'
        if file_info:
            message += f' ({file_info["display_name"]})'
        
        return jsonify({
            'success': True,
            'message': message,
            'count': len(questions),
            'saved_to_db': result['saved_count'],
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
        db_manager.execute_query('DELETE FROM user_answers')
        db_manager.execute_query('DELETE FROM questions')
        
        return jsonify({'message': 'データベースを初期化しました'})
        
    except Exception as e:
        app.logger.error(f"Reset database error: {e}")
        return jsonify({'error': f'データベース初期化中にエラーが発生しました: {str(e)}'}), 500

@app.route('/admin/create_sample', methods=['POST'])
@admin_required
def create_sample_data():
    """サンプルデータの作成"""
    try:
        sample_questions = [
            {
                "question_id": "SAMPLE001",
                "question_text": "基本情報技術者試験について、正しい説明はどれか。",
                "choices": {
                    "ア": "年に1回実施される",
                    "イ": "年に2回実施される", 
                    "ウ": "年に3回実施される",
                    "エ": "年に4回実施される"
                },
                "correct_answer": "イ",
                "explanation": "基本情報技術者試験は春期（4月）と秋期（10月）の年2回実施されます。",
                "genre": "試験制度"
            },
            {
                "question_id": "SAMPLE002",
                "question_text": "2進数1011を10進数に変換すると、いくつになるか。",
                "choices": {
                    "ア": "9",
                    "イ": "10",
                    "ウ": "11", 
                    "エ": "12"
                },
                "correct_answer": "ウ",
                "explanation": "2進数1011は、1×2³ + 0×2² + 1×2¹ + 1×2⁰ = 8 + 0 + 2 + 1 = 11です。",
                "genre": "基礎理論"
            },
            {
                "question_id": "SAMPLE003",
                "question_text": "OSIモデルの第4層は何層か。",
                "choices": {
                    "ア": "ネットワーク層",
                    "イ": "データリンク層",
                    "ウ": "トランスポート層",
                    "エ": "セッション層"
                },
                "correct_answer": "ウ",
                "explanation": "OSIモデルの第4層はトランスポート層で、エンドツーエンドの通信制御を行います。",
                "genre": "ネットワーク"
            }
        ]
        
        result = question_manager.save_questions(sample_questions, 'sample_data')
        
        return jsonify({
            'success': True,
            'message': f'{result["saved_count"]}問のサンプル問題を作成しました',
            'count': result['saved_count']
        })
        
    except Exception as e:
        app.logger.error(f"Create sample error: {e}")
        return jsonify({'success': False, 'error': f'サンプルデータ作成中にエラーが発生しました: {str(e)}'}), 500

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
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
