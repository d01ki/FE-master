"""
メインページのルーティング
"""
from flask import Blueprint, render_template, session, redirect, url_for, current_app
from auth import login_required
from persistent_session import persistent_login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/index')
def index():
    """トップページ - 未ログインユーザーはログインページへリダイレクト"""
    # 永続セッションチェック
    session_manager = getattr(current_app, 'session_manager', None)
    if session_manager:
        session_token = session.get('session_token')
        if session_token:
            session_data = session_manager.get_session_data(session_token)
            if session_data:
                # セッションデータを復元
                for key, value in session_data['user_data'].items():
                    session[key] = value
                return redirect(url_for('main.dashboard'))
    
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    # 未ログインユーザーは直接ログインページへ
    return redirect(url_for('login'))

@main_bp.route('/dashboard')
@persistent_login_required
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
@persistent_login_required
def history():
    """学習履歴ページ"""
    db_manager = current_app.db_manager
    user_id = session.get('user_id')
    
    # ユーザーの解答履歴を取得（解説も含む）
    # 問題が削除されている場合も考慮してINNER JOINに変更
    if db_manager.db_type == 'postgresql':
        history_data = db_manager.execute_query('''
            SELECT 
                ua.id,
                ua.question_id,
                COALESCE(q.question_text, '（削除された問題）') as question_text,
                COALESCE(q.genre, '不明') as genre,
                ua.user_answer,
                COALESCE(q.correct_answer, '不明') as correct_answer,
                q.explanation,
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
                COALESCE(q.question_text, '（削除された問題）') as question_text,
                COALESCE(q.genre, '不明') as genre,
                ua.user_answer,
                COALESCE(q.correct_answer, '不明') as correct_answer,
                q.explanation,
                ua.is_correct,
                ua.answered_at
            FROM user_answers ua
            LEFT JOIN questions q ON ua.question_id = q.id
            WHERE ua.user_id = ?
            ORDER BY ua.answered_at DESC
            LIMIT 100
        ''', (user_id,))
    
    # Noneチェック
    safe_history = []
    for item in history_data:
        safe_item = dict(item)
        if safe_item['question_text'] is None:
            safe_item['question_text'] = '（削除された問題）'
        if safe_item['genre'] is None:
            safe_item['genre'] = '不明'
        if safe_item['correct_answer'] is None:
            safe_item['correct_answer'] = '不明'
        safe_history.append(safe_item)
    
    return render_template('history.html', history=safe_history)
