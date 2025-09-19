"""
メインページのルーティング
"""
from flask import Blueprint, render_template, session, redirect, url_for, current_app
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
    db_manager = current_app.db_manager
    question_manager = current_app.question_manager
    user_id = session.get('user_id')
    
    # 統計情報を取得
    stats = {
        'total_questions': question_manager.get_total_questions(),
        'correct_answers': 0,
        'accuracy_rate': 0,
        'total_answers': 0
    }
    
    if user_id and user_id != 'admin':
        # ユーザーの解答統計を取得
        if db_manager.db_type == 'postgresql':
            user_stats = db_manager.execute_query('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
                FROM user_answers 
                WHERE user_id = %s
            ''', (user_id,))
        else:
            user_stats = db_manager.execute_query('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
                FROM user_answers 
                WHERE user_id = ?
            ''', (user_id,))
        
        if user_stats and user_stats[0]['total'] > 0:
            stats['total_answers'] = user_stats[0]['total']
            stats['correct_answers'] = user_stats[0]['correct'] or 0
            if stats['total_answers'] > 0:
                stats['accuracy_rate'] = round((stats['correct_answers'] / stats['total_answers']) * 100, 1)
    
    return render_template('dashboard.html', stats=stats)

@main_bp.route('/history')
@login_required
def history():
    """学習履歴ページ"""
    db_manager = current_app.db_manager
    user_id = session.get('user_id')
    
    # ユーザーの解答履歴を取得
    if db_manager.db_type == 'postgresql':
        history_data = db_manager.execute_query('''
            SELECT 
                ua.id,
                ua.question_id,
                q.question_text,
                q.genre,
                ua.user_answer,
                q.correct_answer,
                ua.is_correct,
                ua.answered_at
            FROM user_answers ua
            LEFT JOIN questions q ON ua.question_id = q.id
            WHERE ua.user_id = %s
            ORDER BY ua.answered_at DESC
            LIMIT 100
        ''', (user_id,))
    else:
        history_data = db_manager.execute_query('''
            SELECT 
                ua.id,
                ua.question_id,
                q.question_text,
                q.genre,
                ua.user_answer,
                q.correct_answer,
                ua.is_correct,
                ua.answered_at
            FROM user_answers ua
            LEFT JOIN questions q ON ua.question_id = q.id
            WHERE ua.user_id = ?
            ORDER BY ua.answered_at DESC
            LIMIT 100
        ''', (user_id,))
    
    # ジャンル別統計
    if db_manager.db_type == 'postgresql':
        genre_stats = db_manager.execute_query('''
            SELECT 
                q.genre,
                COUNT(*) as total,
                SUM(CASE WHEN ua.is_correct THEN 1 ELSE 0 END) as correct
            FROM user_answers ua
            LEFT JOIN questions q ON ua.question_id = q.id
            WHERE ua.user_id = %s AND q.genre IS NOT NULL
            GROUP BY q.genre
            ORDER BY q.genre
        ''', (user_id,))
    else:
        genre_stats = db_manager.execute_query('''
            SELECT 
                q.genre,
                COUNT(*) as total,
                SUM(CASE WHEN ua.is_correct THEN 1 ELSE 0 END) as correct
            FROM user_answers ua
            LEFT JOIN questions q ON ua.question_id = q.id
            WHERE ua.user_id = ? AND q.genre IS NOT NULL
            GROUP BY q.genre
            ORDER BY q.genre
        ''', (user_id,))
    
    # 正答率を計算
    for stat in genre_stats:
        if stat['total'] > 0:
            stat['accuracy'] = round((stat['correct'] / stat['total']) * 100, 1)
        else:
            stat['accuracy'] = 0
    
    return render_template('history.html', 
                         history=history_data, 
                         genre_stats=genre_stats)
