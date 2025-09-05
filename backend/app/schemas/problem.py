from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

class ProblemBase(BaseModel):
    source: str
    year: int
    exam_session: str
    question_no: str
    text_md: str
    choices_json: Dict[str, Any]
    answer_index: int
    explanation_md: Optional[str] = None
    tags: Optional[List[str]] = None
    difficulty: Optional[float] = 0.5
    category: Optional[str] = None

class ProblemCreate(ProblemBase):
    pass

class ProblemUpdate(BaseModel):
    text_md: Optional[str] = None
    choices_json: Optional[Dict[str, Any]] = None
    answer_index: Optional[int] = None
    explanation_md: Optional[str] = None
    tags: Optional[List[str]] = None
    difficulty: Optional[float] = None
    category: Optional[str] = None

class ProblemInDB(ProblemBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class Problem(ProblemInDB):
    pass

class ProblemSummary(BaseModel):
    """問題一覧表示用の簡略版"""
    id: int
    source: str
    year: int
    exam_session: str
    question_no: str
    category: Optional[str] = None
    difficulty: Optional[float] = None
    tags: Optional[List[str]] = None
    
    class Config:
        from_attributes = True

class SimilarProblem(BaseModel):
    """類似問題レスポンス"""
    problem: ProblemSummary
    similarity_score: float
