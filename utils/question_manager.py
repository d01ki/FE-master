"""
問題管理ユーティリティ
問題の取得、保存、解答処理などを管理
"""

import sqlite3
import json
import random
from typing import List, Dict, Optional
from datetime import datetime
from .database import get_db_connection

class QuestionManager:
    """問題管理クラス"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_question(self, question_id: int) -> Optional[Dict]:
        """指定されたIDの問題を取得"""
        try:
            with get_db_connection(self.db_path) as conn:
                row = conn.execute(
                    'SELECT * FROM questions WHERE id = ?', 
                    (question_id,)
                ).fetchone()
                
                if row:
                    question = dict(row)
                    question['choices'] = json.loads(question['choices'])
                    return question
                return None
        except Exception as e:
            print(f"Error getting question {question_id}: {e}")
            return None
    
    def get_questions_by_genre(self, genre: str) -> List[Dict]:
        """ジャンル別問題を取得"""
        try:
            with get_db_connection(self.db_path) as conn:
                rows = conn.execute(
                    'SELECT * FROM questions WHERE genre = ? ORDER BY id', 
                    (genre,)
                ).fetchall()
                
                questions = []
                for row in rows:
                    question = dict(row)
                    question['choices'] = json.loads(question['choices'])
                    questions.append(question)
                
                return questions
        except Exception as e:
            print(f"Error getting questions by genre {genre}: {e}")
            return []
    
    def get_random_questions(self, count: int) -> List[Dict]:
        """ランダムに問題を取得"""
        try:
            with get_db_connection(self.db_path) as conn:
                rows = conn.execute(
                    'SELECT * FROM questions ORDER BY RANDOM() LIMIT ?', 
                    (count,)
                ).fetchall()
                
                questions = []
                for row in rows:
                    question = dict(row)
                    question['choices'] = json.loads(question['choices'])
                    questions.append(question)
                
                return questions
        except Exception as e:
            print(f"Error getting random questions: {e}")
            return []
    
    def get_random_question(self) -> Optional[Dict]:
        """ランダムに1問取得"""
        questions = self.get_random_questions(1)
        return questions[0] if questions else None
    
    def get_total_questions(self) -> int:
        """総問題数を取得"""
        try:
            with get_db_connection(self.db_path) as conn:
                result = conn.execute('SELECT COUNT(*) FROM questions').fetchone()
                return result[0] if result else 0
        except Exception as e:
            print(f"Error getting total questions count: {e}")
            return 0
    
    def check_answer(self, question_id: int, user_answer: str) -> Dict:
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
    
    def save_answer_history(self, question_id: int, user_answer: str, is_correct: bool) -> bool:
        """解答履歴を保存"""
        try:
            with get_db_connection(self.db_path) as conn:
                conn.execute(
                    '''INSERT INTO user_answers 
                       (question_id, user_answer, is_correct, answered_at) 
                       VALUES (?, ?, ?, ?)''',
                    (question_id, user_answer, is_correct, datetime.now())
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"解答履歴保存エラー: {e}")
            return False
    
    def save_questions(self, questions: List[Dict]) -> int:
        """問題リストをデータベースに保存（簡素化版）"""
        saved_count = 0
        
        try:
            with get_db_connection(self.db_path) as conn:
                for i, question in enumerate(questions):
                    try:
                        # 必須フィールドの確認
                        if not all(key in question for key in ['question_text', 'choices', 'correct_answer']):
                            print(f"問題 {i+1}: 必須フィールドが不足しています")
                            continue
                        
                        choices_json = json.dumps(question['choices'], ensure_ascii=False)
                        
                        # question_idがない場合は自動生成
                        question_id = question.get('question_id', f"Q{i+1:03d}")
                        
                        # 重複チェック（question_idで）
                        existing = conn.execute(
                            'SELECT id FROM questions WHERE question_id = ?',
                            (question_id,)
                        ).fetchone()
                        
                        if not existing:
                            # 新しい問題を挿入
                            conn.execute(
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
                        print(f"問題保存エラー {question.get('question_id', f'Q{i+1}')}: {e}")
                        continue
                
                conn.commit()
                print(f"データベースに {saved_count}問を保存しました")
                
        except Exception as e:
            print(f"Database save error: {e}")
        
        return saved_count
    
    def get_available_genres(self) -> List[str]:
        """利用可能なジャンル一覧を取得"""
        try:
            with get_db_connection(self.db_path) as conn:
                rows = conn.execute(
                    'SELECT DISTINCT genre FROM questions WHERE genre IS NOT NULL ORDER BY genre'
                ).fetchall()
                
                return [row[0] for row in rows]
        except Exception as e:
            print(f"Error getting genres: {e}")
            return []
    
    def get_question_count_by_genre(self) -> Dict[str, int]:
        """ジャンル別問題数を取得"""
        try:
            with get_db_connection(self.db_path) as conn:
                rows = conn.execute(
                    'SELECT genre, COUNT(*) as count FROM questions GROUP BY genre'
                ).fetchall()
                
                return {row[0]: row[1] for row in rows}
        except Exception as e:
            print(f"Error getting question count by genre: {e}")
            return {}
    
    def delete_question(self, question_id: int) -> bool:
        """問題を削除"""
        try:
            with get_db_connection(self.db_path) as conn:
                # 関連する解答履歴も削除
                conn.execute('DELETE FROM user_answers WHERE question_id = ?', (question_id,))
                conn.execute('DELETE FROM questions WHERE id = ?', (question_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"問題削除エラー: {e}")
            return False
