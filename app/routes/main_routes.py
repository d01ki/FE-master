"""
メインページのルーティング
"""
from flask import Blueprint, render_template, session, redirect, url_for, current_app, jsonify
from app.core.auth import login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/health')
def health():
    """ヘルスチェックエンドポイント"""
    return jsonify({'status': 'healthy', 'timestamp': 'ok'}), 200

@main_bp.route('/')
@main_bp.route('/index')
def index():
    """トップページ - ログイン状態に応じてリダイレクト"""
    if 'admin_logged_in' in session or session.get('is_admin'):
        # 管理者は管理画面へ
        return redirect(url_for('admin.admin_dashboard'))
    elif 'user_id' in session:
        # ログインユーザーはダッシュボードへ自動リダイレクト
        return redirect(url_for('main.dashboard'))
    else:
        # 未ログインユーザーはログインページへリダイレクト
        return redirect(url_for('login'))

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
    
    # ジャンル一覧を取得
    genres = question_manager.get_all_genres()
    
    if user_id and user_id != 'admin':
        # ユーザーの解答統計を取得
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
    
    return render_template('dashboard.html', stats=stats, genres=genres)

@main_bp.route('/history')
@login_required
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
    
    # Noneチェックとdatetime変換
    safe_history = []
    for item in history_data:
        safe_item = dict(item)
        if safe_item['question_text'] is None:
            safe_item['question_text'] = '（削除された問題）'
        if safe_item['genre'] is None:
            safe_item['genre'] = '不明'
        if safe_item['correct_answer'] is None:
            safe_item['correct_answer'] = '不明'
        
        # datetime を文字列に変換
        if safe_item.get('answered_at'):
            if hasattr(safe_item['answered_at'], 'strftime'):
                safe_item['answered_at'] = safe_item['answered_at'].strftime('%Y-%m-%d %H:%M')
            elif isinstance(safe_item['answered_at'], str):
                # PostgreSQLから文字列として返される場合は最初の16文字を取得
                safe_item['answered_at'] = safe_item['answered_at'][:16]
        else:
            safe_item['answered_at'] = None
            
        safe_history.append(safe_item)
    
    return render_template('history.html', history=safe_history)

@main_bp.route('/ranking')
@login_required
def ranking():
    """ユーザーランキングページ"""
    db_manager = current_app.db_manager
    user_id = session.get('user_id')

    ranking_rows = db_manager.get_user_rankings(limit=50) or []
    ranking_data = []
    for idx, row in enumerate(ranking_rows, start=1):
        entry = dict(row)
        entry['rank'] = idx
        if entry.get('last_answered_at'):
            if hasattr(entry['last_answered_at'], 'strftime'):
                entry['last_answered_at'] = entry['last_answered_at'].strftime('%Y-%m-%d %H:%M')
            elif isinstance(entry['last_answered_at'], str):
                entry['last_answered_at'] = entry['last_answered_at'][:16]
        ranking_data.append(entry)

    current_user_stat = db_manager.get_user_stat(user_id) if user_id else None
    current_user_rank = None
    if current_user_stat and current_user_stat.get('total_answers', 0) > 0:
        if current_user_stat.get('last_answered_at'):
            if hasattr(current_user_stat['last_answered_at'], 'strftime'):
                current_user_stat['last_answered_at'] = current_user_stat['last_answered_at'].strftime('%Y-%m-%d %H:%M')
            elif isinstance(current_user_stat['last_answered_at'], str):
                current_user_stat['last_answered_at'] = current_user_stat['last_answered_at'][:16]
        current_user_rank = db_manager.get_user_rank(user_id)

    return render_template(
        'ranking.html',
        ranking=ranking_data,
        current_user=current_user_stat,
        current_user_rank=current_user_rank
    )
