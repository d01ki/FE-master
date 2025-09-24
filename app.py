"""
基本情報技術者試験 学習アプリ - メインアプリケーション
Flask + PostgreSQL/SQLite + ユーザー認証を使用した学習プラットフォーム
"""

from flask import Flask, redirect, url_for
import os
from datetime import timedelta
from config import Config

# 分割されたモジュールのインポート
from database import DatabaseManager
from auth import init_auth_routes
from question_manager import QuestionManager
from helper_functions import parse_filename_info

# ルーティングモジュールのインポート
from routes import main_bp, practice_bp, exam_bp, admin_bp, ranking_bp

app = Flask(__name__)

# Configクラスの設定を適用
app.config.from_object(Config)

# セキュリティ強化: SECRET_KEYを環境変数から取得（必須）
if not app.config['SECRET_KEY']:
    if Config.DEBUG:
        # 開発環境用のフォールバック
        app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
        print("⚠️  警告: 開発用のSECRET_KEYを使用しています。本番環境では必ず環境変数を設定してください。")
    else:
        raise ValueError("❌ セキュリティエラー: SECRET_KEY環境変数が設定されていません。本番環境では必須です。")

# セッション設定（セッション時間を延長してRender無料枠でも使いやすく）
app.config.update(
    SESSION_COOKIE_SECURE=not Config.DEBUG,  # 本番環境ではTrue（HTTPS必須）
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24)  # セッション時間を24時間に延長
)

# 管理者パスワードの設定（本番環境では環境変数必須）
if not Config.ADMIN_PASSWORD:
    if Config.DEBUG:
        # 開発環境のみデフォルト使用を許可
        Config.ADMIN_PASSWORD = 'dev-admin-password-CHANGE-ME'
        print("⚠️  警告: 開発用のデフォルト管理者パスワードを使用しています。")
else:
        raise ValueError("❌ セキュリティエラー: 本番環境ではADMIN_PASSWORD環境変数の設定が必須です。")

# フォルダ作成
os.makedirs('uploads', exist_ok=True)
os.makedirs('json_questions', exist_ok=True)
os.makedirs('static/images', exist_ok=True)

# データベースマネージャーの初期化
db_config = Config.get_db_config()
db_manager = DatabaseManager(db_config)
db_manager.init_database()

# QuestionManagerの初期化
question_manager = QuestionManager(db_manager)

# アプリケーションコンテキストに追加
app.db_manager = db_manager
app.question_manager = question_manager
app.config['ADMIN_PASSWORD'] = Config.ADMIN_PASSWORD

# 認証システムの初期化
init_auth_routes(app, db_manager)

# ===== Auth endpoint aliases for compatibility with middleware expecting 'auth.*' endpoints =====
# Some middlewares may call url_for('auth.login') style endpoints; these redirect to actual views.
@app.route('/auth/login', endpoint='auth.login')
def _auth_login_alias():
    return redirect(url_for('login'))

@app.route('/auth/register', endpoint='auth.register')
def _auth_register_alias():
    return redirect(url_for('register'))

@app.route('/auth/logout', endpoint='auth.logout')
def _auth_logout_alias():
    return redirect(url_for('logout'))

# ブループリントの登録
app.register_blueprint(main_bp)
app.register_blueprint(practice_bp)
app.register_blueprint(exam_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(ranking_bp)

# JSONフォルダの問題を自動読み込み
def load_json_questions_on_startup():
    """起動時にJSONフォルダの問題を自動読み込み"""
    try:
        json_folder = 'json_questions'
        if os.path.exists(json_folder):
            existing_count = db_manager.execute_query('SELECT COUNT(*) as count FROM questions')
            existing_total = existing_count[0]['count'] if existing_count else 0
            
            if existing_total == 0:
                print("📚 JSON問題ファイルを読み込み中...")
                
                loaded_files = []
                total_questions = 0
                
                for filename in os.listdir(json_folder):
                    if filename.endswith('.json'):
                        json_filepath = os.path.join(json_folder, filename)
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
    port = Config.PORT
    debug_mode = Config.DEBUG
    
    print(f"🚀 Starting Flask app on port {port}")
    print(f"🔧 Debug mode: {'ON (開発環境)' if debug_mode else 'OFF (本番環境)'}")
    print(f"💾 Database: {Config.DATABASE_TYPE.upper()}")
    print(f"🔒 Cookie Secure: {'ON (HTTPS必須)' if not debug_mode else 'OFF (開発環境)'}")
    
    app.run(debug=debug_mode, host=Config.HOST, port=port)
