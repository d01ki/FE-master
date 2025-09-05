#!/bin/bash

# FE-Master 簡単起動スクリプト

set -e

echo "🚀 FE-Master を起動しています..."
echo "=============================="

# Pythonの確認
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3がインストールされていません"
    echo "以下のコマンドでPython3をインストールしてください:"
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "macOS: brew install python3"
    exit 1
fi

echo "✅ Python3が見つかりました"

# pipの確認と更新
echo "📦 pipを更新中..."
pip3 install --upgrade pip --quiet

# 依存ライブラリのインストール
echo "📦 必要なライブラリをインストール中..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --quiet
else
    echo "⚠️  requirements.txtが見つかりません。基本ライブラリをインストールします..."
    pip3 install fastapi uvicorn pydantic python-multipart requests --quiet
fi

echo "✅ ライブラリのインストールが完了しました"

# app.pyの確認
if [ ! -f "app.py" ]; then
    echo "❌ app.pyが見つかりません"
    echo "正しいディレクトリでスクリプトを実行しているか確認してください"
    exit 1
fi

echo "🎓 FE-Masterを起動中..."
echo ""
echo "🌐 アプリケーションのURL:"
echo "   メインページ: http://localhost:8000"
echo "   APIドキュメント: http://localhost:8000/docs"
echo ""
echo "停止するには Ctrl+C を押してください"
echo "=============================="

# アプリケーションを起動
python3 app.py
