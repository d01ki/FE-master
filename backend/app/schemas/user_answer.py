from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserAnswerBase(BaseModel):
    problem_id: int
    selected_index: int
    time_taken: Optional[float] = None

class UserAnswerCreate(UserAnswerBase):
    pass

class UserAnswerInDB(UserAnswerBase):
    id: int
    user_id: int
    is_correct: bool
    answered_at: datetime
    
    class Config:
        from_attributes = True

class UserAnswer(UserAnswerInDB):
    pass

class AnswerResult(BaseModel):
    """解答結果レスポンス"""
    is_correct: bool
    correct_answer_index: int
    explanation: Optional[str] = None
    user_answer_id: int
