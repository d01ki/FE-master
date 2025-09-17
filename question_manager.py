"""
問題管理クラス（PostgreSQL/SQLite対応）
問題の取得、保存、解答処理などを管理
"""

import json
from datetime import datetime

class QuestionManager:
    """問題管理クラス（PostgreSQL/SQLite対応）"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_question(self, question_id):
        """指定されたIDの問題を取得"""
        try:
            if self.db_manager.db_type == 'postgresql':
                result = self.db_manager.execute_query(
                    'SELECT * FROM questions WHERE id = %s', (question_id,)
                )
            else:
                result = self.db_manager.execute_query(
                    'SELECT * FROM questions WHERE id = ?', (question_id,)
                )
            
            if result:
                question = result[0]
                if isinstance(question['choices'], str):
                    question['choices'] = json.loads(question['choices'])
                return question
            return None
        except Exception as e:
            print(f"Error getting question {question_id}: {e}")
            return None
    
    def get_questions_by_genre(self, genre):
        """ジャンル別問題を取得"""
        try:
            if self.db_manager.db_type == 'postgresql':
                result = self.db_manager.execute_query(
                    'SELECT * FROM questions WHERE genre = %s ORDER BY id', (genre,)
                )
            else:
                result = self.db_manager.execute_query(
                    'SELECT * FROM questions WHERE genre = ? ORDER BY id', (genre,)
                )
            
            questions = []
            for row in result:
                question = dict(row)
                if isinstance(question['choices'], str):
                    question['choices'] = json.loads(question['choices'])
                questions.append(question)
            
            return questions
        except Exception as e:
            print(f"Error getting questions by genre {genre}: {e}")
            return []
    
    def get_random_questions(self, count):
        """ランダムに問題を取得"""
        try:
            if self.db_manager.db_type == 'postgresql':
                result = self.db_manager.execute_query(
                    'SELECT * FROM questions ORDER BY RANDOM() LIMIT %s', (count,)
                )
            else:
                result = self.db_manager.execute_query(
                    'SELECT * FROM questions ORDER BY RANDOM() LIMIT ?', (count,)
                )
            
            questions = []
            for row in result:
                question = dict(row)
                if isinstance(question['choices'], str):
                    question['choices'] = json.loads(question['choices'])
                questions.append(question)
            
            return questions
        except Exception as e:
            print(f"Error getting random questions: {e}")
            return []
    
    def get_random_question(self):
        """ランダムに1問取得"""
        questions = self.get_random_questions(1)
        return questions[0] if questions else None
    
    def get_random_question_by_genre(self, genre):
        """ジャンル別のランダム問題を1問取得"""
        try:
            if self.db_manager.db_type == 'postgresql':
                result = self.db_manager.execute_query(
                    'SELECT * FROM questions WHERE genre = %s ORDER BY RANDOM() LIMIT 1', (genre,)
                )
            else:
                result = self.db_manager.execute_query(
                    'SELECT * FROM questions WHERE genre = ? ORDER BY RANDOM() LIMIT 1', (genre,)
                )
            
            if result:
                question = result[0]
                if isinstance(question['choices'], str):
                    question['choices'] = json.loads(question['choices'])
                return question
            return None
        except Exception as e:
            print(f"Error getting random question by genre {genre}: {e}")
            return None
    
    def get_total_questions(self):
        """総問題数を取得"""
        try:
            result = self.db_manager.execute_query('SELECT COUNT(*) as count FROM questions')
            return result[0]['count'] if result else 0
        except Exception as e:
            print(f"Error getting total questions count: {e}")
            return 0
    
    def check_answer(self, question_id, user_answer):
        """解答をチェックして結果を返す"""
        try:
            question = self.get_question(question_id)
            if not question:
                return {'error': '問題が見つかりません'}
            
            is_correct = user_answer == question['correct_answer']
            
            return {
                'is_correct': is_correct,
                'correct_answer': question['correct_answer'],
                'explanation': question.get('explanation', ''),
                'user_answer': user_answer
            }
        except Exception as e:
            print(f"Error checking answer: {e}")
            return {'error': '解答の確認中にエラーが発生しました'}
    
    def save_answer_history(self, question_id, user_answer, is_correct, user_id):
        """解答履歴を保存（user_idを引数で受け取る）"""
        try:
            if self.db_manager.db_type == 'postgresql':
                self.db_manager.execute_query(
                    '''INSERT INTO user_answers 
                       (user_id, question_id, user_answer, is_correct, answered_at) 
                       VALUES (%s, %s, %s, %s, %s)''',
                    (user_id, question_id, user_answer, is_correct, datetime.now())
                )
            else:
                self.db_manager.execute_query(
                    '''INSERT INTO user_answers 
                       (user_id, question_id, user_answer, is_correct, answered_at) 
                       VALUES (?, ?, ?, ?, ?)''',
                    (user_id, question_id, user_answer, int(is_correct), datetime.now())
                )
            return True
        except Exception as e:
            print(f"解答履歴保存エラー: {e}")
            return False
    
    def save_questions(self, questions, source_file=''):
        """問題リストをデータベースに保存"""
        saved_count = 0
        errors = []
        
        try:
            for i, question in enumerate(questions):
                try:
                    # 必須フィールドの確認
                    required_fields = ['question_text', 'choices', 'correct_answer']
                    if not all(key in question for key in required_fields):
                        errors.append(f"問題 {i+1}: 必須フィールドが不足しています")
                        continue
                    
                    choices_json = json.dumps(question['choices'], ensure_ascii=False)
                    
                    # question_idがない場合は自動生成
                    question_id = question.get('question_id', f"Q{i+1:03d}_{source_file}")
                    
                    # 重複チェック（question_idで）
                    if self.db_manager.db_type == 'postgresql':
                        existing = self.db_manager.execute_query(
                            'SELECT id FROM questions WHERE question_id = %s',
                            (question_id,)
                        )
                    else:
                        existing = self.db_manager.execute_query(
                            'SELECT id FROM questions WHERE question_id = ?',
                            (question_id,)
                        )
                    
                    if not existing:
                        # 新しい問題を挿入
                        if self.db_manager.db_type == 'postgresql':
                            self.db_manager.execute_query(
                                '''INSERT INTO questions 
                                   (question_id, question_text, choices, correct_answer, explanation, genre) 
                                   VALUES (%s, %s, %s, %s, %s, %s)''',
                                (
                                    question_id,
                                    question['question_text'],
                                    choices_json,
                                    question['correct_answer'],
                                    question.get('explanation', ''),
                                    question.get('genre', 'その他')
                                )
                            )
                        else:
                            self.db_manager.execute_query(
                                '''INSERT INTO questions 
                                   (question_id, question_text, choices, correct_answer, explanation, genre) 
                                   VALUES (?, ?, ?, ?, ?, ?)''',
                                (
                                    question_id,
                                    question['question_text'],
                                    choices_json,
                                    question['correct_answer'],
                                    question.get('explanation', ''),
                                    question.get('genre', 'その他')
                                )
                            )
                        saved_count += 1
                    
                except Exception as e:
                    error_msg = f"問題保存エラー {question.get('question_id', f'Q{i+1}')}: {e}"
                    errors.append(error_msg)
                    print(error_msg)
                    continue
            
            print(f"データベースに {saved_count}問を保存しました")
            
        except Exception as e:
            error_msg = f"Database save error: {e}"
            errors.append(error_msg)
            print(error_msg)
        
        return {
            'saved_count': saved_count,
            'total_count': len(questions),
            'errors': errors
        }
    
    def get_available_genres(self):
        """利用可能なジャンル一覧を取得"""
        try:
            result = self.db_manager.execute_query(
                'SELECT DISTINCT genre FROM questions WHERE genre IS NOT NULL ORDER BY genre'
            )
            return [row['genre'] for row in result]
        except Exception as e:
            print(f"Error getting genres: {e}")
            return []
    
    def get_question_count_by_genre(self):
        """ジャンル別問題数を取得"""
        try:
            result = self.db_manager.execute_query(
                'SELECT genre, COUNT(*) as count FROM questions WHERE genre IS NOT NULL GROUP BY genre'
            )
            return {row['genre']: row['count'] for row in result}
        except Exception as e:
            print(f"Error getting question count by genre: {e}")
            return {}
