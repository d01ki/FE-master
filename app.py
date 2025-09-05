"""
基本情報技術者試験 学習アプリ
Flask + SQLite + Tailwind CSS を使用した学習プラットフォーム
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import sqlite3
import json
import os
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

# データベースの初期化
if not os.path.exists(app.config['DATABASE']):
    init_db(app.config['DATABASE'])

# QuestionManagerの初期化
question_manager = QuestionManager(app.config['DATABASE'])

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
    """模擬試験"""
    # 午前問題80問をランダムに抽出
    questions = question_manager.get_random_questions(80)
    
    if len(questions) < 80:
        return render_template('error.html', 
                             message=f'模擬試験に必要な問題数が不足しています。現在: {len(questions)}問')
    
    # セッションに試験開始時刻を保存
    session['exam_start_time'] = datetime.now().isoformat()
    session['exam_questions'] = [q['id'] for q in questions]
    
    return render_template('mock_exam.html', questions=questions)

@app.route('/mock_exam/submit', methods=['POST'])
def submit_mock_exam():
    """模擬試験の採点"""
    data = request.get_json()
    answers = data.get('answers', {})
    
    if 'exam_questions' not in session:
        return jsonify({'error': '試験セッションが見つかりません'}), 400
    
    question_ids = session['exam_questions']
    results = []
    correct_count = 0
    
    for question_id in question_ids:
        question_id_str = str(question_id)
        user_answer = answers.get(question_id_str, '')
        
        result = question_manager.check_answer(question_id, user_answer)
        question_manager.save_answer_history(question_id, user_answer, result['is_correct'])
        
        results.append({
            'question_id': question_id,
            'user_answer': user_answer,
            'correct_answer': result['correct_answer'],
            'is_correct': result['is_correct']
        })
        
        if result['is_correct']:
            correct_count += 1
    
    score = round((correct_count / len(question_ids)) * 100, 1)
    
    # セッションクリア
    session.pop('exam_start_time', None)
    session.pop('exam_questions', None)
    
    return jsonify({
        'score': score,
        'correct_count': correct_count,
        'total_count': len(question_ids),
        'results': results
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
def admin():
    """管理画面"""
    with get_db_connection(app.config['DATABASE']) as conn:
        question_count = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
        genres = conn.execute('SELECT DISTINCT genre FROM questions').fetchall()
        
        admin_data = {
            'question_count': question_count,
            'genres': [row[0] for row in genres]
        }
    
    return render_template('admin.html', data=admin_data)

@app.route('/admin/upload_pdf', methods=['POST'])
def upload_pdf():
    """PDF問題集のアップロードと処理"""
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'PDFファイルが選択されていません'}), 400
    
    file = request.files['pdf_file']
    if file.filename == '':
        return jsonify({'error': 'ファイルが選択されていません'}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'PDFファイルを選択してください'}), 400
    
    try:
        # アップロードフォルダが存在しない場合は作成
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # ファイル保存
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        # PDF処理
        processor = PDFProcessor()
        questions = processor.extract_questions_from_pdf(filepath)
        
        # データベースに保存
        saved_count = question_manager.save_questions(questions)
        
        # 一時ファイル削除
        os.remove(filepath)
        
        return jsonify({
            'message': f'{saved_count}問の問題を正常に登録しました',
            'count': saved_count
        })
        
    except Exception as e:
        return jsonify({'error': f'PDF処理中にエラーが発生しました: {str(e)}'}), 500

@app.route('/admin/create_sample', methods=['POST'])
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

@app.route('/api/stats')
def get_stats():
    """統計データ取得API"""
    with get_db_connection(app.config['DATABASE']) as conn:
        # 基本統計
        total_questions = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
        total_answers = conn.execute('SELECT COUNT(*) FROM user_answers').fetchone()[0]
        correct_answers = conn.execute('SELECT COUNT(*) FROM user_answers WHERE is_correct = 1').fetchone()[0]
        
        # ジャンル別統計
        genre_stats = conn.execute('''
            SELECT q.genre, 
                   COUNT(*) as total,
                   SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct,
                   ROUND(AVG(CASE WHEN ua.is_correct = 1 THEN 100.0 ELSE 0.0 END), 1) as accuracy
            FROM user_answers ua 
            JOIN questions q ON ua.question_id = q.id 
            GROUP BY q.genre
            ORDER BY accuracy DESC
        ''').fetchall()
        
        stats = {
            'total_questions': total_questions,
            'total_answers': total_answers,
            'correct_answers': correct_answers,
            'accuracy_rate': round((correct_answers / total_answers * 100), 1) if total_answers > 0 else 0,
            'genre_stats': [dict(row) for row in genre_stats]
        }
    
    return jsonify(stats)

@app.route('/api/genre_count')
def get_genre_count():
    """ジャンル別問題数取得API"""
    genre = request.args.get('genre')
    if not genre:
        return jsonify({'error': 'ジャンルが指定されていません'}), 400
    
    with get_db_connection(app.config['DATABASE']) as conn:
        count = conn.execute('SELECT COUNT(*) FROM questions WHERE genre = ?', (genre,)).fetchone()[0]
    
    return jsonify({'count': count})

# ランダム問題への直接アクセス
@app.route('/random')
def random_question():
    """ランダム問題への直接アクセス"""
    question = question_manager.get_random_question()
    if not question:
        flash('問題が見つかりません。まず問題を登録してください。', 'error')
        return redirect(url_for('admin'))
    
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
