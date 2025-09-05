"""
データベース関連のユーティリティ
SQLiteデータベースの初期化と接続管理
"""

import sqlite3
import os
from contextlib import contextmanager

def init_db(db_path):
    """データベースの初期化とテーブル作成"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # 問題テーブル
    conn.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id TEXT UNIQUE NOT NULL,
            question_text TEXT NOT NULL,
            choices TEXT NOT NULL,  -- JSON形式で選択肢を保存
            correct_answer TEXT NOT NULL,
            explanation TEXT,
            genre TEXT,
            difficulty INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ユーザー解答履歴テーブル
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            user_answer TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
    ''')
    
    # インデックス作成
    conn.execute('CREATE INDEX IF NOT EXISTS idx_questions_genre ON questions(genre)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_user_answers_question_id ON user_answers(question_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_user_answers_answered_at ON user_answers(answered_at)')
    
    conn.commit()
    conn.close()
    
    print(f"データベース '{db_path}' を初期化しました")

@contextmanager
def get_db_connection(db_path):
    """データベース接続のコンテキストマネージャー"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_db_stats(db_path):
    """データベースの統計情報を取得"""
    with get_db_connection(db_path) as conn:
        stats = {
            'questions_count': conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0],
            'answers_count': conn.execute('SELECT COUNT(*) FROM user_answers').fetchone()[0],
            'correct_answers': conn.execute('SELECT COUNT(*) FROM user_answers WHERE is_correct = 1').fetchone()[0]
        }
        
        # ジャンル別統計
        genres = conn.execute('SELECT DISTINCT genre FROM questions WHERE genre IS NOT NULL').fetchall()
        stats['genres'] = [row[0] for row in genres]
        
        return stats
