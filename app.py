"""
基本情報技術者試験 学習アプリ
Flask + SQLite + Tailwind CSS を使用した学習プラットフォーム
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
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
app.secret_key = 'your-secret-key-change-in-production'

# アプリケーション設定
app.config['DATABASE'] = 'fe_exam.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['JSON_FOLDER'] = 'json_questions'
app.config['ADMIN_PASSWORD'] = 'fe2025admin'  # 管理者パスワード（本番環境では環境変数で設定）

# アップロードフォルダとJSONフォルダを作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['JSON_FOLDER'], exist_ok=True)

# データベースの初期化
if not os.path.exists(app.config['DATABASE']):
    print("データベースを初期化しています...")
    init_db(app.config['DATABASE'])
    
    # サンプル問題を自動作成
    try:
        processor = PDFProcessor()
        sample_questions = processor.create_sample_questions()
        question_manager = QuestionManager(app.config['DATABASE'])
        saved_count = question_manager.save_questions(sample_questions)
        print(f"サンプル問題 {saved_count}問を作成しました。")
    except Exception as e:
        print(f"サンプル問題作成中にエラーが発生しました: {e}")

# QuestionManagerの初期化
question_manager = QuestionManager(app.config['DATABASE'])

def admin_required(f):
    """管理者認証デコレータ"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def parse_filename_info(filename):
    """ファイル名から年度と期の情報を抽出"""
    # 例: 2025r07_kamoku_a_spring.json → {'year': 2025, 'era': 'r07', 'season': 'spring'}
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
            'display_name': f'{year}年 {season_jp}'
        }
    return None

@app.route('/')
def index():
    """メインページ - ダッシュボード表示"""
    with get_db_connection(app.config['DATABASE']) as conn:
        # 学習統計の取得
        total_questions = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
        total_answers = conn.execute('SELECT COUNT(*) FROM user_answers').fetchone()[0]
        correct_answers = conn.execute('SELECT COUNT(*) FROM user_answers WHERE is_correct = 1').fetchone()[0]
        
        accuracy_rate = round((correct_answers / total_answers * 100), 1) if total_answers > 0 else 0
        
        # 最近の学習履歴
        recent_history = conn.execute('''
            SELECT q.question_text, ua.is_correct, ua.answered_at 
            FROM user_answers ua 
            JOIN questions q ON ua.question_id = q.id 
            ORDER BY ua.answered_at DESC 
            LIMIT 10
        ''').fetchall()
        
        # ジャンル別正答率
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
    flash('ログアウトしました', 'info')
    return redirect(url_for('index'))

@app.route('/questions/<int:question_id>')
def show_question(question_id):
    """個別問題の表示"""
    question = question_manager.get_question(question_id)
    if not question:
        return render_template('error.html', message='問題が見つかりません'), 404
    
    return render_template('question.html', question=question)

@app.route('/questions/<int:question_id>/answer', methods=['POST'])
def submit_answer(question_id):
    """解答の提出と判定"""
    data = request.get_json()
    user_answer = data.get('answer')
    
    if not user_answer:
        return jsonify({'error': '解答が選択されていません'}), 400
    
    result = question_manager.check_answer(question_id, user_answer)
    
    # 解答履歴を保存
    question_manager.save_answer_history(question_id, user_answer, result['is_correct'])
    
    return jsonify(result)

@app.route('/practice/<genre>')
def practice_by_genre(genre):
    """ジャンル別練習"""
    questions = question_manager.get_questions_by_genre(genre)
    
    if not questions:
        return render_template('error.html', message=f'ジャンル "{genre}" の問題が見つかりません'), 404
    
    # ランダムに並び替え
    random.shuffle(questions)
    
    return render_template('practice.html', questions=questions, genre=genre)

@app.route('/mock_exam')
def mock_exam():
    """模擬試験年度選択画面"""
    # 利用可能な年度別問題を取得
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
    
    # 年度順でソート
    json_files.sort(key=lambda x: (x['info']['year'], x['info']['season']), reverse=True)
    
    return render_template('mock_exam_select.html', exam_files=json_files)

@app.route('/mock_exam/<filename>')
def mock_exam_start(filename):
    """指定年度の模擬試験開始"""
    file_info = parse_filename_info(filename)
    if not file_info:
        flash('無効な試験ファイルです', 'error')
        return redirect(url_for('mock_exam'))
    
    # 該当ファイルから問題を読み込み
    json_filepath = os.path.join(app.config['JSON_FOLDER'], filename)
    if not os.path.exists(json_filepath):
        flash('試験ファイルが見つかりません', 'error')
        return redirect(url_for('mock_exam'))
    
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        # 最大20問を選択
        if len(questions) > 20:
            questions = random.sample(questions, 20)
        
        # セッションに試験情報を保存
        session['exam_start_time'] = datetime.now().isoformat()
        session['exam_questions'] = [q['question_id'] for q in questions]
        session['exam_year_info'] = file_info
        
        return render_template('mock_exam_practice.html', 
                             questions=questions, 
                             exam_info=file_info)
        
    except Exception as e:
        flash(f'試験ファイルの読み込みに失敗しました: {str(e)}', 'error')
        return redirect(url_for('mock_exam'))

@app.route('/mock_exam/submit', methods=['POST'])
def submit_mock_exam():
    """模擬試験の採点"""
    data = request.get_json()
    answers = data.get('answers', {})
    
    if 'exam_questions' not in session:
        return jsonify({'error': '試験セッションが見つかりません'}), 400
    
    question_ids = session['exam_questions']
    exam_info = session.get('exam_year_info', {})
    results = []
    correct_count = 0
    
    # JSONファイルから問題を再読み込み
    filename = None
    for file in os.listdir(app.config['JSON_FOLDER']):
        if parse_filename_info(file) and parse_filename_info(file)['year'] == exam_info.get('year'):
            filename = file
            break
    
    if filename:
        json_filepath = os.path.join(app.config['JSON_FOLDER'], filename)
        with open(json_filepath, 'r', encoding='utf-8') as f:
            file_questions = json.load(f)
        
        # 問題IDをキーとした辞書を作成
        question_dict = {q['question_id']: q for q in file_questions}
        
        for question_id in question_ids:
            user_answer = answers.get(question_id, '')
            question_data = question_dict.get(question_id)
            
            if question_data:
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
    
    score = round((correct_count / len(question_ids)) * 100, 1) if question_ids else 0
    
    # セッションクリア
    session.pop('exam_start_time', None)
    session.pop('exam_questions', None)
    session.pop('exam_year_info', None)
    
    return jsonify({
        'score': score,
        'correct_count': correct_count,
        'total_count': len(question_ids),
        'results': results,
        'exam_info': exam_info
    })

@app.route('/history')
def history():
    """学習履歴の表示"""
    with get_db_connection(app.config['DATABASE']) as conn:
        # 詳細な学習履歴
        detailed_history = conn.execute('''
            SELECT q.question_text, q.genre, ua.user_answer, ua.is_correct, ua.answered_at,
                   q.correct_answer, q.explanation
            FROM user_answers ua 
            JOIN questions q ON ua.question_id = q.id 
            ORDER BY ua.answered_at DESC 
            LIMIT 50
        ''').fetchall()
        
        # 日別統計
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

@app.route('/admin')
@admin_required
def admin():
    """管理画面"""
    with get_db_connection(app.config['DATABASE']) as conn:
        question_count = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
        genres = conn.execute('SELECT DISTINCT genre FROM questions').fetchall()
        
        # JSONファイル一覧を取得（年度別情報付き）
        json_files = []
        if os.path.exists(app.config['JSON_FOLDER']):
            for filename in os.listdir(app.config['JSON_FOLDER']):
                if filename.endswith('.json'):
                    filepath = os.path.join(app.config['JSON_FOLDER'], filename)
                    file_size = os.path.getsize(filepath)
                    file_info = parse_filename_info(filename)
                    
                    json_files.append({
                        'filename': filename,
                        'size': file_size,
                        'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M'),
                        'info': file_info
                    })
        
        # 年度順でソート
        json_files.sort(key=lambda x: (x['info']['year'], x['info']['season']) if x['info'] else (0, ''), reverse=True)
        
        admin_data = {
            'question_count': question_count,
            'genres': [row[0] for row in genres],
            'json_files': json_files
        }
    
    return render_template('admin.html', data=admin_data)

@app.route('/admin/upload_json', methods=['POST'])
@admin_required
def upload_json():
    """JSON問題ファイルのアップロードと処理（年度別対応）"""
    if 'json_file' not in request.files:
        return jsonify({'error': 'JSONファイルが選択されていません'}), 400
    
    file = request.files['json_file']
    if file.filename == '':
        return jsonify({'error': 'ファイルが選択されていません'}), 400
    
    if not file.filename.lower().endswith('.json'):
        return jsonify({'error': 'JSONファイルを選択してください'}), 400
    
    try:
        # ファイル内容を読み込み
        content = file.read().decode('utf-8')
        questions = json.loads(content)
        
        # バリデーション
        if not isinstance(questions, list):
            return jsonify({'error': 'JSONファイルは問題の配列である必要があります'}), 400
        
        # 各問題の形式をチェック
        for i, question in enumerate(questions):
            required_fields = ['question_text', 'choices', 'correct_answer']
            for field in required_fields:
                if field not in question:
                    return jsonify({'error': f'問題{i+1}: 必須フィールド "{field}" がありません'}), 400
        
        # ファイル名から年度情報を解析
        file_info = parse_filename_info(file.filename)
        if not file_info:
            # 年度情報がない場合は警告して保存
            flash('ファイル名に年度情報が含まれていません。推奨形式: 2025r07_kamoku_a_spring.json', 'warning')
        
        # JSONファイルを保存
        json_filepath = os.path.join(app.config['JSON_FOLDER'], file.filename)
        with open(json_filepath, 'w', encoding='utf-8') as json_file:
            json.dump(questions, json_file, ensure_ascii=False, indent=2)
        
        message = f'{len(questions)}問の問題を正常に保存しました'
        if file_info:
            message += f' ({file_info["display_name"]})'
        
        return jsonify({
            'message': message,
            'count': len(questions),
            'json_file': file.filename,
            'file_info': file_info
        })
        
    except json.JSONDecodeError:
        return jsonify({'error': 'JSONファイルの形式が正しくありません'}), 400
    except Exception as e:
        return jsonify({'error': f'JSON処理中にエラーが発生しました: {str(e)}'}), 500

@app.route('/admin/load_json/<filename>', methods=['POST'])
@admin_required
def load_json_file(filename):
    """保存されたJSONファイルからデータベースに問題を読み込み"""
    try:
        json_filepath = os.path.join(app.config['JSON_FOLDER'], filename)
        
        if not os.path.exists(json_filepath):
            return jsonify({'error': 'JSONファイルが見つかりません'}), 404
        
        with open(json_filepath, 'r', encoding='utf-8') as json_file:
            questions = json.load(json_file)
        
        # データベースに保存
        saved_count = question_manager.save_questions(questions)
        
        return jsonify({
            'message': f'{saved_count}問の問題を正常に登録しました',
            'count': saved_count
        })
        
    except Exception as e:
        return jsonify({'error': f'JSON読み込み中にエラーが発生しました: {str(e)}'}), 500

@app.route('/admin/create_sample', methods=['POST'])
@admin_required
def create_sample_data():
    """サンプルデータの作成"""
    try:
        processor = PDFProcessor()
        sample_questions = processor.create_sample_questions()
        
        saved_count = question_manager.save_questions(sample_questions)
        
        return jsonify({
            'message': f'{saved_count}問のサンプル問題を作成しました',
            'count': saved_count
        })
        
    except Exception as e:
        return jsonify({'error': f'サンプルデータ作成中にエラーが発生しました: {str(e)}'}), 500

@app.route('/admin/reset_database', methods=['POST'])
@admin_required
def reset_database():
    """データベースの初期化"""
    try:
        with get_db_connection(app.config['DATABASE']) as conn:
            # 全データを削除
            conn.execute('DELETE FROM user_answers')
            conn.execute('DELETE FROM questions')
            conn.commit()
        
        return jsonify({'message': 'データベースを初期化しました'})
        
    except Exception as e:
        return jsonify({'error': f'データベース初期化中にエラーが発生しました: {str(e)}'}), 500

@app.route('/api/questions/random')
def get_random_question():
    """ランダムな問題を1問取得するAPI"""
    question = question_manager.get_random_question()
    if not question:
        return jsonify({'error': '問題が見つかりません'}), 404
    
    return jsonify(question)

@app.route('/random')
def random_question():
    """ランダム問題への直接アクセス"""
    question = question_manager.get_random_question()
    if not question:
        flash('問題が見つかりません。まず問題を登録してください。', 'error')
        return redirect(url_for('admin_login'))
    
    return redirect(url_for('show_question', question_id=question['id']))

@app.errorhandler(404)
def not_found_error(error):
    """404エラーハンドラ"""
    return render_template('error.html', message='ページが見つかりません'), 404

@app.errorhandler(500)
def internal_error(error):
    """500エラーハンドラ"""
    return render_template('error.html', message='内部サーバーエラーが発生しました'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
