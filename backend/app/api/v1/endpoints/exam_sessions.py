from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.exam_session import ExamSession
from app.models.problem import Problem
from app.models.user_answer import UserAnswer
from app.schemas.exam_session import (
    ExamSessionCreate, ExamSession as ExamSessionSchema, 
    ExamSessionUpdate, ExamSessionResult
)
from datetime import datetime

router = APIRouter()

@router.post("/", response_model=ExamSessionSchema)
def create_exam_session(
    session_data: ExamSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """模擬試験セッション作成"""
    
    # 問題の存在確認
    problems = db.query(Problem).filter(Problem.id.in_(session_data.problem_ids)).all()
    if len(problems) != len(session_data.problem_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効な問題IDが含まれています"
        )
    
    # セッション作成
    exam_session = ExamSession(
        user_id=current_user.id,
        started_at=datetime.utcnow(),
        metadata_json={
            "problem_ids": session_data.problem_ids,
            "total_questions": len(session_data.problem_ids),
            **(session_data.metadata or {})
        }
    )
    
    db.add(exam_session)
    db.commit()
    db.refresh(exam_session)
    
    return exam_session

@router.get("/", response_model=List[ExamSessionSchema])
def get_exam_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 20
):
    """模擬試験セッション一覧取得"""
    sessions = db.query(ExamSession).filter(
        ExamSession.user_id == current_user.id
    ).order_by(
        ExamSession.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return sessions

@router.get("/{session_id}", response_model=ExamSessionSchema)
def get_exam_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """模擬試験セッション詳細取得"""
    session = db.query(ExamSession).filter(
        ExamSession.id == session_id,
        ExamSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模擬試験セッションが見つかりません"
        )
    
    return session

@router.put("/{session_id}", response_model=ExamSessionSchema)
def update_exam_session(
    session_id: int,
    session_update: ExamSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """模擬試験セッション更新（終了時など）"""
    session = db.query(ExamSession).filter(
        ExamSession.id == session_id,
        ExamSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模擬試験セッションが見つかりません"
        )
    
    if session_update.ended_at is not None:
        session.ended_at = session_update.ended_at
    
    if session_update.score is not None:
        session.score = session_update.score
    
    if session_update.metadata_json is not None:
        # 既存のメタデータとマージ
        current_metadata = session.metadata_json or {}
        current_metadata.update(session_update.metadata_json)
        session.metadata_json = current_metadata
    
    db.commit()
    db.refresh(session)
    
    return session

@router.get("/{session_id}/result", response_model=ExamSessionResult)
def get_exam_session_result(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """模擬試験結果取得"""
    session = db.query(ExamSession).filter(
        ExamSession.id == session_id,
        ExamSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模擬試験セッションが見つかりません"
        )
    
    if not session.metadata_json or "problem_ids" not in session.metadata_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="セッションメタデータが不正です"
        )
    
    problem_ids = session.metadata_json["problem_ids"]
    total_questions = len(problem_ids)
    
    # セッション中の解答を取得
    # セッション開始後の解答のみを対象
    answers = db.query(UserAnswer).filter(
        UserAnswer.user_id == current_user.id,
        UserAnswer.problem_id.in_(problem_ids),
        UserAnswer.answered_at >= session.started_at
    )
    
    if session.ended_at:
        answers = answers.filter(UserAnswer.answered_at <= session.ended_at)
    
    answers = answers.all()
    
    # 結果計算
    correct_answers = sum(1 for answer in answers if answer.is_correct)
    score_percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    # 総解答時間
    total_time = sum(answer.time_taken for answer in answers if answer.time_taken)
    
    # 分野別スコア
    category_stats = db.query(
        Problem.category,
        func.count(UserAnswer.id).label("total"),
        func.sum(func.cast(UserAnswer.is_correct, db.Integer)).label("correct")
    ).join(
        Problem, UserAnswer.problem_id == Problem.id
    ).filter(
        UserAnswer.user_id == current_user.id,
        UserAnswer.problem_id.in_(problem_ids),
        UserAnswer.answered_at >= session.started_at,
        Problem.category.isnot(None)
    )
    
    if session.ended_at:
        category_stats = category_stats.filter(UserAnswer.answered_at <= session.ended_at)
    
    category_stats = category_stats.group_by(Problem.category).all()
    
    category_scores = {}
    for stat in category_stats:
        if stat.total > 0:
            category_scores[stat.category] = round((stat.correct / stat.total * 100), 1)
    
    return ExamSessionResult(
        session=session,
        total_questions=total_questions,
        correct_answers=correct_answers,
        score_percentage=round(score_percentage, 1),
        time_taken=total_time,
        category_scores=category_scores
    )
