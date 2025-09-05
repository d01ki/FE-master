#!/usr/bin/env python3
"""
基本情報技術者試験学習アプリ 起動スクリプト
"""

import os
from app import app
from utils.database import init_db
from utils.question_manager import QuestionManager
from utils.pdf_processor import PDFProcessor

def setup_app():
    """アプリケーションの初期設定"""
    print("基本情報技術者試験学習アプリを初期化しています...")
    
    # アップロードディレクトリの作成
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # データベースの初期化（既に存在する場合はスキップ）
    if not os.path.exists(app.config['DATABASE']):
        print("データベースを初期化しています...")
        init_db(app.config['DATABASE'])
        
        # サンプルデータの作成
        print("サンプル問題を作成しています...")
        question_manager = QuestionManager(app.config['DATABASE'])
        processor = PDFProcessor()
        sample_questions = processor.create_sample_questions()
        saved_count = question_manager.save_questions(sample_questions)
        print(f"{saved_count}問のサンプル問題を作成しました。")
    
    print("\n✅ アプリケーションの準備が完了しました!")
    print("\n🌐 ブラウザで http://localhost:5000 にアクセスしてください")
    print("\n📚 機能:")
    print("  - ランダム練習")
    print("  - ジャンル別練習")
    print("  - 模擬試験（80問・150分）")
    print("  - 学習履歴・統計")
    print("  - PDF問題集アップロード")
    print("\n⚙️ 管理画面: http://localhost:5000/admin")
    print("\n🔧 開発者: Python Flask + SQLite + Tailwind CSS")
    print("="*60)

if __name__ == '__main__':
    setup_app()
    app.run(
        debug=True, 
        host='0.0.0.0', 
        port=5000,
        threaded=True
    )
