from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.problem import Problem
from app.schemas.problem import SimilarProblem, ProblemSummary

def get_similar_problems(db: Session, problem_id: int, limit: int = 5) -> List[SimilarProblem]:
    """類似問題を取得する（pgvector使用）"""
    
    # 対象問題の取得
    target_problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not target_problem or not target_problem.embedding:
        return []
    
    # pgvectorを使用した類似性検索
    # コサイン類似度でソート
    query = text("""
        SELECT p.*, (1 - (p.embedding <=> :target_embedding)) as similarity_score
        FROM problems p
        WHERE p.id != :problem_id 
          AND p.embedding IS NOT NULL
        ORDER BY p.embedding <=> :target_embedding
        LIMIT :limit
    """)
    
    result = db.execute(
        query,
        {
            "target_embedding": str(target_problem.embedding),
            "problem_id": problem_id,
            "limit": limit
        }
    ).fetchall()
    
    similar_problems = []
    for row in result:
        problem_summary = ProblemSummary(
            id=row.id,
            source=row.source,
            year=row.year,
            exam_session=row.exam_session,
            question_no=row.question_no,
            category=row.category,
            difficulty=row.difficulty,
            tags=row.tags
        )
        
        similar_problems.append(SimilarProblem(
            problem=problem_summary,
            similarity_score=round(row.similarity_score, 3)
        ))
    
    return similar_problems

def generate_embedding(text: str) -> List[float]:
    """テキストから埋め込みを生成（OpenAI API使用）"""
    import openai
    from app.core.config import settings
    
    if not settings.OPENAI_API_KEY:
        raise ValueError("OpenAI APIキーが設定されていません")
    
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    try:
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"埋め込み生成エラー: {e}")
        return []

def update_problem_embedding(db: Session, problem: Problem):
    """問題の埋め込みを更新"""
    # 問題文、選択肢、解説を結合してテキスト作成
    text_parts = [problem.text_md]
    
    if problem.choices_json and isinstance(problem.choices_json, dict):
        for key, value in problem.choices_json.items():
            text_parts.append(f"{key}: {value}")
    
    if problem.explanation_md:
        text_parts.append(problem.explanation_md)
    
    combined_text = "\n".join(text_parts)
    
    # 埋め込み生成
    embedding = generate_embedding(combined_text)
    
    if embedding:
        problem.embedding = embedding
        db.commit()
        return True
    
    return False
