"""
メインページのルーティング
"""
from flask import Blueprint, render_template, session, redirect, url_for
from auth import login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/index')
def index():
    """トップページ"""
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """ダッシュボード"""
    return render_template('dashboard.html')
