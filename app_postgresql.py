# PostgreSQL環境で動作するためのアプリケーション設定
import os
import psycopg2
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import json
import sqlite3
import logging
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fe-exam-app-secret-key-change-in-production')

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # PostgreSQL設定（Render用）
    app.config['DATABASE_TYPE'] = 'postgresql'
    app.config['DATABASE_URL'] = DATABASE_URL
    print("Using PostgreSQL database")
else:
    # SQLite設定（開発用）
    app.config['DATABASE_TYPE'] = 'sqlite'
    app.config['DATABASE'] = 'fe_exam.db'
    print("Using SQLite database")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """データベース操作を管理するクラス"""
    
    def __init__(self):
        self.db_type = app.config['DATABASE_TYPE']
        
    def get_connection(self):
        """データベース接続を取得"""
        if self.db_type == 'postgresql':
            conn = psycopg2.connect(app.config['DATABASE_URL'])
            conn.autocommit = False
            return conn
        else:
            conn = sqlite3.connect(app.config['DATABASE'])
            conn.row_factory = sqlite3.Row
            return conn
    
    def execute_query(self, query, params=None):
        """クエリを実行して結果を返す"""
        conn = self.get_connection()
        try:
            if self.db_type == 'postgresql':
                cur = conn.cursor()
                cur.execute(query, params or ())
                if query.strip().upper().startswith(('SELECT', 'WITH')):
                    result = cur.fetchall()
                    # PostgreSQLの結果をdictに変換
                    columns = [desc[0] for desc in cur.description]
                    result = [dict(zip(columns, row)) for row in result]
                else:
                    result = cur.rowcount
                    conn.commit()
                cur.close()
            else:
                cur = conn.cursor()
                cur.execute(query, params or ())
                if query.strip().upper().startswith(('SELECT', 'WITH')):
                    result = [dict(row) for row in cur.fetchall()]
                else:
                    result = cur.rowcount
                    conn.commit()
                cur.close()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_database(self):
        """データベースを初期化"""
        if self.db_type == 'postgresql':
            self._init_postgresql()
        else:
            self._init_sqlite()
    
    def _init_postgresql(self):
        """PostgreSQL用のテーブル作成"""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                question_id VARCHAR(50) UNIQUE NOT NULL,
                question_text TEXT NOT NULL,
                choices JSON NOT NULL,
                correct_answer VARCHAR(10) NOT NULL,
                explanation TEXT,
                genre VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_answers (
                id SERIAL PRIMARY KEY,
                question_id INTEGER REFERENCES questions(id),
                user_answer VARCHAR(10) NOT NULL,
                is_correct BOOLEAN NOT NULL,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_questions_genre ON questions(genre)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_user_answers_question_id ON user_answers(question_id)
            """
        ]
        
        for query in queries:
            try:
                self.execute_query(query)
                logger.info("PostgreSQL table created/updated successfully")
            except Exception as e:
                logger.error(f"Error creating PostgreSQL table: {e}")
    
    def _init_sqlite(self):
        """SQLite用のテーブル作成"""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id TEXT UNIQUE NOT NULL,
                question_text TEXT NOT NULL,
                choices TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                explanation TEXT,
                genre TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER,
                user_answer TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                answered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_id) REFERENCES questions (id)
            )
            """
        ]
        
        for query in queries:
            try:
                self.execute_query(query)
                logger.info("SQLite table created/updated successfully")
            except Exception as e:
                logger.error(f"Error creating SQLite table: {e}")

# データベースマネージャーのインスタンス化
db_manager = DatabaseManager()

class QuestionManager:
    """問題管理クラス"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def save_questions(self, questions, source_file=''):
        """問題をデータベースに保存"""
        if not isinstance(questions, list):
            raise ValueError("Questions must be a list")
        
        saved_count = 0
        errors = []
        
        for i, question in enumerate(questions):
            try:
                # 必須フィールドの検証
                required_fields = ['question_text', 'choices', 'correct_answer']
                missing_fields = [field for field in required_fields if field not in question]
                if missing_fields:
                    errors.append(f"Question {i+1}: Missing fields {missing_fields}")
                    continue
                
                # question_idの自動生成
                question_id = question.get('question_id', f"Q{i+1:03d}_{source_file}")
                
                # choicesの処理
                if self.db.db_type == 'postgresql':
                    choices_data = json.dumps(question['choices'], ensure_ascii=False)
                else:
                    choices_data = json.dumps(question['choices'], ensure_ascii=False)
                
                # 重複チェック
                existing = self.db.execute_query(
                    'SELECT id FROM questions WHERE question_id = %s' if self.db.db_type == 'postgresql' else 'SELECT id FROM questions WHERE question_id = ?',
                    (question_id,)
                )
                
                if existing:
                    # 更新
                    if self.db.db_type == 'postgresql':
                        self.db.execute_query("""
                            UPDATE questions 
                            SET question_text = %s, choices = %s, correct_answer = %s, 
                                explanation = %s, genre = %s
                            WHERE question_id = %s
                        """, (
                            question['question_text'],
                            choices_data,
                            question['correct_answer'],
                            question.get('explanation', ''),
                            question.get('genre', 'その他'),
                            question_id
                        ))
                    else:
                        self.db.execute_query("""
                            UPDATE questions 
                            SET question_text = ?, choices = ?, correct_answer = ?, 
                                explanation = ?, genre = ?
                            WHERE question_id = ?
                        """, (
                            question['question_text'],
                            choices_data,
                            question['correct_answer'],
                            question.get('explanation', ''),
                            question.get('genre', 'その他'),
                            question_id
                        ))
                else:
                    # 新規追加
                    if self.db.db_type == 'postgresql':
                        self.db.execute_query("""
                            INSERT INTO questions 
                            (question_id, question_text, choices, correct_answer, explanation, genre) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            question_id,
                            question['question_text'],
                            choices_data,
                            question['correct_answer'],
                            question.get('explanation', ''),
                            question.get('genre', 'その他')
                        ))
                    else:
                        self.db.execute_query("""
                            INSERT INTO questions 
                            (question_id, question_text, choices, correct_answer, explanation, genre) 
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            question_id,
                            question['question_text'],
                            choices_data,
                            question['correct_answer'],
                            question.get('explanation', ''),
                            question.get('genre', 'その他')
                        ))
                
                saved_count += 1
                
            except Exception as e:
                errors.append(f"Question {i+1}: {str(e)}")
                logger.error(f"Error saving question {i+1}: {e}")
        
        return {
            'saved_count': saved_count,
            'total_count': len(questions),
            'errors': errors
        }
    
    def load_json_files(self):
        """JSONファイルを自動読み込み"""
        json_folder = 'json_questions'
        if not os.path.exists(json_folder):
            logger.warning(f"JSON folder not found: {json_folder}")
            return {'total_files': 0, 'total_questions': 0, 'errors': []}
        
        total_files = 0
        total_questions = 0
        errors = []
        
        for filename in os.listdir(json_folder):
            if filename.endswith('.json'):
                filepath = os.path.join(json_folder, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        questions = json.load(f)
                    
                    result = self.save_questions(questions, filename)
                    total_files += 1
                    total_questions += result['saved_count']
                    
                    if result['errors']:
                        errors.extend([f"{filename}: {error}" for error in result['errors']])
                    
                    logger.info(f"Loaded {result['saved_count']} questions from {filename}")
                    
                except Exception as e:
                    errors.append(f"{filename}: {str(e)}")
                    logger.error(f"Error loading {filename}: {e}")
        
        return {
            'total_files': total_files,
            'total_questions': total_questions,
            'errors': errors
        }

# 問題マネージャーのインスタンス化
question_manager = QuestionManager(db_manager)

# アプリケーション初期化
@app.before_first_request
def initialize_app():
    """アプリケーション初期化"""
    try:
        # データベース初期化
        db_manager.init_database()
        logger.info("Database initialized successfully")
        
        # JSONファイル自動読み込み
        result = question_manager.load_json_files()
        logger.info(f"Auto-loaded {result['total_questions']} questions from {result['total_files']} files")
        
        if result['errors']:
            for error in result['errors']:
                logger.warning(f"JSON loading warning: {error}")
                
    except Exception as e:
        logger.error(f"Application initialization error: {e}")

# 以下、ルート定義は既存のapp.pyと同じ...

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
