"""
管理者用ユーザー管理機能
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from app.core.auth import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@admin_required
def admin_dashboard():
    """管理者ダッシュボード"""
    db_manager = current_app.db_manager
    
    # システム統計の取得
    stats = _get_system_stats(db_manager)
    
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/admin/users')
@admin_required
def user_management():
    """ユーザー管理画面"""
    db_manager = current_app.db_manager
    
    # ユーザー一覧と統計の取得
    users = _get_users_with_stats(db_manager)
    total_users = len(users)
    active_users = len([u for u in users if not u.get('is_inactive')])
    
    return render_template('admin/users.html', 
                         users=users, 
                         total_users=total_users,
                         active_users=active_users)

@admin_bp.route('/admin/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    """ユーザー詳細画面（簡略化）"""
    # 詳細画面は不要なのでユーザー一覧にリダイレクト
    flash('ユーザー詳細画面は現在利用できません。', 'info')
    return redirect(url_for('admin.user_management'))

@admin_bp.route('/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin_status(user_id):
    """ユーザーの管理者権限切り替え"""
    db_manager = current_app.db_manager
    
    # 自分自身の権限は変更できない
    if user_id == session.get('user_id'):
        flash('自分自身の管理者権限は変更できません。', 'error')
        return redirect(url_for('admin.user_management'))
    
    try:
        # 現在の権限を取得
        user = db_manager.execute_query(
            "SELECT is_admin FROM users WHERE id = ?", (user_id,)
        )
        if not user:
            flash('ユーザーが見つかりません。', 'error')
            return redirect(url_for('admin.user_management'))
        
        current_admin = user[0].get('is_admin', 0)
        new_admin = 0 if current_admin else 1
        
        # 権限更新
        db_manager.execute_query(
            "UPDATE users SET is_admin = ? WHERE id = ?", 
            (new_admin, user_id)
        )
        
        status_text = "付与" if new_admin else "削除"
        flash(f'管理者権限を{status_text}しました。', 'success')
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('admin.user_management'))

@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """ユーザーを完全削除（DBから削除）"""
    db_manager = current_app.db_manager
    
    # 自分自身は削除できない
    if user_id == session.get('user_id'):
        flash('自分自身を削除することはできません。', 'error')
        return redirect(url_for('admin.user_management'))
    
    try:
        # ユーザーの存在確認
        user = db_manager.execute_query(
            "SELECT username, is_admin FROM users WHERE id = ?", (user_id,)
        )
        if not user:
            flash('ユーザーが見つかりません。', 'error')
            return redirect(url_for('admin.user_management'))
        
        username = user[0].get('username')
        is_admin = user[0].get('is_admin', 0)
        
        # 管理者の場合は警告
        if is_admin:
            flash('管理者アカウントは削除できません。先に管理者権限を削除してください。', 'error')
            return redirect(url_for('admin.user_management'))
        
        # ユーザーの解答履歴を削除
        db_manager.execute_query(
            "DELETE FROM user_answers WHERE user_id = ?", (user_id,)
        )
        
        # ユーザーを削除
        db_manager.execute_query(
            "DELETE FROM users WHERE id = ?", (user_id,)
        )
        
        flash(f'ユーザー「{username}」を完全に削除しました。', 'success')
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('admin.user_management'))

def _get_system_stats(db_manager):
    """システム統計取得"""
    try:
        # 総問題数
        questions_count = db_manager.execute_query(
            "SELECT COUNT(*) as count FROM questions"
        )[0]['count']
        
        # 総ユーザー数
        users_count = db_manager.execute_query(
            "SELECT COUNT(*) as count FROM users"
        )[0]['count']
        
        # 総解答数
        answers_count = db_manager.execute_query(
            "SELECT COUNT(*) as count FROM user_answers"
        )[0]['count']
        
        # ジャンル数
        genres_count = db_manager.execute_query(
            "SELECT COUNT(DISTINCT genre) as count FROM questions WHERE genre IS NOT NULL"
        )[0]['count']
        
        return {
            'questions_count': questions_count,
            'users_count': users_count,
            'answers_count': answers_count,
            'genres_count': genres_count
        }
    except Exception:
        return {
            'questions_count': 0,
            'users_count': 0, 
            'answers_count': 0,
            'genres_count': 0
        }

def _get_users_with_stats(db_manager):
    """統計付きユーザー一覧取得"""
    try:
        users = db_manager.execute_query("""
            SELECT u.id, u.username, u.created_at, u.is_admin,
                   COUNT(ua.id) as total_answers,
                   SUM(CASE WHEN ua.is_correct THEN 1 ELSE 0 END) as correct_answers,
                   MAX(ua.answered_at) as last_activity
            FROM users u
            LEFT JOIN user_answers ua ON u.id = ua.user_id
            GROUP BY u.id, u.username, u.created_at, u.is_admin
            ORDER BY u.created_at DESC
        """)
        
        # 正答率とdatetime変換を処理
        for user in users:
            if user['total_answers'] > 0:
                user['accuracy_rate'] = round((user['correct_answers'] / user['total_answers']) * 100, 1)
            else:
                user['accuracy_rate'] = 0
            
            # datetime を文字列に変換
            if user.get('created_at'):
                if hasattr(user['created_at'], 'strftime'):
                    user['created_at'] = user['created_at'].strftime('%Y-%m-%d')
                elif isinstance(user['created_at'], str):
                    user['created_at'] = user['created_at'][:10]
            
            if user.get('last_activity'):
                if hasattr(user['last_activity'], 'strftime'):
                    user['last_activity'] = user['last_activity'].strftime('%Y-%m-%d')
                elif isinstance(user['last_activity'], str):
                    user['last_activity'] = user['last_activity'][:10]
                
        return users
    except Exception as e:
        print(f"Error getting users: {e}")
        return []