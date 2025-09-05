from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List

class ExamSessionBase(BaseModel):
    started_at: datetime
    ended_at: Optional[datetime] = None
    metadata_json: Optional[Dict[str, Any]] = None

class ExamSessionCreate(BaseModel):
    problem_ids: List[int]
    metadata: Optional[Dict[str, Any]] = None

class ExamSessionUpdate(BaseModel):
    ended_at: Optional[datetime] = None
    score: Optional[float] = None
    metadata_json: Optional[Dict[str, Any]] = None

class ExamSessionInDB(ExamSessionBase):
    id: int
    user_id: int
    score: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ExamSession(ExamSessionInDB):
    pass

class ExamSessionResult(BaseModel):
    """模擬試験結果"""
    session: ExamSession
    total_questions: int
    correct_answers: int
    score_percentage: float
    time_taken: Optional[float] = None
    category_scores: Dict[str, float] = {}
