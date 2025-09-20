"""
問題管理クラス（PostgreSQL/SQLite対応）
問題の取得、保存、解答処理などを管理
"""

import json
from datetime import datetime
import re

class QuestionManager:
    """問題管理クラス（PostgreSQL/SQLite対応）"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.last_question_id = None  # 前回出題した問題ID
    
    def is_image_url(self, text):
        """テキストが画像URLかどうかを判定"""
        if not text or not isinstance(text, str):
            return False
        
        # 画像URLのパターン
        image_patterns = [
            r'/static/images/',
            r'\.png$',
            r'\.jpg$',
            r'\.jpeg$',
            r'\.gif$',
            r'\.svg$',
            r'\.webp$'
        ]
        
        text_lower = text.lower()
        is_image = any(re.search(pattern, text_lower) for pattern in image_patterns)
        
        # デバッグログ
        print(f"[DEBUG] is_image_url: text='{text}', is_image={is_image}")
        
        return is_image
    
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
                question = dict(result[0])
                
                # image_urlの正規化（空やnullを None に統一）
                if question.get('image_url'):
                    img_url = question['image_url']
                    if img_url in ['null', 'None', '', 'undefined']:
                        question['image_url'] = None
                else:
                    question['image_url'] = None
                
                print(f"[DEBUG] Question image_url after normalization: {question.get('image_url')}")
                
                # choicesをJSONパース
                if isinstance(question['choices'], str):
                    question['choices'] = json.loads(question['choices'])
                
                # デバッグログ
                print(f"[DEBUG] Question choices: {question['choices']}")
                
                # 選択肢が画像URLかどうかを判定
                question['has_image_choices'] = False
                if question['choices']:
                    # 最初の選択肢をチェック（すべて同じ形式と仮定）
                    first_choice = list(question['choices'].values())[0]
                    question['has_image_choices'] = self.is_image_url(first_choice)
                    
                    print(f"[DEBUG] First choice: '{first_choice}'")
                    print(f"[DEBUG] has_image_choices: {question['has_image_choices']}")
                
                # 後方互換性: choice_imagesがあれば処理（廃止予定）
                if question.get('choice_images'):
                    if isinstance(question['choice_images'], str):
                        question['choice_images'] = json.loads(question['choice_images'])
                else:
                    question['choice_images'] = None
                
                return question
            return None
        except Exception as e:
            print(f"Error getting question {question_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_questions_by_genre(self, genre):
        """ジャンル別問題を取得"""
        try:
            if self.db_manager.db_type == 'postgresql':
                result = self.db_manager.execute_query(
                    'SELECT * FROM questions WHERE genre = %s ORDER BY question_id', (genre,)
                )
            else:
                result = self.db_manager.execute_query(
                    'SELECT * FROM questions WHERE genre = ? ORDER BY question_id', (genre,)
                )
            
            questions = []
            for row in result:
                question = dict(row)
                
                # image_urlの正規化
                if question.get('image_url'):
                    img_url = question['image_url']
                    if img_url in ['null', 'None', '', 'undefined']:
                        question['image_url'] = None
                else:
                    question['image_url'] = None
                
                # choicesをJSONパース
                if isinstance(question['choices'], str):
                    question['choices'] = json.loads(question['choices'])
                
                # 選択肢が画像URLかどうかを判定
                question['has_image_choices'] = False
                if question['choices']:
                    first_choice = list(question['choices'].values())[0]
                    question['has_image_choices'] = self.is_image_url(first_choice)
                
                # choice_imagesがあれば処理
                if question.get('choice_images') and isinstance(question['choice_images'], str):
                    question['choice_images'] = json.loads(question['choice_images'])
                else:
                    question['choice_images'] = None
                
                questions.append(question)
            
            return questions
        except Exception as e:
            print(f"Error getting questions by genre {genre}: {e}")
            return []
    
    def get_random_question(self):
        """ランダムに1問取得（前回と同じ問題を避ける）"""
        try:
            # 前回の問題を除外するクエリ
            if self.last_question_id:
                if self.db_manager.db_type == 'postgresql':
                    result = self.db_manager.execute_query(
                        'SELECT * FROM questions WHERE id != %s ORDER BY RANDOM() LIMIT 1',
                        (self.last_question_id,)
                    )
                else:
                    result = self.db_manager.execute_query(
                        'SELECT * FROM questions WHERE id != ? ORDER BY RANDOM() LIMIT 1',
                        (self.last_question_id,)
                    )
            else:
                if self.db_manager.db_type == 'postgresql':
                    result = self.db_manager.execute_query(
                        'SELECT * FROM questions ORDER BY RANDOM() LIMIT 1'
                    )
                else:
                    result = self.db_manager.execute_query(
                        'SELECT * FROM questions ORDER BY RANDOM() LIMIT 1'
                    )
            
            if result:
                question = dict(result[0])
                
                # image_urlの正規化
                if question.get('image_url'):
                    img_url = question['image_url']
                    if img_url in ['null', 'None', '', 'undefined']:
                        question['image_url'] = None
                else:
                    question['image_url'] = None
                
                # choicesをJSONパース
                if isinstance(question['choices'], str):
                    question['choices'] = json.loads(question['choices'])
                
                # 選択肢が画像URLかどうかを判定
                question['has_image_choices'] = False
                if question['choices']:
                    first_choice = list(question['choices'].values())[0]
                    question['has_image_choices'] = self.is_image_url(first_choice)
                
                # choice_imagesがあれば処理
                if question.get('choice_images') and isinstance(question['choice_images'], str):
                    question['choice_images'] = json.loads(question['choice_images'])
                else:
                    question['choice_images'] = None
                
                self.last_question_id = question['id']  # 今回の問題IDを記録
                return question
            return None
        except Exception as e:
            print(f"Error getting random question: {e}")
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
    
    def extract_year_from_filename(self, filename):
        """ファイル名から年度を抽出"""
        # 2025r07_kamoku_a_spring.json -> 2025
        match = re.search(r'(\d{4})', filename)
        return match.group(1) if match else None
    
    def save_questions(self, questions, source_file=''):
        """問題リストをデータベースに保存"""
        saved_count = 0
        errors = []
        
        try:
            # ファイル名から年度を抽出して、既にその年度の問題が登録されているかチェック
            year = self.extract_year_from_filename(source_file)
            if year and self.check_year_exists(year):
                return {
                    'saved_count': 0,
                    'total_count': len(questions),
                    'errors': [f'{year}年度の問題は既に登録されています。データを初期化してから再度アップロードしてください。']
                }
            
            for i, question in enumerate(questions):
                try:
                    # 必須フィールドの確認
                    required_fields = ['question_text', 'choices', 'correct_answer']
                    if not all(key in question for key in required_fields):
                        errors.append(f"問題 {i+1}: 必須フィールドが不足しています")
                        continue
                    
                    choices_json = json.dumps(question['choices'], ensure_ascii=False)
                    
                    # question_idの取得
                    question_id = question.get('question_id', f"Q{i+1:03d}_{source_file}")
                    
                    # image_urlの処理（nullや空文字をNoneに統一）
                    image_url = question.get('image_url')
                    if not image_url or image_url in ['null', 'None', 'undefined', '']:
                        image_url = None
                    
                    # choice_images（後方互換性のため保持）
                    choice_images = question.get('choice_images')
                    choice_images_json = None
                    if choice_images and isinstance(choice_images, dict):
                        valid_choice_images = {}
                        for key, url in choice_images.items():
                            if url and url not in ['null', 'None', 'undefined', '']:
                                valid_choice_images[key] = url
                        
                        if valid_choice_images:
                            choice_images_json = json.dumps(valid_choice_images, ensure_ascii=False)
                    
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
                                   (question_id, question_text, choices, correct_answer, explanation, genre, image_url, choice_images) 
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                                (
                                    question_id,
                                    question['question_text'],
                                    choices_json,
                                    question['correct_answer'],
                                    question.get('explanation', ''),
                                    question.get('genre', 'その他'),
                                    image_url,
                                    choice_images_json
                                )
                            )
                        else:
                            self.db_manager.execute_query(
                                '''INSERT INTO questions 
                                   (question_id, question_text, choices, correct_answer, explanation, genre, image_url, choice_images) 
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                                (
                                    question_id,
                                    question['question_text'],
                                    choices_json,
                                    question['correct_answer'],
                                    question.get('explanation', ''),
                                    question.get('genre', 'その他'),
                                    image_url,
                                    choice_images_json
                                )
                            )
                        saved_count += 1
                    else:
                        errors.append(f"問題 {question_id}: 既に登録されています（スキップ）")
                    
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
    
    def check_year_exists(self, year):
        """指定された年度の問題が既に登録されているかチェック"""
        try:
            if self.db_manager.db_type == 'postgresql':
                result = self.db_manager.execute_query(
                    'SELECT COUNT(*) as count FROM questions WHERE question_id LIKE %s',
                    (f'{year}_%',)
                )
            else:
                result = self.db_manager.execute_query(
                    'SELECT COUNT(*) as count FROM questions WHERE question_id LIKE ?',
                    (f'{year}_%',)
                )
            return result[0]['count'] > 0 if result else False
        except Exception as e:
            print(f"Error checking year existence: {e}")
            return False
    
    def delete_all_questions(self):
        """すべての問題を削除（学習履歴は保持）"""
        try:
            self.db_manager.execute_query('DELETE FROM questions')
            print("✅ すべての問題を削除しました")
            # 学習履歴は削除しない！
            return {'success': True, 'message': 'すべての問題を削除しました（学習履歴は保持）'}
        except Exception as e:
            print(f"Error deleting all questions: {e}")
            return {'success': False, 'error': str(e)}
    
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
