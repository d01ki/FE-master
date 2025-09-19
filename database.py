import os
import sqlite3
import json
import logging

# PostgreSQLライブラリのインポート（エラー時はSQLiteのみ使用）
try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("Warning: psycopg2 not available. PostgreSQL support disabled.")

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, config):
        self.db_type = config['DATABASE_TYPE']
        self.config = config
        
        # PostgreSQLが利用できない場合はSQLiteにフォールバック
        if self.db_type == 'postgresql' and not PSYCOPG2_AVAILABLE:
            print("PostgreSQL requested but psycopg2 not available. Falling back to SQLite.")
            self.db_type = 'sqlite'
            config['DATABASE_TYPE'] = 'sqlite'
        
    def get_connection(self):
        if self.db_type == 'postgresql' and PSYCOPG2_AVAILABLE:
            conn = psycopg2.connect(self.config['DATABASE_URL'])
            conn.autocommit = False
            return conn
        else:
            conn = sqlite3.connect(self.config['DATABASE'])
            conn.row_factory = sqlite3.Row
            return conn
    
    def execute_query(self, query, params=None):
        conn = self.get_connection()
        try:
            if self.db_type == 'postgresql' and PSYCOPG2_AVAILABLE:
                cur = conn.cursor()
                cur.execute(query, params or ())
                if query.strip().upper().startswith(('SELECT', 'WITH')):
                    result = cur.fetchall()
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
        if self.db_type == 'postgresql' and PSYCOPG2_AVAILABLE:
            self._init_postgresql()
        else:
            self._init_sqlite()
    
    def _init_postgresql(self):
        queries = [
            """CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                question_id VARCHAR(50) UNIQUE NOT NULL,
                question_text TEXT NOT NULL,
                choices JSON NOT NULL,
                correct_answer VARCHAR(10) NOT NULL,
                explanation TEXT,
                genre VARCHAR(100),
                image_url VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS user_answers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                question_id INTEGER REFERENCES questions(id),
                user_answer VARCHAR(10) NOT NULL,
                is_correct BOOLEAN NOT NULL,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS idx_questions_genre ON questions(genre)",
            "CREATE INDEX IF NOT EXISTS idx_user_answers_user_id ON user_answers(user_id)",
            # 既存のテーブルにimage_urlカラムを追加（存在しない場合のみ）
            """DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='questions' AND column_name='image_url') THEN
                    ALTER TABLE questions ADD COLUMN image_url VARCHAR(500);
                END IF;
            END $$;"""
        ]
        
        for query in queries:
            try:
                self.execute_query(query)
            except Exception as e:
                logger.error(f"PostgreSQL init error: {e}")
    
    def _init_sqlite(self):
        queries = [
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id TEXT UNIQUE NOT NULL,
                question_text TEXT NOT NULL,
                choices TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                explanation TEXT,
                genre TEXT,
                image_url TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS user_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_id INTEGER,
                user_answer TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                answered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (question_id) REFERENCES questions (id)
            )"""
        ]
        
        for query in queries:
            try:
                self.execute_query(query)
            except Exception as e:
                logger.error(f"SQLite init error: {e}")
        
        # 既存のテーブルにimage_urlカラムを追加（存在しない場合のみ）
        try:
            self.execute_query("""
                SELECT sql FROM sqlite_master WHERE type='table' AND name='questions'
            """)
            # カラムが存在するかチェック
            table_info = self.execute_query("PRAGMA table_info(questions)")
            column_names = [col['name'] for col in table_info]
            
            if 'image_url' not in column_names:
                self.execute_query("ALTER TABLE questions ADD COLUMN image_url TEXT")
                logger.info("Added image_url column to questions table")
        except Exception as e:
            logger.error(f"SQLite alter table error: {e}")

class QuestionManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def load_json_files(self):
        json_folder = 'json_questions'
        if not os.path.exists(json_folder):
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
                    
                except Exception as e:
                    errors.append(f"{filename}: {str(e)}")
        
        return {'total_files': total_files, 'total_questions': total_questions, 'errors': errors}
    
    def save_questions(self, questions, source_file=''):
        saved_count = 0
        errors = []
        
        for i, question in enumerate(questions):
            try:
                required_fields = ['question_text', 'choices', 'correct_answer']
                if not all(field in question for field in required_fields):
                    errors.append(f"Question {i+1}: Missing required fields")
                    continue
                
                question_id = question.get('question_id', f"Q{i+1:03d}_{source_file}")
                choices_data = json.dumps(question['choices'], ensure_ascii=False)
                
                # image_urlの処理（nullまたは空文字列をNoneに変換）
                image_url = question.get('image_url')
                if image_url and image_url.lower() in ['null', 'none', '']:
                    image_url = None
                
                # Check if exists
                existing = self.db.execute_query(
                    'SELECT id FROM questions WHERE question_id = %s' if self.db.db_type == 'postgresql' else 'SELECT id FROM questions WHERE question_id = ?',
                    (question_id,)
                )
                
                if not existing:
                    # Insert new
                    if self.db.db_type == 'postgresql':
                        self.db.execute_query("""
                            INSERT INTO questions (question_id, question_text, choices, correct_answer, explanation, genre, image_url) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            question_id, question['question_text'], choices_data,
                            question['correct_answer'], question.get('explanation', ''),
                            question.get('genre', 'その他'), image_url
                        ))
                    else:
                        self.db.execute_query("""
                            INSERT INTO questions (question_id, question_text, choices, correct_answer, explanation, genre, image_url) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            question_id, question['question_text'], choices_data,
                            question['correct_answer'], question.get('explanation', ''),
                            question.get('genre', 'その他'), image_url
                        ))
                else:
                    # Update existing question with image_url
                    if self.db.db_type == 'postgresql':
                        self.db.execute_query("""
                            UPDATE questions 
                            SET question_text = %s, choices = %s, correct_answer = %s, 
                                explanation = %s, genre = %s, image_url = %s
                            WHERE question_id = %s
                        """, (
                            question['question_text'], choices_data,
                            question['correct_answer'], question.get('explanation', ''),
                            question.get('genre', 'その他'), image_url, question_id
                        ))
                    else:
                        self.db.execute_query("""
                            UPDATE questions 
                            SET question_text = ?, choices = ?, correct_answer = ?, 
                                explanation = ?, genre = ?, image_url = ?
                            WHERE question_id = ?
                        """, (
                            question['question_text'], choices_data,
                            question['correct_answer'], question.get('explanation', ''),
                            question.get('genre', 'その他'), image_url, question_id
                        ))
                
                saved_count += 1
                
            except Exception as e:
                errors.append(f"Question {i+1}: {str(e)}")
        
        return {'saved_count': saved_count, 'total_count': len(questions), 'errors': errors}
