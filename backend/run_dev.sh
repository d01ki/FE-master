#!/bin/bash

# 開発サーバー起動スクリプト

set -e

echo "=== FE-Master 開発サーバー起動 ==="

# 仮想環境の確認
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  仮想環境が有効になっていません"
    echo "以下のコマンドを実行してください："
    echo "cd ~/FE-master"
    echo "source venv/bin/activate"
    exit 1
fi

# .envファイルの確認
if [ ! -f ".env" ]; then
    echo "❌ .envファイルが見つかりません"
    echo "./setup.sh を先に実行してください"
    exit 1
fi

# データベース接続確認
echo "🔗 データベース接続を確認中..."
python -c "from app.core.database import engine; engine.connect().close(); print('✅ データベース接続OK')"

echo "🚀 FastAPIサーバーを起動中..."
echo "📖 API仕様書: http://localhost:8000/docs"
echo "🏥 ヘルスチェック: http://localhost:8000/health"
echo ""
echo "停止するには Ctrl+C を押してください"
echo ""

# サーバー起動
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
