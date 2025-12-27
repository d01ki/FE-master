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

    def normalize_media_value(self, val):
        """Normalize image path/URL; return None when empty."""
        if not val or not isinstance(val, str):
            return None
        cleaned = val.strip()
        if not cleaned:
            return None
        cleaned = cleaned.replace('\\', '/')

        if 'protected_images/questions/' in cleaned:
            fname = cleaned.split('/')[-1]
            return f'/images/questions/{fname}'

        if cleaned.startswith('/images/questions/'):
            return cleaned
        if cleaned.startswith('images/questions/'):
            return '/' + cleaned
        if cleaned.startswith('/static/'):
            return cleaned
        if cleaned.startswith('static/'):
            return '/' + cleaned

        # If it looks like just a filename, map to protected route
        if '/' not in cleaned:
            return f'/images/questions/{cleaned}'

        return cleaned

    def sanitize_question_text(self, text):
        """Remove stray image path fragments from question text."""
        if not text or not isinstance(text, str):
            return text
        patterns = [
            r'/image\\?s?/question[s]?/[^\s]+',
            r'images?/questions?/[^\s]+',
            r'protected_images/questions/[^\s]+'
        ]
        cleaned = text
        for p in patterns:
            cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def normalize_choice_value(self, val):
        """Normalize choice text or image path, dropping noisy JSON blobs."""
        if val is None:
            return None
        if not isinstance(val, str):
            val = str(val)
        s = val.strip()
        if not s:
            return None

        lower = s.lower()
        if re.search(r'(\.png|\.jpg|\.jpeg|\.gif|\.svg|\.webp)$', lower) or '/image' in lower or 'protected_images/questions/' in lower:
            return self.normalize_media_value(s) or s

        if (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']')):
            try:
                decoded = json.loads(s)
                if isinstance(decoded, str):
                    s = decoded.strip()
                else:
                    return None
            except Exception:
                return None

        s = self.sanitize_question_text(s)
        return s if s else None
    
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
                
                # question text sanitize
                question['question_text'] = self.sanitize_question_text(question.get('question_text'))

                # image_urlの正規化
                question['image_url'] = self.normalize_media_value(question.get('image_url'))

                # choicesをJSONパース
                if isinstance(question['choices'], str):
                    question['choices'] = json.loads(question['choices'])

                # 選択肢の正規化
                if isinstance(question.get('choices'), dict):
                    cleaned_choices = {}
                    for ck, cv in question['choices'].items():
                        cleaned_val = self.normalize_choice_value(cv)
                        if cleaned_val:
                            cleaned_choices[ck] = cleaned_val
                    question['choices'] = cleaned_choices
                else:
                    question['choices'] = {}

                # デバッグログ
                print(f"[DEBUG] Question choices: {question['choices']}")

                # 選択肢が画像URLかどうかを判定
                question['has_image_choices'] = False
                if question['choices']:
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
            result = self.db_manager.execute_query(
                'SELECT * FROM questions WHERE genre = ? ORDER BY question_id', (genre,)
            )
            
            questions = []
            for row in result:
                question = dict(row)
                
                # question text sanitize & image normalization
                question['question_text'] = self.sanitize_question_text(question.get('question_text'))
                question['image_url'] = self.normalize_media_value(question.get('image_url'))

                # choicesをJSONパース
                if isinstance(question['choices'], str):
                    question['choices'] = json.loads(question['choices'])

                if isinstance(question.get('choices'), dict):
                    cleaned_choices = {}
                    for ck, cv in question['choices'].items():
                        cleaned_val = self.normalize_choice_value(cv)
                        if cleaned_val:
                            cleaned_choices[ck] = cleaned_val
                    question['choices'] = cleaned_choices
                else:
                    question['choices'] = {}

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
    
    def get_all_genres(self):
        """すべてのジャンル一覧を取得"""
        try:
            result = self.db_manager.execute_query(
                'SELECT DISTINCT genre FROM questions WHERE genre IS NOT NULL ORDER BY genre'
            )
            
            genres = []
            for row in result:
                genre = row['genre']
                # ジャンル別問題数も取得
                count_result = self.db_manager.execute_query(
                    'SELECT COUNT(*) as count FROM questions WHERE genre = ?', (genre,)
                )
                count = count_result[0]['count'] if count_result else 0
                
                genres.append({
                    'name': genre,
                    'count': count
                })
            
            return genres
        except Exception as e:
            print(f"Error getting genres: {e}")
            return []
    
    def get_random_question(self):
        """ランダムに1問取得（前回と同じ問題を避ける）"""
        try:
            # DBごとのランダム関数
            if self.db_manager.db_type == 'mysql':
                random_func = 'RAND()'
            else:
                random_func = 'RANDOM()'
            
            # 前回の問題を除外するクエリ
            if self.last_question_id:
                result = self.db_manager.execute_query(
                    f'SELECT * FROM questions WHERE id != ? ORDER BY {random_func} LIMIT 1',
                    (self.last_question_id,)
                )
            else:
                result = self.db_manager.execute_query(
                    f'SELECT * FROM questions ORDER BY {random_func} LIMIT 1'
                )
            
            if result:
                question = dict(result[0])
                
                # question text sanitize & image normalization
                question['question_text'] = self.sanitize_question_text(question.get('question_text'))
                question['image_url'] = self.normalize_media_value(question.get('image_url'))

                # choicesをJSONパース
                if isinstance(question['choices'], str):
                    question['choices'] = json.loads(question['choices'])

                if isinstance(question.get('choices'), dict):
                    cleaned_choices = {}
                    for ck, cv in question['choices'].items():
                        cleaned_val = self.normalize_choice_value(cv)
                        if cleaned_val:
                            cleaned_choices[ck] = cleaned_val
                    question['choices'] = cleaned_choices
                else:
                    question['choices'] = {}

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
            # 回答保存後に集計を更新
            try:
                self.db_manager.update_user_stats(user_id)
            except Exception as stats_error:
                print(f"Failed to update user_stats for user {user_id}: {stats_error}")
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
                    
                    cleaned_choices = {}
                    if isinstance(question.get('choices'), dict):
                        for ck, cv in question['choices'].items():
                            cleaned_val = self.normalize_choice_value(cv)
                            if cleaned_val:
                                cleaned_choices[ck] = cleaned_val
                    choices_json = json.dumps(cleaned_choices, ensure_ascii=False)
                    
                    # question_idの取得
                    question_id = question.get('question_id', f"Q{i+1:03d}_{source_file}")
                    
                    # image_urlの処理（正規化して格納）
                    image_url = self.normalize_media_value(question.get('image_url'))
                    
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
                                    self.sanitize_question_text(question.get('question_text')),
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
                                    self.sanitize_question_text(question.get('question_text')),
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
