from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# SQLAlchemy設定
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# データベース依存性
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# テーブル作成
async def create_tables():
    """データベーステーブルとpgvector拡張を作成"""
    # pgvector拡張を有効化
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
    except Exception as e:
        print(f"pgvector拡張の作成に失敗: {e}")
    
    # テーブル作成
    Base.metadata.create_all(bind=engine)
