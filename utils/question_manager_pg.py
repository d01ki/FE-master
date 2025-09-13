"""
PostgreSQL用問題管理クラス (psycopg3対応)
"""

import psycopg
from psycopg.rows import dict_row
import json
import random
from .database_pg import get_db_connection

class QuestionManager:
    """PostgreSQL対応問題管理クラス"""
    
    def __init__(self, database_url):
        self.database_url = database_url
    
    def save_questions(self, questions):
        """問題をデータベースに保存（重複チェック付き）"""
        saved_count = 0
        try:
            with get_db_connection(self.database_url) as conn:
                cursor = conn.cursor()
                
                for question in questions:
                    try:
                        # 重複チェック
                        cursor.execute(
                            'SELECT id FROM questions WHERE question_id = %s',
                            (question.get('question_id'),)
                        )
                        
                        if cursor.fetchone():
                            continue  # 既存の問題はスキップ
                        
                        # 選択肢をJSON文字列として保存
                        choices_json = json.dumps(question['choices'], ensure_ascii=False)
                        
                        cursor.execute('''
                            INSERT INTO questions (question_id, question_text, choices, correct_answer, explanation, genre)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (
                            question.get('question_id', f'Q{saved_count+1}'),
                            question['question_text'],
                            choices_json,
                            question['correct_answer'],
                            question.get('explanation', ''),
                            question.get('genre', 'その他')
                        ))
                        
                        saved_count += 1
                        
                    except Exception as e:
                        print(f"問題保存エラー: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            print(f"データベース保存エラー: {e}")
        
        return saved_count
    
    def get_question(self, question_id):
        """IDで問題を取得"""
        try:
            with get_db_connection(self.database_url) as conn:
                cursor = conn.cursor(row_factory=dict_row)
                cursor.execute(
                    'SELECT * FROM questions WHERE id = %s',
                    (question_id,)
                )
                
                question = cursor.fetchone()
                if question:
                    question_dict = dict(question)
                    # JSON文字列を辞書に変換
                    question_dict['choices'] = json.loads(question_dict['choices'])
                    return question_dict
                    
        except Exception as e:
            print(f"問題取得エラー: {e}")
        
        return None
    
    def get_random_question(self):
        """ランダムな問題を1問取得"""
        try:
            with get_db_connection(self.database_url) as conn:
                cursor = conn.cursor(row_factory=dict_row)
                cursor.execute('SELECT * FROM questions ORDER BY RANDOM() LIMIT 1')
                
                question = cursor.fetchone()
                if question:
                    question_dict = dict(question)
                    question_dict['choices'] = json.loads(question_dict['choices'])
                    return question_dict
                    
        except Exception as e:
            print(f"ランダム問題取得エラー: {e}")
        
        return None
    
    def get_random_questions(self, count):
        """ランダムな問題を指定数取得"""
        try:
            with get_db_connection(self.database_url) as conn:
                cursor = conn.cursor(row_factory=dict_row)
                cursor.execute('SELECT * FROM questions ORDER BY RANDOM() LIMIT %s', (count,))
                
                questions = cursor.fetchall()
                result = []
                for question in questions:
                    question_dict = dict(question)
                    question_dict['choices'] = json.loads(question_dict['choices'])
                    result.append(question_dict)
                
                return result
                    
        except Exception as e:
            print(f"ランダム問題取得エラー: {e}")
        
        return []
    
    def get_questions_by_genre(self, genre):
        """ジャンル別問題取得"""
        try:
            with get_db_connection(self.database_url) as conn:
                cursor = conn.cursor(row_factory=dict_row)
                cursor.execute('SELECT * FROM questions WHERE genre = %s', (genre,))
                
                questions = cursor.fetchall()
                result = []
                for question in questions:
                    question_dict = dict(question)
                    question_dict['choices'] = json.loads(question_dict['choices'])
                    result.append(question_dict)
                
                return result
                    
        except Exception as e:
            print(f"ジャンル別問題取得エラー: {e}")
        
        return []
    
    def get_available_genres(self):
        """利用可能なジャンル一覧を取得"""
        try:
            with get_db_connection(self.database_url) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT DISTINCT genre FROM questions ORDER BY genre')
                
                genres = cursor.fetchall()
                return [genre[0] for genre in genres]
                    
        except Exception as e:
            print(f"ジャンル取得エラー: {e}")
        
        return []
    
    def get_question_count_by_genre(self):
        """ジャンル別問題数を取得"""
        try:
            with get_db_connection(self.database_url) as conn:
                cursor = conn.cursor(row_factory=dict_row)
                cursor.execute('SELECT genre, COUNT(*) as count FROM questions GROUP BY genre')
                
                counts = cursor.fetchall()
                return {row['genre']: row['count'] for row in counts}
                    
        except Exception as e:
            print(f"ジャンル別問題数取得エラー: {e}")
        
        return {}
    
    def get_total_questions(self):
        """総問題数を取得"""
        try:
            with get_db_connection(self.database_url) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM questions')
                
                return cursor.fetchone()[0]
                    
        except Exception as e:
            print(f"総問題数取得エラー: {e}")
        
        return 0
    
    def check_answer(self, question_id, user_answer):
        """解答をチェック"""
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
            print(f"解答チェックエラー: {e}")
            return {'error': '解答チェック中にエラーが発生しました'}
    
    def save_answer_history(self, question_id, user_answer, is_correct, user_id):
        """解答履歴を保存"""
        try:
            with get_db_connection(self.database_url) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_answers (user_id, question_id, user_answer, is_correct)
                    VALUES (%s, %s, %s, %s)
                ''', (user_id, question_id, user_answer, is_correct))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"解答履歴保存エラー: {e}")
            return False
    
    def get_user_stats(self, user_id):
        """ユーザー統計を取得"""
        try:
            with get_db_connection(self.database_url) as conn:
                cursor = conn.cursor(row_factory=dict_row)
                
                # 総解答数
                cursor.execute('SELECT COUNT(*) as total FROM user_answers WHERE user_id = %s', (user_id,))
                total_answers = cursor.fetchone()['total']
                
                # 正答数
                cursor.execute('SELECT COUNT(*) as correct FROM user_answers WHERE user_id = %s AND is_correct = true', (user_id,))
                correct_answers = cursor.fetchone()['correct']
                
                # 正答率
                accuracy_rate = (correct_answers / total_answers * 100) if total_answers > 0 else 0
                
                # ジャンル別統計
                cursor.execute('''
                    SELECT q.genre, 
                           COUNT(*) as total,
                           SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) as correct
                    FROM user_answers ua 
                    JOIN questions q ON ua.question_id = q.id 
                    WHERE ua.user_id = %s
                    GROUP BY q.genre
                ''', (user_id,))
                
                genre_stats = cursor.fetchall()
                
                return {
                    'total_answers': total_answers,
                    'correct_answers': correct_answers,
                    'accuracy_rate': round(accuracy_rate, 1),
                    'genre_stats': [dict(row) for row in genre_stats]
                }
                
        except Exception as e:
            print(f"ユーザー統計取得エラー: {e}")
            return {
                'total_answers': 0,
                'correct_answers': 0,
                'accuracy_rate': 0,
                'genre_stats': []
            }
