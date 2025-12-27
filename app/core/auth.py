from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from .config import Config


def login_required(f):
    """ログイン確認デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session and 'admin_logged_in' not in session:
            flash('ログインしてください。', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """管理者権限確認デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('管理者権限が必要です。', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def init_auth_routes(app, db_manager):
    """認証ルートの初期化"""
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            # XSS対策: 危険な文字を検出
            if any(char in username for char in ['<', '>', '"', "'", '&', ';']):
                flash('ユーザー名に使用できない文字が含まれています。', 'error')
                return render_template('auth/login.html')
            
            if not username or not password:
                flash('ユーザー名とパスワードを入力してください。', 'error')
                return render_template('auth/login.html')
            
            # 管理者ログイン確認
            if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
                session.permanent = True
                session['admin_logged_in'] = True
                session['username'] = username
                flash('管理者としてログインしました。', 'success')
                return redirect(url_for('main.dashboard'))
            
            # 一般ユーザーログイン確認
            users = db_manager.execute_query(
                'SELECT id, username, password_hash FROM users WHERE username = ?', 
                (username,)
            )
            
            if users and check_password_hash(users[0]['password_hash'], password):
                from markupsafe import escape
                session.permanent = True
                session['user_id'] = users[0]['id']
                session['username'] = users[0]['username']
                flash(f'{escape(username)}さん、ようこそ！', 'success')
                return redirect(url_for('main.dashboard'))
            else:
                flash('ユーザー名またはパスワードが正しくありません。', 'error')
                
        return render_template('auth/login.html')
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            # XSS対策: 危険な文字を検出
            if any(char in username for char in ['<', '>', '"', "'", '&', ';']):
                flash('ユーザー名に使用できない文字が含まれています。英数字とアンダースコア、ハイフンのみ使用できます。', 'error')
                return render_template('auth/register.html')
            
            if not username or not password:
                flash('ユーザー名とパスワードを入力してください。', 'error')
                return render_template('auth/register.html')
            
            if len(username) < 3:
                flash('ユーザー名は3文字以上で入力してください。', 'error')
                return render_template('auth/register.html')
            
            if len(username) > 50:
                flash('ユーザー名は50文字以内で入力してください。', 'error')
                return render_template('auth/register.html')
                
            if len(password) < 6:
                flash('パスワードは6文字以上で入力してください。', 'error')
                return render_template('auth/register.html')
            
            # ユーザー名重複確認
            existing_users = db_manager.execute_query(
                'SELECT id FROM users WHERE username = ?', 
                (username,)
            )
            
            if existing_users:
                flash('そのユーザー名は既に使用されています。', 'error')
                return render_template('auth/register.html')
            
            # ユーザー作成
            password_hash = generate_password_hash(password)
            try:
                db_manager.execute_query(
                    'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                    (username, password_hash)
                )
                flash('アカウントが作成されました。ログインしてください。', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                flash('アカウント作成に失敗しました。', 'error')
                app.logger.error(f"ユーザー登録エラー: {e}")
                
        return render_template('auth/register.html')
    
    @app.route('/logout')
    def logout():
        from markupsafe import escape
        username = escape(session.get('username', 'ユーザー'))
        session.clear()
        flash(f'{username}さん、ログアウトしました。', 'info')
        return redirect(url_for('login'))