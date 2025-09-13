"""
PostgreSQL データベース管理ユーティリティ
"""

import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from urllib.parse import urlparse

def get_db_connection(database_url):
    """PostgreSQL データベース接続を取得"""
    return psycopg2.connect(database_url)

@contextmanager
def get_db_context(database_url):
    """PostgreSQL データベース接続のコンテキストマネージャー"""
    conn = None
    try:
        conn = psycopg2.connect(database_url)
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def init_db(database_url):
    """データベースの初期化とテーブル作成"""
    try:
        with get_db_context(database_url) as conn:
            cursor = conn.cursor()
            
            # ユーザーテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 問題テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id SERIAL PRIMARY KEY,
                    question_id VARCHAR(50) UNIQUE NOT NULL,
                    question_text TEXT NOT NULL,
                    choices TEXT NOT NULL,
                    correct_answer VARCHAR(10) NOT NULL,
                    explanation TEXT,
                    genre VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ユーザー解答履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_answers (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
                    user_answer VARCHAR(10) NOT NULL,
                    is_correct BOOLEAN NOT NULL,
                    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # インデックス作成
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_answers_user_id 
                ON user_answers(user_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_answers_question_id 
                ON user_answers(question_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_questions_genre 
                ON questions(genre)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_questions_question_id 
                ON questions(question_id)
            ''')
            
            conn.commit()
            print("データベーステーブルとインデックスが正常に作成されました")
            
    except Exception as e:
        print(f"データベース初期化エラー: {e}")
        raise e

def test_connection(database_url):
    """データベース接続テスト"""
    try:
        with get_db_context(database_url) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT version()')
            version = cursor.fetchone()
            print(f"PostgreSQL接続成功: {version[0]}")
            return True
    except Exception as e:
        print(f"PostgreSQL接続エラー: {e}")
        return False
