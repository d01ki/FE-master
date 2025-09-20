"""
ランキング・達成度ルート
"""

from flask import Blueprint, render_template, jsonify, session, redirect, url_for, request, flash
from functools import wraps
import logging

logger = logging.getLogger(__name__)

ranking_bp = Blueprint('ranking', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@ranking_bp.route('/ranking')
@login_required
def ranking_page():
    """ランキングページ"""
    try:
        from flask import current_app
        from ranking_system import RankingSystem
        
        db_manager = current_app.db_manager
        ranking_system = RankingSystem(db_manager)
        
        # ランキングを取得（管理者除外）
        rankings = ranking_system.get_ranking(limit=100, exclude_admin=True)
        
        # 現在のユーザーの情報
        user_id = session.get('user_id')
        user_stats = ranking_system.get_user_statistics(user_id)
        
        return render_template(
            'ranking.html',
            rankings=rankings,
            user_stats=user_stats,
            current_user_id=user_id
        )
        
    except Exception as e:
        logger.error(f"ランキングページエラー: {e}")
        flash('ランキングの取得に失敗しました', 'error')
        return redirect(url_for('main.dashboard'))

@ranking_bp.route('/api/ranking/user/<int:user_id>')
@login_required
def get_user_ranking(user_id):
    """ユーザーのランキング情報をAPI経由で取得"""
    try:
        from flask import current_app
        from ranking_system import RankingSystem
        
        db_manager = current_app.db_manager
        ranking_system = RankingSystem(db_manager)
        
        stats = ranking_system.get_user_statistics(user_id)
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"ユーザーランキング取得エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ranking_bp.route('/achievement')
@login_required
def achievement_page():
    """達成度ページ（網羅表）"""
    try:
        from flask import current_app
        from achievement_system import AchievementSystem
        
        db_manager = current_app.db_manager
        achievement_system = AchievementSystem(db_manager)
        
        user_id = session.get('user_id')
        
        # 網羅度データを取得
        coverage_data = achievement_system.get_mock_exam_coverage(user_id)
        
        # 進捗状況を取得
        progress_data = achievement_system.get_achievement_progress(user_id)
        
        return render_template(
            'achievement.html',
            coverage_map=coverage_data['coverage_map'],
            summary=coverage_data['summary'],
            progress=progress_data
        )
        
    except Exception as e:
        logger.error(f"達成度ページエラー: {e}")
        flash('達成度の取得に失敗しました', 'error')
        return redirect(url_for('main.dashboard'))

@ranking_bp.route('/achievement/review/<achievement_level>')
@login_required
def achievement_review(achievement_level):
    """達成度別の問題復習ページ"""
    try:
        from flask import current_app
        from achievement_system import AchievementSystem
        
        # レベルの検証
        if achievement_level not in ['gold', 'silver', 'bronze']:
            flash('無効な達成度レベルです', 'error')
            return redirect(url_for('ranking.achievement_page'))
        
        db_manager = current_app.db_manager
        achievement_system = AchievementSystem(db_manager)
        
        user_id = session.get('user_id')
        
        # 指定された達成度の問題を取得
        questions = achievement_system.get_questions_by_achievement(user_id, achievement_level)
        
        # レベル情報
        level_info = AchievementSystem.ACHIEVEMENT_LEVELS[achievement_level]
        
        return render_template(
            'achievement_review.html',
            questions=questions,
            achievement_level=achievement_level,
            level_info=level_info
        )
        
    except Exception as e:
        logger.error(f"達成度別復習エラー: {e}")
        flash('問題の取得に失敗しました', 'error')
        return redirect(url_for('ranking.achievement_page'))

@ranking_bp.route('/achievement/practice/<int:question_id>')
@login_required
def achievement_practice(question_id):
    """達成度から問題演習を開始"""
    try:
        from flask import current_app
        
        db_manager = current_app.db_manager
        
        # 問題が存在するか確認
        if db_manager.db_type == 'postgresql':
            question = db_manager.execute_query(
                "SELECT * FROM questions WHERE id = %s",
                (question_id,)
            )
        else:
            question = db_manager.execute_query(
                "SELECT * FROM questions WHERE id = ?",
                (question_id,)
            )
        
        if not question:
            flash('問題が見つかりません', 'error')
            return redirect(url_for('ranking.achievement_page'))
        
        # セッションに問題IDを保存
        session['current_question_id'] = question_id
        session['practice_mode'] = 'achievement'
        
        # 問題演習ページにリダイレクト
        return redirect(url_for('practice.random_practice'))
        
    except Exception as e:
        logger.error(f"問題演習開始エラー: {e}")
        flash('問題の読み込みに失敗しました', 'error')
        return redirect(url_for('ranking.achievement_page'))

@ranking_bp.route('/api/achievement/coverage')
@login_required
def get_achievement_coverage():
    """達成度網羅表データをAPI経由で取得"""
    try:
        from flask import current_app
        from achievement_system import AchievementSystem
        
        db_manager = current_app.db_manager
        achievement_system = AchievementSystem(db_manager)
        
        user_id = session.get('user_id')
        coverage_data = achievement_system.get_mock_exam_coverage(user_id)
        
        return jsonify({
            'success': True,
            'data': coverage_data
        })
        
    except Exception as e:
        logger.error(f"網羅度データ取得エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
