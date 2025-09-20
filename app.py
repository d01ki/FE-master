"""
基本情報技術者試験 学習アプリ - メインアプリケーション
Flask + PostgreSQL/SQLite + ユーザー認証を使用した学習プラットフォーム
"""

from flask import Flask
import os
from datetime import timedelta

# 分割されたモジュールのインポート
from database import DatabaseManager
from auth import init_auth_routes
from question_manager import QuestionManager
from helper_functions import parse_filename_info

# ルーティングモジュールのインポート
from routes import main_bp, practice_bp, exam_bp, admin_bp

app = Flask(__name__)

# セキュリティ強化: SECRET_KEYを環境変数から取得（必須）
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    # 開発環境用のフォールバック（本番では必ず環境変数を設定）
    if os.environ.get('FLASK_ENV') == 'development':
        app.secret_key = 'dev-secret-key-change-in-production'
        print("⚠️  警告: 開発用のSECRET_KEYを使用しています。本番環境では必ず環境変数を設定してください。")
    else:
        raise ValueError("❌ セキュリティエラー: SECRET_KEY環境変数が設定されていません。本番環境では必須です。")

# セッション設定
app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2)
)

# データベース設定
DATABASE_URL = os.environ.get('DATABASE_URL')
DATABASE_TYPE = 'postgresql' if DATABASE_URL else 'sqlite'

# 管理者パスワードの設定（環境変数から取得、デフォルトあり）
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'fe2025admin')
if ADMIN_PASSWORD == 'fe2025admin':
    print("⚠️  警告: デフォルトの管理者パスワードを使用しています。セキュリティのため変更を推奨します。")

app.config.update({
    'DATABASE_URL': DATABASE_URL,
    'DATABASE': 'fe_exam.db',
    'DATABASE_TYPE': DATABASE_TYPE,
    'UPLOAD_FOLDER': 'uploads',
    'JSON_FOLDER': 'json_questions',
    'ADMIN_PASSWORD': ADMIN_PASSWORD
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

# アプリケーションコンテキストに追加
app.db_manager = db_manager
app.question_manager = question_manager

# 認証システムの初期化
init_auth_routes(app, db_manager)

# ブループリントの登録
app.register_blueprint(main_bp)
app.register_blueprint(practice_bp)
app.register_blueprint(exam_bp)
app.register_blueprint(admin_bp)

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
                            import json
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    # デバッグモードは開発環境のみ有効化（本番環境では自動的に無効）
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"🚀 Starting Flask app on port {port}")
    print(f"🔧 Debug mode: {'ON (開発環境)' if debug_mode else 'OFF (本番環境)'}")
    print(f"💾 Database: {DATABASE_TYPE.upper()}")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
