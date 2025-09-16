#!/bin/bash

# FE-Master (ログイン機能付き) 起動スクリプト

set -e

echo "🚀 FE-Master (ログイン機能付き) を起動しています..."
echo "============================================="

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
    pip3 install Flask Flask-Login Werkzeug --quiet
fi

echo "✅ ライブラリのインストールが完了しました"

# app.pyの確認
if [ ! -f "app.py" ]; then
    echo "❌ app.pyが見つかりません"
    echo "正しいディレクトリでスクリプトを実行しているか確認してください"
    exit 1
fi

echo "🎓 FE-Master (ログイン機能付き) を起動中..."
echo ""
echo "🌐 アプリケーションのURL:"
echo "   ログイン画面: http://localhost:5000/login"
echo "   ダッシュボード: http://localhost:5000 (ログイン後)"
echo ""
echo "🔐 デフォルトアカウント:"
echo "   管理者: admin / admin123"
echo ""
echo "💡 新規ユーザー登録: http://localhost:5000/register"
echo ""
echo "停止するには Ctrl+C を押してください"
echo "============================================="

# 環境変数の設定 (開発環境用)
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key

# アプリケーションを起動
python3 app.py
