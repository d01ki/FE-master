"""
基本情報技術者試験 学習アプリ - メインアプリケーション
Flask + PostgreSQL/SQLite + ユーザー認証を使用した学習プラットフォーム
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import os
import json
import random
from datetime import datetime, timedelta

# 分割されたモジュールのインポート
from database import DatabaseManager
from auth import login_required, admin_required, init_auth_routes
from question_manager import QuestionManager
from helper_functions import parse_filename_info

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# セッション設定を追加
app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2)
)

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
os.makedirs('static/images', exist_ok=True)

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

# 既存のルート定義はそのまま維持（省略）

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
        
        # セッションに問題を保存
        session['mock_exam_questions'] = questions
        session.modified = True  # セッションの変更を明示的にマーク
        
        print(f"📚 Saved {len(questions)} questions to session")
        print(f"🔑 Session keys: {list(session.keys())}")
        
        return render_template('mock_exam_practice.html', 
                             questions=questions, 
                             exam_info=file_info)
        
    except Exception as e:
        print(f"❌ Mock exam start error: {e}")
        flash(f'試験ファイルの読み込みに失敗しました: {str(e)}', 'error')
        return redirect(url_for('mock_exam'))

@app.route('/mock_exam/submit', methods=['POST'])
@login_required  
def submit_mock_exam():
    """模擬試験の採点"""
    try:
        data = request.get_json()
        answers = data.get('answers', {})
        
        # デバッグログ
        print(f"📝 Received answers: {len(answers)} questions")
        print(f"🔑 Session keys: {list(session.keys())}")
        
        # セッションから問題を取得
        questions = session.get('mock_exam_questions', [])
        
        print(f"📚 Questions from session: {len(questions) if questions else 0}")
        
        if not questions:
            print(f"❌ No questions in session!")
            return jsonify({'error': '試験データが見つかりません。ページを再読み込みして試験を再開してください。'}), 400
        
        # 採点処理
        total_count = len(questions)
        correct_count = 0
        
        for i, question in enumerate(questions):
            question_index = str(i)
            user_answer = answers.get(question_index)
            correct_answer = question.get('correct_answer')
            
            if user_answer and user_answer == correct_answer:
                correct_count += 1
        
        score = round((correct_count / total_count) * 100, 1) if total_count > 0 else 0
        
        # セッションをクリア
        session.pop('mock_exam_questions', None)
        
        print(f"✅ Result: {correct_count}/{total_count} = {score}%")
        
        return jsonify({
            'score': score,
            'correct_count': correct_count,
            'total_count': total_count
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'採点処理中にエラー: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    print(f"🚀 Starting Flask app on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
