from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from config import Config
from persistent_session import DatabaseSessionManager, persistent_login_required, create_persistent_session, destroy_persistent_session

def login_required(f):
    """従来の一時的なセッションでのログイン確認（後方互換性用）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('ログインが必要です。', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理者権限確認（永続セッション対応）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import current_app
        
        # 永続セッションから確認
        session_manager = getattr(current_app, 'session_manager', None)
        if session_manager:
            session_token = session.get('session_token')
            session_data = session_manager.get_session_data(session_token)
            if session_data and session_data['user_data'].get('is_admin'):
                # セッションデータを復元
                for key, value in session_data['user_data'].items():
                    session[key] = value
                return f(*args, **kwargs)
        
        # 従来のセッション確認
        if 'user_id' not in session:
            flash('ログインが必要です。', 'warning')
            return redirect(url_for('admin_login'))
        if not session.get('is_admin'):
            flash('管理者権限が必要です。', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def init_auth_routes(app, db_manager):
    # 永続セッションマネージャーの初期化
    session_manager = DatabaseSessionManager(db_manager)
    app.session_manager = session_manager
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        # 永続セッションチェック
        session_token = session.get('session_token')
        if session_token:
            session_data = session_manager.get_session_data(session_token)
            if session_data:
                return redirect(url_for('main.dashboard'))
        
        if 'user_id' in session:
            return redirect(url_for('main.dashboard'))
            
        if request.method == 'POST':
            username = request.form['username'].strip()
            password = request.form['password']
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            if not username or not password:
                flash('ユーザー名とパスワードを入力してください。', 'error')
                return redirect(url_for('register'))
            
            # Security: Block "admin" username registration (case-insensitive)
            if username.lower() == 'admin':
                flash('このユーザー名は使用できません。別のユーザー名を選択してください。', 'error')
                return redirect(url_for('register'))
            
            if len(username) < 3:
                flash('ユーザー名は3文字以上で入力してください。', 'error')
                return redirect(url_for('register'))
            
            if len(password) < 6:
                flash('パスワードは6文字以上で入力してください。', 'error')
                return redirect(url_for('register'))
                
            if password != confirm_password:
                flash('パスワードが一致しません。', 'error')
                return redirect(url_for('register'))

            # Check duplicate username (case-insensitive)
            try:
                # Check for exact match first
                existing_user = db_manager.execute_query(
                    'SELECT id FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT id FROM users WHERE username = ?',
                    (username,)
                )
                
                # Also check case-insensitive to prevent similar usernames
                if db_manager.db_type == 'postgresql':
                    existing_user_case_insensitive = db_manager.execute_query(
                        'SELECT id FROM users WHERE LOWER(username) = LOWER(%s)',
                        (username,)
                    )
                else:
                    # SQLite is case-insensitive by default for LIKE, but we'll be explicit
                    existing_user_case_insensitive = db_manager.execute_query(
                        'SELECT id FROM users WHERE LOWER(username) = LOWER(?)',
                        (username,)
                    )
                
                if existing_user or existing_user_case_insensitive:
                    flash('このユーザー名は既に使用されています。別のユーザー名を選択してください。', 'error')
                    return redirect(url_for('register'))

                # Create user
                password_hash = generate_password_hash(password)
                db_manager.execute_query(
                    'INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, %s)' if db_manager.db_type == 'postgresql' else 'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                    (username, password_hash, False if db_manager.db_type == 'postgresql' else 0)
                )
                
                flash('登録が完了しました。ログインしてください。', 'success')
                
                return redirect(url_for('login'))
            except Exception as e:
                flash(f'登録エラー: {e}', 'error')
                return redirect(url_for('register'))

        return render_template('auth/register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        # 永続セッションチェック
        session_token = session.get('session_token')
        if session_token:
            session_data = session_manager.get_session_data(session_token)
            if session_data:
                return redirect(url_for('main.dashboard'))
        
        if 'user_id' in session:
            return redirect(url_for('main.dashboard'))
            
        if request.method == 'POST':
            username = request.form['username'].strip()
            password = request.form['password']
            remember_me = request.form.get('remember_me') == 'on'  # ログイン情報を記憶するか
            
            if not username or not password:
                flash('ユーザー名とパスワードを入力してください。', 'error')
                return redirect(url_for('login'))
            
            # Admin login via environment variable (if set)
            if username.lower() == 'admin' and Config.ADMIN_PASSWORD:
                if password == Config.ADMIN_PASSWORD:
                    session.clear()
                    user_data = {
                        'user_id': 'admin',
                        'username': 'admin',
                        'is_admin': True
                    }
                    
                    # 永続セッション作成（管理者も記憶する）
                    if remember_me or True:  # 管理者は常に永続セッション
                        create_persistent_session(session_manager, 'admin', user_data)
                    
                    # 通常のセッションも設定
                    for key, value in user_data.items():
                        session[key] = value
                    
                    flash('管理者としてログインしました。', 'success')
                    return redirect(url_for('admin.admin'))
                else:
                    flash('ユーザー名またはパスワードが正しくありません。', 'error')
                    return redirect(url_for('login'))
            
            try:
                # Case-sensitive username lookup for regular users
                user = db_manager.execute_query(
                    'SELECT * FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT * FROM users WHERE username = ?',
                    (username,)
                )
                
                if user and check_password_hash(user[0]['password_hash'], password):
                    session.clear()
                    user_data = {
                        'user_id': user[0]['id'],
                        'username': user[0]['username'],
                        'is_admin': user[0]['is_admin']
                    }
                    
                    # 永続セッション作成（記憶するにチェックがある場合、または常に有効化）
                    if remember_me or True:  # 常に永続セッションを使用（Render対応）
                        create_persistent_session(session_manager, user[0]['id'], user_data)
                    
                    # 通常のセッションも設定
                    for key, value in user_data.items():
                        session[key] = value
                    
                    flash(f'ようこそ、{username}さん！', 'success')
                    return redirect(url_for('main.dashboard'))
                else:
                    flash('ユーザー名またはパスワードが正しくありません。', 'error')
            except Exception as e:
                flash('ログイン処理中にエラーが発生しました。', 'error')
                app.logger.error(f"Login error: {e}")
                
        return render_template('auth/login.html')

    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        # 永続セッションチェック
        session_token = session.get('session_token')
        if session_token:
            session_data = session_manager.get_session_data(session_token)
            if session_data and session_data['user_data'].get('is_admin'):
                return redirect(url_for('admin.admin'))
        
        if request.method == 'POST':
            username = request.form['username'].strip()
            password = request.form['password']
            
            # Admin login via environment variable only
            if username.lower() == 'admin' and Config.ADMIN_PASSWORD and password == Config.ADMIN_PASSWORD:
                session.clear()
                user_data = {
                    'user_id': 'admin',
                    'username': 'admin',
                    'is_admin': True
                }
                
                # 管理者の永続セッション作成
                create_persistent_session(session_manager, 'admin', user_data)
                
                # 通常のセッションも設定
                for key, value in user_data.items():
                    session[key] = value
                
                flash('管理者としてログインしました。', 'success')
                return redirect(url_for('admin.admin'))
            else:
                flash('管理者のユーザー名またはパスワードが正しくありません。', 'error')
                
        return render_template('admin_login.html')

    @app.route('/logout')
    def logout():
        # 永続セッション削除
        destroy_persistent_session(session_manager)
        flash('ログアウトしました。', 'info')
        return redirect(url_for('login'))

    # 期限切れセッションの定期クリーンアップ
    @app.before_request
    def cleanup_expired_sessions():
        # 10回に1回程度の頻度でクリーンアップ実行
        import random
        if random.randint(1, 10) == 1:
            session_manager.cleanup_expired_sessions()
