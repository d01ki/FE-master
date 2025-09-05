from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.user_answer import UserAnswer
from app.models.problem import Problem
from app.schemas.dashboard import Dashboard, StudyStats, CategoryScore, RecentActivity
from datetime import datetime, timedelta
from typing import List

router = APIRouter()

@router.get("/", response_model=Dashboard)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """ダッシュボードデータ取得"""
    
    # 基本統計取得
    total_answers = db.query(UserAnswer).filter(UserAnswer.user_id == current_user.id).count()
    correct_answers = db.query(UserAnswer).filter(
        UserAnswer.user_id == current_user.id,
        UserAnswer.is_correct == True
    ).count()
    
    accuracy_rate = (correct_answers / total_answers * 100) if total_answers > 0 else 0
    
    # 今日の問題数
    today = datetime.utcnow().date()
    problems_today = db.query(UserAnswer).filter(
        UserAnswer.user_id == current_user.id,
        func.date(UserAnswer.answered_at) == today
    ).count()
    
    # 総学習時間
    total_time_result = db.query(func.sum(UserAnswer.time_taken)).filter(
        UserAnswer.user_id == current_user.id,
        UserAnswer.time_taken.isnot(None)
    ).scalar()
    total_study_time = total_time_result or 0
    
    # 基本統計
    stats = StudyStats(
        total_problems_attempted=total_answers,
        total_correct=correct_answers,
        accuracy_rate=round(accuracy_rate, 1),
        total_study_time=total_study_time,
        problems_today=problems_today,
        streak_days=0  # TODO: 連続日数の計算ロジックを実装
    )
    
    # 分野別スコア
    category_stats = db.query(
        Problem.category,
        func.count(UserAnswer.id).label("total_attempted"),
        func.sum(func.cast(UserAnswer.is_correct, db.Integer)).label("correct_count"),
        func.avg(UserAnswer.time_taken).label("avg_time")
    ).join(
        Problem, UserAnswer.problem_id == Problem.id
    ).filter(
        UserAnswer.user_id == current_user.id,
        Problem.category.isnot(None)
    ).group_by(Problem.category).all()
    
    category_scores = []
    for stat in category_stats:
        if stat.total_attempted > 0:
            accuracy = (stat.correct_count / stat.total_attempted * 100) if stat.correct_count else 0
            category_scores.append(CategoryScore(
                category=stat.category,
                total_attempted=stat.total_attempted,
                correct_count=stat.correct_count or 0,
                accuracy_rate=round(accuracy, 1),
                avg_time=round(stat.avg_time or 0, 1)
            ))
    
    # 最近のアクティビティ（7日間）
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_stats = db.query(
        func.date(UserAnswer.answered_at).label("date"),
        func.count(UserAnswer.id).label("problems_solved"),
        func.avg(func.cast(UserAnswer.is_correct, db.Integer)).label("accuracy"),
        func.sum(UserAnswer.time_taken).label("study_time")
    ).filter(
        UserAnswer.user_id == current_user.id,
        UserAnswer.answered_at >= seven_days_ago
    ).group_by(func.date(UserAnswer.answered_at)).all()
    
    recent_activities = []
    for stat in recent_stats:
        recent_activities.append(RecentActivity(
            date=datetime.combine(stat.date, datetime.min.time()),
            problems_solved=stat.problems_solved,
            accuracy_rate=round((stat.accuracy or 0) * 100, 1),
            study_time=stat.study_time or 0
        ))
    
    # 推奨カテゴリ（正答率が低い順）
    recommended_categories = []
    for score in sorted(category_scores, key=lambda x: x.accuracy_rate)[:3]:
        recommended_categories.append(score.category)
    
    return Dashboard(
        stats=stats,
        category_scores=category_scores,
        recent_activities=recent_activities,
        recommended_categories=recommended_categories
    )
