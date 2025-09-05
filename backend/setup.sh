#!/bin/bash

# FE-Master バックエンドセットアップスクリプト

set -e  # エラーで停止

echo "=== FE-Master Backend Setup ==="

# 仮想環境の確認
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  仮想環境が有効になっていません"
    echo "以下のコマンドを実行してから再度お試しください："
    echo "cd ~/FE-master"
    echo "source venv/bin/activate"
    exit 1
fi

echo "✅ 仮想環境が有効です: $VIRTUAL_ENV"

# 依存関係のインストール
echo "📦 依存関係をインストール中..."
pip install --upgrade pip
pip install -r requirements.txt

# .envファイルの確認
if [ ! -f ".env" ]; then
    echo "📝 .envファイルを作成中..."
    cp .env.example .env
    echo "⚠️  .envファイルを編集してデータベース接続情報を設定してください"
else
    echo "✅ .envファイルが見つかりました"
fi

# PostgreSQLの確認
echo "🔍 PostgreSQLの確認中..."
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQLがインストールされていません"
    echo "以下のコマンドでインストールしてください："
    echo "sudo apt update && sudo apt install postgresql postgresql-contrib"
    exit 1
fi

echo "✅ PostgreSQLが見つかりました"

# データベース接続テスト
echo "🔗 データベース接続をテスト中..."
python -c "
from app.core.database import engine
try:
    with engine.connect() as conn:
        print('✅ データベース接続成功')
except Exception as e:
    print(f'❌ データベース接続失敗: {e}')
    print('以下を確認してください：')
    print('1. PostgreSQLが起動しているか: sudo systemctl status postgresql')
    print('2. データベースとユーザーが作成されているか')
    print('3. .envファイルの接続情報が正しいか')
    exit(1)
"

# Alembicの初期化（必要な場合）
if [ ! -d "alembic/versions" ] || [ -z "$(ls -A alembic/versions)" ]; then
    echo "🔄 データベーススキーマを初期化中..."
    alembic revision --autogenerate -m "Initial migration"
fi

# マイグレーションの実行
echo "🔄 データベースマイグレーションを実行中..."
alembic upgrade head

# pgvector拡張の確認
echo "🔍 pgvector拡張を確認中..."
python -c "
from app.core.database import engine
from sqlalchemy import text
try:
    with engine.connect() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))
        conn.commit()
        print('✅ pgvector拡張が有効です')
except Exception as e:
    print(f'⚠️  pgvector拡張の確認中にエラー: {e}')
"

# サンプルデータの投入
echo "📊 サンプルデータを投入中..."
python scripts/sample_data.py

echo ""
echo "🎉 セットアップ完了！"
echo ""
echo "次のステップ："
echo "1. サーバーを起動: uvicorn app.main:app --reload"
echo "2. ブラウザで http://localhost:8000/docs にアクセス"
echo "3. テストユーザーでログイン: test@example.com / password123"
echo ""
