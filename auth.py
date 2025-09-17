from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import os

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('ログインが必要です。', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('ログインが必要です。', 'warning')
            return redirect(url_for('admin_login'))
        if not session.get('is_admin'):
            flash('管理者権限が必要です。', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def init_auth_routes(app, db_manager):
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
            
        if request.method == 'POST':
            username = request.form['username'].strip()
            password = request.form['password']
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            if not username or not password:
                flash('ユーザー名とパスワードを入力してください。', 'error')
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

            # Check duplicate username
            try:
                existing_user = db_manager.execute_query(
                    'SELECT id FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT id FROM users WHERE username = ?',
                    (username,)
                )
                if existing_user:
                    flash('このユーザー名は既に使用されています。', 'error')
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
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
            
        if request.method == 'POST':
            username = request.form['username'].strip()
            password = request.form['password']
            
            if not username or not password:
                flash('ユーザー名とパスワードを入力してください。', 'error')
                return redirect(url_for('login'))
            
            # 管理者ログインの特別処理
            if username == 'admin' and password == 'fe2025@adminPass':
                session.clear()
                session['user_id'] = 'admin'
                session['username'] = 'admin'
                session['is_admin'] = True
                flash('管理者としてログインしました。', 'success')
                return redirect(url_for('admin'))
            
            try:
                user = db_manager.execute_query(
                    'SELECT * FROM users WHERE username = %s' if db_manager.db_type == 'postgresql' else 'SELECT * FROM users WHERE username = ?',
                    (username,)
                )
                
                if user and check_password_hash(user[0]['password_hash'], password):
                    session.clear()
                    session['user_id'] = user[0]['id']
                    session['username'] = user[0]['username']
                    session['is_admin'] = user[0]['is_admin']
                    flash(f'ようこそ、{username}さん！', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('ユーザー名またはパスワードが正しくありません。', 'error')
            except Exception as e:
                flash('ログイン処理中にエラーが発生しました。', 'error')
                app.logger.error(f"Login error: {e}")
                
        return render_template('auth/login.html')

    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        if request.method == 'POST':
            username = request.form['username'].strip()
            password = request.form['password']
            
            # 管理者専用ログイン
            if username == 'admin' and password == 'fe2025@adminPass':
                session.clear()
                session['user_id'] = 'admin'
                session['username'] = 'admin'
                session['is_admin'] = True
                flash('管理者としてログインしました。', 'success')
                return redirect(url_for('admin'))
            else:
                flash('管理者のユーザー名またはパスワードが正しくありません。', 'error')
                
        return render_template('admin_login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('ログアウトしました。', 'info')
        return redirect(url_for('login'))
