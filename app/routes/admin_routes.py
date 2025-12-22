"""
管理者用ユーザー管理機能
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.core.auth import admin_required
from datetime import datetime

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
    """ユーザー詳細画面"""
    db_manager = current_app.db_manager
    
    # ユーザー基本情報
    user = db_manager.execute_query(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    )
    if not user:
        flash('ユーザーが見つかりません。', 'error')
        return redirect(url_for('admin.user_management'))
    
    user = user[0]
    
    # 学習統計
    stats = _get_user_detailed_stats(db_manager, user_id)
    
    # 最近の解答履歴
    recent_answers = db_manager.execute_query("""
        SELECT ua.*, q.question_text, q.genre 
        FROM user_answers ua
        LEFT JOIN questions q ON ua.question_id = q.id
        WHERE ua.user_id = ?
        ORDER BY ua.answered_at DESC
        LIMIT 20
    """, (user_id,))
    
    return render_template('admin/user_detail.html', 
                         user=user, 
                         stats=stats, 
                         recent_answers=recent_answers)

@admin_bp.route('/admin/users/<int:user_id>/reset', methods=['POST'])
@admin_required
def reset_user_progress(user_id):
    """ユーザーの学習進捗リセット"""
    db_manager = current_app.db_manager
    
    try:
        # 解答履歴を削除
        db_manager.execute_query(
            "DELETE FROM user_answers WHERE user_id = ?", (user_id,)
        )
        flash('ユーザーの学習進捗をリセットしました。', 'success')
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@admin_required  
def toggle_user_status(user_id):
    """ユーザーの有効/無効切り替え"""
    db_manager = current_app.db_manager
    
    try:
        # ユーザーテーブルにis_activeカラムがない場合は追加
        db_manager.execute_query("""
            ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1
        """)
    except:
        pass  # カラムが既に存在する場合
    
    try:
        # 現在のステータスを取得
        user = db_manager.execute_query(
            "SELECT is_active FROM users WHERE id = ?", (user_id,)
        )
        if not user:
            flash('ユーザーが見つかりません。', 'error')
            return redirect(url_for('admin.user_management'))
        
        current_status = user[0].get('is_active', 1)
        new_status = 0 if current_status else 1
        
        # ステータス更新
        db_manager.execute_query(
            "UPDATE users SET is_active = ? WHERE id = ?", 
            (new_status, user_id)
        )
        
        status_text = "有効" if new_status else "無効"
        flash(f'ユーザーを{status_text}にしました。', 'success')
        
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

def _get_user_detailed_stats(db_manager, user_id):
    """ユーザー詳細統計取得"""
    try:
        # 基本統計
        basic_stats = db_manager.execute_query("""
            SELECT 
                COUNT(*) as total_answers,
                SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
                MIN(answered_at) as first_answer,
                MAX(answered_at) as last_answer
            FROM user_answers 
            WHERE user_id = ?
        """, (user_id,))
        
        stats = basic_stats[0] if basic_stats else {
            'total_answers': 0, 'correct_answers': 0, 
            'first_answer': None, 'last_answer': None
        }
        
        # 正答率計算
        if stats['total_answers'] > 0:
            stats['accuracy_rate'] = round((stats['correct_answers'] / stats['total_answers']) * 100, 1)
        else:
            stats['accuracy_rate'] = 0
            
        # ジャンル別統計
        genre_stats = db_manager.execute_query("""
            SELECT q.genre,
                   COUNT(*) as answered,
                   SUM(CASE WHEN ua.is_correct THEN 1 ELSE 0 END) as correct
            FROM user_answers ua
            JOIN questions q ON ua.question_id = q.id
            WHERE ua.user_id = ? AND q.genre IS NOT NULL
            GROUP BY q.genre
            ORDER BY answered DESC
        """, (user_id,))
        
        stats['genre_breakdown'] = genre_stats
        
        return stats
    except Exception as e:
        print(f"Error getting detailed stats: {e}")
        return {'total_answers': 0, 'correct_answers': 0, 'accuracy_rate': 0, 'genre_breakdown': []}