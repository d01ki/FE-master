from pydantic import BaseModel
from typing import Dict, List
from datetime import datetime

class StudyStats(BaseModel):
    """学習統計"""
    total_problems_attempted: int
    total_correct: int
    accuracy_rate: float
    total_study_time: float  # 秒
    problems_today: int
    streak_days: int

class CategoryScore(BaseModel):
    """分野別スコア"""
    category: str
    total_attempted: int
    correct_count: int
    accuracy_rate: float
    avg_time: float

class RecentActivity(BaseModel):
    """最近のアクティビティ"""
    date: datetime
    problems_solved: int
    accuracy_rate: float
    study_time: float

class Dashboard(BaseModel):
    """ダッシュボードデータ"""
    stats: StudyStats
    category_scores: List[CategoryScore]
    recent_activities: List[RecentActivity]
    recommended_categories: List[str]
