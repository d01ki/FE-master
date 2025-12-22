"""
基本情報技術者試験 学習アプリ - メインアプリケーション
Flask + PostgreSQL/SQLite + ユーザー認証を使用した学習プラットフォーム
"""

import os
from datetime import timedelta
from flask import Flask, redirect, url_for

from app.core.config import Config
from app.core.database import DatabaseManager
from app.core.auth import init_auth_routes
from app.core.question_manager import QuestionManager
from app.routes import main_bp, practice_bp, exam_bp, admin_bp, upload_bp


def create_app(config_class=Config):
    """Application Factory Pattern"""
    app = Flask(__name__, 
                template_folder='app/templates',
                static_folder='app/static')
    app.config.from_object(config_class)
    
    # セキュリティ設定
    _configure_security(app, config_class)
    
    # データベース初期化
    db_manager = _init_database(config_class)
    
    # アプリケーションコンテキスト設定
    app.db_manager = db_manager
    app.question_manager = QuestionManager(db_manager)
    app.config['ADMIN_PASSWORD'] = config_class.ADMIN_PASSWORD
    
    # 認証システム初期化
    init_auth_routes(app, db_manager)
    
    # ルーティング登録
    _register_blueprints(app)
    
    # Auth endpoint aliases
    _register_auth_aliases(app)
    
    # 必要なディレクトリ作成
    _create_directories()
    
    return app


def _configure_security(app, config_class):
    """セキュリティ設定"""
    if not app.config['SECRET_KEY']:
        if config_class.DEBUG:
            app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
            app.logger.warning("開発用のSECRET_KEYを使用しています。本番環境では必ず環境変数を設定してください。")
        else:
            raise ValueError("セキュリティエラー: SECRET_KEY環境変数が設定されていません。")
    
    if not config_class.ADMIN_PASSWORD:
        if config_class.DEBUG:
            config_class.ADMIN_PASSWORD = 'dev-admin-password-CHANGE-ME'
            app.logger.warning("開発用のデフォルト管理者パスワードを使用しています。")
        else:
            raise ValueError("セキュリティエラー: ADMIN_PASSWORD環境変数が設定されていません。")
    
    # セッション設定
    app.config.update(
        SESSION_COOKIE_SECURE=not config_class.DEBUG,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
    )


def _init_database(config_class):
    """データベース初期化"""
    try:
        # Config オブジェクトを直接渡す
        db_manager = DatabaseManager(config_class)
        db_manager.init_database()
        return db_manager
    except Exception as e:
        raise RuntimeError(f"データベース初期化エラー: {e}")


def _register_blueprints(app):
    """ブループリント登録"""
    blueprints = [
        (main_bp, {}),
        (practice_bp, {}),
        (exam_bp, {}),
        (upload_bp, {}),
        (admin_bp, {})
    ]
    
    for blueprint, options in blueprints:
        app.register_blueprint(blueprint, **options)


def _register_auth_aliases(app):
    """認証エンドポイントエイリアス登録"""
    @app.route('/auth/login', endpoint='auth.login')
    def _auth_login_alias():
        return redirect(url_for('login'))

    @app.route('/auth/register', endpoint='auth.register')  
    def _auth_register_alias():
        return redirect(url_for('register'))

    @app.route('/auth/logout', endpoint='auth.logout')
    def _auth_logout_alias():
        return redirect(url_for('logout'))


def _create_directories():
    """必要なディレクトリ作成"""
    directories = ['json_questions', 'static/images']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def load_initial_questions(app):
    """初期問題データ読み込み"""
    with app.app_context():
        try:
            json_folder = 'json_questions'
            if not os.path.exists(json_folder):
                app.logger.info("JSON問題フォルダが見つかりません。スキップします。")
                return

            existing_count = app.db_manager.execute_query('SELECT COUNT(*) as count FROM questions')
            existing_total = existing_count[0]['count'] if existing_count else 0
            
            if existing_total > 0:
                app.logger.info(f"データベースに既に {existing_total}問の問題が登録されています。")
                return
                
            app.logger.info("JSON問題ファイルを読み込み中...")
            _process_json_files(app, json_folder)
            
        except Exception as e:
            app.logger.error(f"初期問題データ読み込みエラー: {e}")


def _process_json_files(app, json_folder):
    """JSONファイル処理"""
    import json
    
    loaded_files = []
    total_questions = 0
    
    for filename in os.listdir(json_folder):
        if not filename.endswith('.json'):
            continue
            
        json_filepath = os.path.join(json_folder, filename)
        try:
            with open(json_filepath, 'r', encoding='utf-8') as json_file:
                questions = json.load(json_file)
            
            app.logger.info(f"   📄 {filename}: {len(questions)}問を読み込み中...")
            result = app.question_manager.save_questions(questions, filename)
            
            if result['saved_count'] > 0:
                loaded_files.append({
                    'filename': filename,
                    'file_questions': len(questions),
                    'saved_count': result['saved_count']
                })
                total_questions += result['saved_count']
                
        except Exception as e:
            app.logger.error(f"ファイル {filename} の読み込みエラー: {e}")
            continue
    
    if loaded_files:
        app.logger.info(f"✅ {len(loaded_files)}個のファイルから合計 {total_questions}問を読み込み完了")
        for file_info in loaded_files:
            app.logger.info(f"   📄 {file_info['filename']}: {file_info['saved_count']}問保存")
    else:
        app.logger.warning("JSONファイルの読み込みに失敗しました。")


# アプリケーション作成
app = create_app()

if __name__ == '__main__':
    # 初期データ読み込み
    load_initial_questions(app)
    
    # アプリケーション起動
    app.logger.info(f"🚀 Starting Flask app on port {Config.PORT}")
    app.logger.info(f"🔧 Debug mode: {'ON (開発環境)' if Config.DEBUG else 'OFF (本番環境)'}")
    app.logger.info(f"💾 Database: {Config.DATABASE_TYPE.upper()}")
    app.logger.info(f"🔒 Cookie Secure: {'ON (HTTPS必須)' if not Config.DEBUG else 'OFF (開発環境)'}")
    
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)