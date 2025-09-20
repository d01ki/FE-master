import os
import sqlite3
import json
import logging
from utils import sanitize_image_url, validate_image_url

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
                choice_images JSON,
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
            END $$;""",
            # choice_imagesカラムを追加（存在しない場合のみ）
            """DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='questions' AND column_name='choice_images') THEN
                    ALTER TABLE questions ADD COLUMN choice_images JSON;
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
                choice_images TEXT,
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
                logger.error(f"SQLite init error: {e}\")\n        \n        # 既存のテーブルにimage_urlカラムを追加（存在しない場合のみ）\n        try:\n            table_info = self.execute_query(\"PRAGMA table_info(questions)\")\n            column_names = [col['name'] for col in table_info]\n            \n            if 'image_url' not in column_names:\n                self.execute_query(\"ALTER TABLE questions ADD COLUMN image_url TEXT\")\n                logger.info(\"Added image_url column to questions table\")\n            \n            # choice_imagesカラムを追加\n            if 'choice_images' not in column_names:\n                self.execute_query(\"ALTER TABLE questions ADD COLUMN choice_images TEXT\")\n                logger.info(\"Added choice_images column to questions table\")\n        except Exception as e:\n            logger.error(f\"SQLite alter table error: {e}\")\n\nclass QuestionManager:\n    def __init__(self, db_manager):\n        self.db = db_manager\n    \n    def load_json_files(self):\n        json_folder = 'json_questions'\n        if not os.path.exists(json_folder):\n            return {'total_files': 0, 'total_questions': 0, 'errors': []}\n        \n        total_files = 0\n        total_questions = 0\n        errors = []\n        \n        for filename in os.listdir(json_folder):\n            if filename.endswith('.json'):\n                filepath = os.path.join(json_folder, filename)\n                try:\n                    with open(filepath, 'r', encoding='utf-8') as f:\n                        questions = json.load(f)\n                    \n                    result = self.save_questions(questions, filename)\n                    total_files += 1\n                    total_questions += result['saved_count']\n                    \n                except Exception as e:\n                    errors.append(f\"{filename}: {str(e)}\")\n        \n        return {'total_files': total_files, 'total_questions': total_questions, 'errors': errors}\n    \n    def save_questions(self, questions, source_file=''):\n        saved_count = 0\n        errors = []\n        warnings = []\n        \n        for i, question in enumerate(questions):\n            try:\n                required_fields = ['question_text', 'choices', 'correct_answer']\n                if not all(field in question for field in required_fields):\n                    errors.append(f\"Question {i+1}: Missing required fields\")\n                    continue\n                \n                question_id = question.get('question_id', f\"Q{i+1:03d}_{source_file}\")\n                choices_data = json.dumps(question['choices'], ensure_ascii=False)\n                \n                # 画像URLの処理とバリデーション\n                image_url = question.get('image_url')\n                image_url = sanitize_image_url(image_url)\n                \n                if image_url:\n                    is_valid, error_message = validate_image_url(image_url)\n                    if not is_valid:\n                        logger.warning(f\"Question {question_id}: 画像URL検証失敗 - {error_message}\")\n                        warnings.append(f\"Question {i+1}: 画像URL検証失敗 - {error_message}\")\n                        image_url = None\n                    elif error_message:\n                        logger.info(f\"Question {question_id}: {error_message}\")\n                \n                # 選択肢画像の処理\n                choice_images = question.get('choice_images')\n                choice_images_json = None\n                \n                if choice_images and isinstance(choice_images, dict):\n                    # 各選択肢の画像URLをサニタイズ\n                    sanitized_choice_images = {}\n                    for key, url in choice_images.items():\n                        sanitized_url = sanitize_image_url(url)\n                        if sanitized_url:\n                            is_valid, error_message = validate_image_url(sanitized_url)\n                            if is_valid:\n                                sanitized_choice_images[key] = sanitized_url\n                            else:\n                                logger.warning(f\"Question {question_id}, Choice {key}: 画像URL検証失敗 - {error_message}\")\n                    \n                    if sanitized_choice_images:\n                        choice_images_json = json.dumps(sanitized_choice_images, ensure_ascii=False)\n                \n                # Check if exists\n                existing = self.db.execute_query(\n                    'SELECT id FROM questions WHERE question_id = %s' if self.db.db_type == 'postgresql' else 'SELECT id FROM questions WHERE question_id = ?',\n                    (question_id,)\n                )\n                \n                if not existing:\n                    # Insert new\n                    if self.db.db_type == 'postgresql':\n                        self.db.execute_query(\"\"\"\n                            INSERT INTO questions (question_id, question_text, choices, correct_answer, explanation, genre, image_url, choice_images) \n                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)\n                        \"\"\", (\n                            question_id, question['question_text'], choices_data,\n                            question['correct_answer'], question.get('explanation', ''),\n                            question.get('genre', 'その他'), image_url, choice_images_json\n                        ))\n                    else:\n                        self.db.execute_query(\"\"\"\n                            INSERT INTO questions (question_id, question_text, choices, correct_answer, explanation, genre, image_url, choice_images) \n                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n                        \"\"\", (\n                            question_id, question['question_text'], choices_data,\n                            question['correct_answer'], question.get('explanation', ''),\n                            question.get('genre', 'その他'), image_url, choice_images_json\n                        ))\n                else:\n                    # Update existing question\n                    if self.db.db_type == 'postgresql':\n                        self.db.execute_query(\"\"\"\n                            UPDATE questions \n                            SET question_text = %s, choices = %s, correct_answer = %s, \n                                explanation = %s, genre = %s, image_url = %s, choice_images = %s\n                            WHERE question_id = %s\n                        \"\"\", (\n                            question['question_text'], choices_data,\n                            question['correct_answer'], question.get('explanation', ''),\n                            question.get('genre', 'その他'), image_url, choice_images_json, question_id\n                        ))\n                    else:\n                        self.db.execute_query(\"\"\"\n                            UPDATE questions \n                            SET question_text = ?, choices = ?, correct_answer = ?, \n                                explanation = ?, genre = ?, image_url = ?, choice_images = ?\n                            WHERE question_id = ?\n                        \"\"\", (\n                            question['question_text'], choices_data,\n                            question['correct_answer'], question.get('explanation', ''),\n                            question.get('genre', 'その他'), image_url, choice_images_json, question_id\n                        ))\n                \n                saved_count += 1\n                \n            except Exception as e:\n                errors.append(f\"Question {i+1}: {str(e)}\")\n                logger.error(f\"Error saving question {i+1}: {str(e)}\")\n        \n        return {\n            'saved_count': saved_count, \n            'total_count': len(questions), \n            'errors': errors,\n            'warnings': warnings\n        }
