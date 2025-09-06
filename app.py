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
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# アプリケーション設定
app.config['DATABASE'] = 'fe_exam.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['JSON_FOLDER'] = 'json_questions'
# 管理者パスワードを環境変数から取得（デフォルトあり）
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'fe2025admin')

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
                        
                        # データベースに保存（重複チェック付き）
                        saved_count = question_manager.save_questions(questions, check_duplicates=True)
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
            'display_name': f'{year}年{season_jp}'
        }
    return None

@app.route('/')
def index():
    """メインページ - ダッシュボード表示"""
    try:
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
    except Exception as e:
        app.logger.error(f"Dashboard error: {e}")
        # エラー時は空の統計を返す
        stats = {
            'total_questions': 0,
            'total_answers': 0,
            'correct_answers': 0,
            'accuracy_rate': 0,
            'recent_history': [],
            'genre_stats': []
        }
        return render_template('dashboard.html', stats=stats)

# 以下、他のルート定義（省略）...

@app.route('/admin/create_extended_sample', methods=['POST'])
@admin_required
def create_extended_sample():
    """拡張サンプルデータの作成（10問）"""
    try:
        processor = PDFProcessor()
        extended_questions = processor.create_extended_sample_questions()
        
        saved_count = question_manager.save_questions(extended_questions)
        
        return jsonify({
            'message': f'{saved_count}問の拡張サンプル問題を作成しました',
            'count': saved_count
        })
        
    except Exception as e:
        app.logger.error(f"Create extended sample error: {e}")
        return jsonify({'error': f'拡張サンプルデータ作成中にエラーが発生しました: {str(e)}'}), 500

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

@app.route('/random')
def random_question():
    """ランダム問題への直接アクセス"""
    try:
        question = question_manager.get_random_question()
        if not question:
            flash('問題が見つかりません。まず問題を登録してください。', 'error')
            return redirect(url_for('admin_login'))
        
        return redirect(url_for('show_question', question_id=question['id']))
    except Exception as e:
        app.logger.error(f"Random question error: {e}")
        flash('ランダム問題の表示中にエラーが発生しました。', 'error')
        return redirect(url_for('index'))

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
