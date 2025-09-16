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

# アプリ起動時にJSON問題を自動読み込み
load_json_questions_on_startup()

# ========== ルート定義 ==========

@app.route('/')
def index():
    """ログイン前のホーム画面"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """メインページ - ダッシュボード表示（ログイン後）"""
    try:
        with get_db_connection(app.config['DATABASE_URL'], app.config['DATABASE']) as conn:
            if is_postgresql(app.config['DATABASE_URL']):
                with conn.cursor() as cur:
                    cur.execute('SELECT COUNT(*) as count FROM questions')
                    total_questions = cur.fetchone()['count']
                    
                    cur.execute('SELECT COUNT(*) as count FROM user_answers')
                    total_answers = cur.fetchone()['count']
                    
                    cur.execute('SELECT COUNT(*) as count FROM user_answers WHERE is_correct = true')
                    correct_answers = cur.fetchone()['count']
                    
                    accuracy_rate = round((correct_answers / total_answers * 100), 1) if total_answers > 0 else 0
                    
                    cur.execute('''
                        SELECT q.question_text, ua.is_correct, ua.answered_at 
                        FROM user_answers ua 
                        JOIN questions q ON ua.question_id = q.id 
                        ORDER BY ua.answered_at DESC 
                        LIMIT 10
                    ''')
                    recent_history = cur.fetchall()
                    
                    cur.execute('''
                        SELECT q.genre, 
                               COUNT(*) as total,
                               SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) as correct
                        FROM user_answers ua 
                        JOIN questions q ON ua.question_id = q.id 
                        GROUP BY q.genre
                    ''')
                    genre_stats = cur.fetchall()
                    
                    stats = {
                        'total_questions': total_questions,
                        'total_answers': total_answers,
                        'correct_answers': correct_answers,
                        'accuracy_rate': accuracy_rate,
                        'recent_history': [dict(row) for row in recent_history],
                        'genre_stats': [dict(row) for row in genre_stats]
                    }
            else:
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
        
        with get_db_connection(app.config['DATABASE_URL'], app.config['DATABASE']) as conn:
            if is_postgresql(app.config['DATABASE_URL']):
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT q.genre, 
                               COUNT(*) as total,
                               SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) as correct
                        FROM user_answers ua 
                        JOIN questions q ON ua.question_id = q.id 
                        GROUP BY q.genre
                    ''')
                    genre_stats = cur.fetchall()
            else:
                genre_stats = conn.execute('''
                    SELECT q.genre, 
                           COUNT(*) as total,
                           SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct
                    FROM user_answers ua 
                    JOIN questions q ON ua.question_id = q.id 
                    GROUP BY q.genre
                ''').fetchall()
        
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
                return render_template('error.html', message='問題が登録されていません。管理者に問い合わせてください。'), 404
        
        return render_template('mock_exam_select.html', exam_files=json_files)
    except Exception as e:
        app.logger.error(f"Mock exam error: {e}")
        return render_template('error.html', message='模擬試験の準備中にエラーが発生しました'), 500

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
        
        if len(questions) > 20:
            questions = random.sample(questions, 20)
        
        session['exam_start_time'] = datetime.now().isoformat()
        session['exam_questions'] = [q.get('question_id', f"Q{i+1:03d}") for i, q in enumerate(questions)]
        session['exam_year_info'] = file_info
        session['exam_file_questions'] = questions
        
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
        
        if 'exam_questions' not in session:
            return jsonify({'error': '試験セッションが見つかりません'}), 400
        
        question_ids = session['exam_questions']
        results = []
        correct_count = 0
        
        if 'exam_file_questions' in session:
            file_questions = session['exam_file_questions']
            question_dict = {q.get('question_id', f"Q{i+1:03d}"): q for i, q in enumerate(file_questions)}
            
            for question_id in question_ids:
                question_data = question_dict.get(question_id)
                if question_data:
                    user_answer = answers.get(question_id, '')
                    is_correct = user_answer == question_data['correct_answer']
                    
                    results.append({
                        'question_id': question_id,
                        'question_text': question_data['question_text'],
                        'user_answer': user_answer,
                        'correct_answer': question_data['correct_answer'],
                        'is_correct': is_correct,
                        'explanation': question_data.get('explanation', '')
                    })
                    
                    if is_correct:
                        correct_count += 1
        else:
            for question_id in question_ids:
                if isinstance(question_id, int):
                    question = question_manager.get_question(question_id)
                    if question:
                        user_answer = answers.get(str(question_id), '')
                        is_correct = user_answer == question['correct_answer']
                        
                        question_manager.save_answer_history(question_id, user_answer, is_correct)
                        
                        results.append({
                            'question_id': question_id,
                            'question_text': question['question_text'],
                            'user_answer': user_answer,
                            'correct_answer': question['correct_answer'],
                            'is_correct': is_correct,
                            'explanation': question.get('explanation', '')
                        })
                        
                        if is_correct:
                            correct_count += 1
        
        score = round((correct_count / len(question_ids)) * 100, 1) if question_ids else 0
        
        session.pop('exam_start_time', None)
        session.pop('exam_questions', None)
        session.pop('exam_year_info', None)
        session.pop('exam_file_questions', None)
        
        return jsonify({
            'score': score,
            'correct_count': correct_count,
            'total_count': len(question_ids),
            'results': results
        })
        
    except Exception as e:
        app.logger.error(f"Submit mock exam error: {e}")
        return jsonify({'error': '採点処理中にエラーが発生しました'}), 500

@app.route('/history')
@login_required
def history():
    """学習履歴の表示"""
    try:
        with get_db_connection(app.config['DATABASE_URL'], app.config['DATABASE']) as conn:
            if is_postgresql(app.config['DATABASE_URL']):
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT q.question_text, q.genre, ua.user_answer, ua.is_correct, ua.answered_at,
                               q.correct_answer, q.explanation
                        FROM user_answers ua 
                        JOIN questions q ON ua.question_id = q.id 
                        ORDER BY ua.answered_at DESC 
                        LIMIT 50
                    ''')
                    detailed_history = cur.fetchall()
                    
                    cur.execute('''
                        SELECT DATE(answered_at) as date, 
                               COUNT(*) as total,
                               SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END) as correct
                        FROM user_answers 
                        GROUP BY DATE(answered_at) 
                        ORDER BY date DESC 
                        LIMIT 30
                    ''')
                    daily_stats = cur.fetchall()
                    
                    history_data = {
                        'detailed_history': [dict(row) for row in detailed_history],
                        'daily_stats': [dict(row) for row in daily_stats]
                    }
            else:
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

@app.route('/admin')
@admin_required
def admin():
    """管理画面"""
    try:
        with get_db_connection(app.config['DATABASE_URL'], app.config['DATABASE']) as conn:
            if is_postgresql(app.config['DATABASE_URL']):
                with conn.cursor() as cur:
                    cur.execute('SELECT COUNT(*) as count FROM questions')
                    question_count = cur.fetchone()['count']
                    cur.execute('SELECT DISTINCT genre FROM questions')
                    genres = [row['genre'] for row in cur.fetchall()]
            else:
                question_count = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
                genres = conn.execute('SELECT DISTINCT genre FROM questions').fetchall()
                genres = [row[0] for row in genres]
            
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
        
        json_filepath = os.path.join(app.config['JSON_FOLDER'], file.filename)
        with open(json_filepath, 'w', encoding='utf-8') as json_file:
            json.dump(questions, json_file, ensure_ascii=False, indent=2)
        
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
        with get_db_connection(app.config['DATABASE_URL'], app.config['DATABASE']) as conn:
            if is_postgresql(app.config['DATABASE_URL']):
                with conn.cursor() as cur:
                    cur.execute('DELETE FROM user_answers')
                    cur.execute('DELETE FROM questions')
                conn.commit()
            else:
                conn.execute('DELETE FROM user_answers')
                conn.execute('DELETE FROM questions')
                conn.commit()
        
        return jsonify({'message': 'データベースを初期化しました'})
        
    except Exception as e:
        app.logger.error(f"Reset database error: {e}")
        return jsonify({'error': f'データベース初期化中にエラーが発生しました: {str(e)}'}), 500

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

@app.route('/random')
@login_required
def random_question():
    """ランダム問題への直接アクセス"""
    try:
        question = question_manager.get_random_question()
        if not question:
            flash('問題が見つかりません。管理者に問い合わせてください。', 'error')
            return redirect(url_for('dashboard'))
        
        return redirect(url_for('show_question', question_id=question['id']))
    except Exception as e:
        app.logger.error(f"Random question error: {e}")
        flash('ランダム問題の表示中にエラーが発生しました。', 'error')
        return redirect(url_for('dashboard'))

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
