from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import engine, create_tables

# アプリケーション初期化
def create_application() -> FastAPI:
    app = FastAPI(
        title="FE-Master API",
        description="基本情報技術者過去問学習アプリ API",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # CORS設定
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # APIルーター追加
    app.include_router(api_router, prefix="/api/v1")

    return app

app = create_application()

@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    await create_tables()

@app.get("/")
def root():
    """ヘルスチェック"""
    return {"message": "FE-Master API is running"}

@app.get("/health")
def health_check():
    """ヘルスチェック詳細"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }
