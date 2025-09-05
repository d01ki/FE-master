from fastapi import APIRouter
from app.api.v1.endpoints import auth, problems, users, dashboard, exam_sessions

api_router = APIRouter()

# 各エンドポイントを登録
api_router.include_router(auth.router, prefix="/auth", tags=["認証"])
api_router.include_router(users.router, prefix="/users", tags=["ユーザー"])
api_router.include_router(problems.router, prefix="/problems", tags=["問題"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["ダッシュボード"])
api_router.include_router(exam_sessions.router, prefix="/exam-sessions", tags=["模擬試験"])
