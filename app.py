#!/usr/bin/env python3
"""
FE-Master - 基本情報技術者試験 過去問学習アプリ
シンプル版: SQLite + FastAPI
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List

try:
    from fastapi import FastAPI, HTTPException, Form
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse
    import uvicorn
except ImportError as e:
    print(f"❌ 必要なライブラリがインストールされていません: {e}")
    print("以下のコマンドを実行してください:")
    print("pip install fastapi uvicorn pydantic python-multipart")
    sys.exit(1)

# アプリケーション設定
APP_NAME = "FE-Master"
APP_VERSION = "1.0.0"
DATABASE_FILE = "fe_master.db"
PORT = 8000
HOST = "0.0.0.0"

# FastAPIアプリケーション
app = FastAPI(
    title=APP_NAME,
    description="基本情報技術者試験 過去問学習アプリ",
    version=APP_VERSION
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベース初期化
def init_database():
    """データベースとサンプルデータを初期化"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # problemsテーブル作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            year INTEGER NOT NULL,
            exam_session TEXT NOT NULL,
            question_no TEXT NOT NULL,
            text_md TEXT NOT NULL,
            choices_json TEXT NOT NULL,
            answer_index INTEGER NOT NULL,
            explanation_md TEXT,
            category TEXT,
            difficulty REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, year, exam_session, question_no)
        )
    """)
    
    # user_answersテーブル作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER NOT NULL,
            selected_index INTEGER NOT NULL,
            is_correct BOOLEAN NOT NULL,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (problem_id) REFERENCES problems (id)
        )
    """)
    
    # サンプルデータの挿入
    cursor.execute("SELECT COUNT(*) FROM problems")
    if cursor.fetchone()[0] == 0:
        sample_problems = [
            {
                "source": "FE",
                "year": 2023,
                "exam_session": "autumn",
                "question_no": "Q1",
                "text_md": "# システム性能\n\nスループットに関する説明として、最も適切なものはどれか。",
                "choices_json": '{"a": "単位時間当たりに処理できるジョブ数", "b": "処理完了までの平均時間", "c": "単位時間当たりのデータ量", "d": "システムの稼働時間の割合"}',
                "answer_index": 0,
                "explanation_md": "**正解：a**\n\nスループットは単位時間当たりに処理できるジョブ数を表す性能指標です。",
                "category": "システム構成要素",
                "difficulty": 0.3
            },
            {
                "source": "FE",
                "year": 2023,
                "exam_session": "spring",
                "question_no": "Q10",
                "text_md": "# データベース\n\n関係データベースの正規化の目的として、適切なものはどれか。",
                "choices_json": '{"a": "処理速度の向上", "b": "記憶容量の削減", "c": "データの一貫性保持", "d": "検索効率の向上"}',
                "answer_index": 2,
                "explanation_md": "**正解：c**\n\n正規化の主な目的は、データの一貫性を保ち、更新異常を防ぐことです。",
                "category": "データベース",
                "difficulty": 0.4
            },
            {
                "source": "FE",
                "year": 2023,
                "exam_session": "autumn",
                "question_no": "Q25",
                "text_md": "# ネットワーク\n\nTCP/IPモデルのトランスポート層で動作するプロトコルはどれか。",
                "choices_json": '{"a": "HTTP", "b": "IP", "c": "TCP", "d": "Ethernet"}',
                "answer_index": 2,
                "explanation_md": "**正解：c**\n\nTCPはトランスポート層で動作するプロトコルです。",
                "category": "ネットワーク",
                "difficulty": 0.3
            },
            {
                "source": "FE",
                "year": 2023,
                "exam_session": "spring",
                "question_no": "Q35",
                "text_md": "# アルゴリズム\n\n最悪計算量O(n log n)を持つソートアルゴリズムはどれか。",
                "choices_json": '{"a": "バブルソート", "b": "選択ソート", "c": "マージソート", "d": "挿入ソート"}',
                "answer_index": 2,
                "explanation_md": "**正解：c**\n\nマージソートは常にO(n log n)の時間計算量を保証します。",
                "category": "アルゴリズム",
                "difficulty": 0.6
            },
            {
                "source": "FE",
                "year": 2023,
                "exam_session": "autumn",
                "question_no": "Q50",
                "text_md": "# セキュリティ\n\nファイアウォールの機能として、最も適切なものはどれか。",
                "choices_json": '{"a": "パケットの監視", "b": "データの暗号化", "c": "パケットの通過制御", "d": "ウイルスの検知"}',
                "answer_index": 2,
                "explanation_md": "**正解：c**\n\nファイアウォールの主な機能はパケットの通過を制御することです。",
                "category": "セキュリティ",
                "difficulty": 0.4
            }
        ]
        
        for problem in sample_problems:
            cursor.execute("""
                INSERT INTO problems 
                (source, year, exam_session, question_no, text_md, choices_json, 
                 answer_index, explanation_md, category, difficulty)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                problem["source"], problem["year"], problem["exam_session"],
                problem["question_no"], problem["text_md"], problem["choices_json"],
                problem["answer_index"], problem["explanation_md"],
                problem["category"], problem["difficulty"]
            ))
        
        print(f"✅ {len(sample_problems)}問のサンプルデータを挿入しました")
    
    conn.commit()
    conn.close()

# APIエンドポイント
@app.get("/", response_class=HTMLResponse)
def root():
    """メインページ"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FE-Master - 基本情報技術者試験 学習アプリ</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
            .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; }
            .feature { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .links { text-align: center; margin: 20px 0; }
            .links a { display: inline-block; margin: 5px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
            .links a:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎓 FE-Master</h1>
            <p style="text-align: center; color: #666;">基本情報技術者試験 過去問学習アプリ</p>
            
            <div class="feature">
                <h3>📚 サンプル問題</h3>
                <p>5問のサンプル問題が利用可能です：システム性能、データベース、ネットワーク、アルゴリズム、セキュリティ</p>
            </div>
            
            <div class="feature">
                <h3>📊 学習記録</h3>
                <p>解答履歴と正答率を自動で記録・分析します</p>
            </div>
            
            <div class="links">
                <a href="/docs">📖 API仕様書</a>
                <a href="/api/problems">📝 問題一覧</a>
                <a href="/api/stats">📊 統計</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/api/problems")
def get_problems(category: Optional[str] = None):
    """問題一覧を取得"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if category:
        cursor.execute("SELECT * FROM problems WHERE category = ?", (category,))
    else:
        cursor.execute("SELECT * FROM problems")
    
    problems = []
    for row in cursor.fetchall():
        problem = dict(row)
        problem['choices_json'] = json.loads(problem['choices_json'])
        problems.append(problem)
    
    conn.close()
    return {"problems": problems, "count": len(problems)}

@app.get("/api/problems/{problem_id}")
def get_problem(problem_id: int):
    """特定の問題を取得"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM problems WHERE id = ?", (problem_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="問題が見つかりません")
    
    problem = dict(row)
    problem['choices_json'] = json.loads(problem['choices_json'])
    
    conn.close()
    return problem

@app.post("/api/problems/{problem_id}/answer")
def submit_answer(problem_id: int, selected_index: int = Form(...)):
    """解答を送信"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # 問題を取得
    cursor.execute("SELECT * FROM problems WHERE id = ?", (problem_id,))
    problem_row = cursor.fetchone()
    
    if not problem_row:
        conn.close()
        raise HTTPException(status_code=404, detail="問題が見つかりません")
    
    is_correct = selected_index == problem_row[6]  # answer_index
    
    # 解答を記録
    cursor.execute(
        "INSERT INTO user_answers (problem_id, selected_index, is_correct) VALUES (?, ?, ?)",
        (problem_id, selected_index, is_correct)
    )
    
    conn.commit()
    answer_id = cursor.lastrowid
    conn.close()
    
    return {
        "answer_id": answer_id,
        "is_correct": is_correct,
        "correct_answer_index": problem_row[6],
        "explanation": problem_row[8] if len(problem_row) > 8 else ""
    }

@app.get("/api/stats")
def get_stats():
    """統計情報を取得"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # 基本統計
    cursor.execute("SELECT COUNT(*) FROM problems")
    total_problems = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM user_answers")
    total_answers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM user_answers WHERE is_correct = 1")
    correct_answers = cursor.fetchone()[0]
    
    accuracy_rate = (correct_answers / total_answers * 100) if total_answers > 0 else 0
    
    conn.close()
    
    return {
        "total_problems": total_problems,
        "total_answers": total_answers,
        "correct_answers": correct_answers,
        "accuracy_rate": round(accuracy_rate, 1)
    }

@app.get("/api/categories")
def get_categories():
    """カテゴリ一覧を取得"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT category FROM problems WHERE category IS NOT NULL")
    categories = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return {"categories": categories}

def main():
    """メイン関数"""
    print(f"🚀 {APP_NAME} v{APP_VERSION} を起動中...")
    
    # データベース初期化
    init_database()
    
    print(f"🌐 サーバー: http://{HOST}:{PORT}")
    print(f"📖 API仕様書: http://{HOST}:{PORT}/docs")
    print("\n停止するには Ctrl+C を押してください")
    print("=" * 50)
    
    try:
        uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    except KeyboardInterrupt:
        print("\n👋 アプリケーションを停止しました")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
