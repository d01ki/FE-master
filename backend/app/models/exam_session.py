from sqlalchemy import Column, Integer, DateTime, ForeignKey, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class ExamSession(Base):
    __tablename__ = "exam_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True))
    score = Column(Float)  # スコア（百分率）
    
    # メタデータ（問題ID、解答時間等）
    metadata_json = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーション
    user = relationship("User", back_populates="exam_sessions")
