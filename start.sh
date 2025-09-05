#!/bin/bash

# 基本情報技術者試験学習アプリ 起動スクリプト

echo "================================================"
echo "基本情報技術者試験 学習アプリ"
echo "Flask + SQLite + Tailwind CSS"
echo "================================================"
echo ""

# Python バージョンチェック
python_version=$(python3 --version 2>/dev/null || python --version 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✅ Python: $python_version"
else
    echo "❌ Python が見つかりません。Python 3.8以上をインストールしてください。"
    exit 1
fi

# 仮想環境の確認・作成
if [ ! -d "venv" ]; then
    echo "📦 仮想環境を作成しています..."
    python3 -m venv venv 2>/dev/null || python -m venv venv
fi

# 仮想環境の有効化
echo "🔧 仮想環境を有効化しています..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "❌ 仮想環境の有効化に失敗しました。"
    exit 1
fi

# 依存関係のインストール
echo "📚 依存関係をインストールしています..."
pip install -r requirements.txt --quiet

if [ $? -eq 0 ]; then
    echo "✅ 依存関係のインストールが完了しました"
else
    echo "❌ 依存関係のインストールに失敗しました。"
    exit 1
fi

echo ""
echo "✨ アプリケーションを起動しています..."
echo ""

# アプリケーション起動
python run.py

# 仮想環境を無効化
deactivate

echo ""
echo "👋 アプリケーションを終了しました。お疲れ様でした！"