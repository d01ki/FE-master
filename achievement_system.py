"""
達成度システム（冠機能） - 模擬試験の網羅度管理
2回連続正解=金、1回正解=シルバー、ミス=銅
"""

import logging
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

class AchievementSystem:
    # 達成度の種類
    ACHIEVEMENT_LEVELS = {
        'gold': {'name': '金', 'emoji': '🥇', 'consecutive_correct': 2},
        'silver': {'name': 'シルバー', 'emoji': '🥈', 'consecutive_correct': 1},
        'bronze': {'name': '銅', 'emoji': '🥉', 'consecutive_correct': 0}
    }
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_question_achievement(self, user_id: int, question_id: int) -> str:
        """特定の問題の達成度を取得
        
        Returns:
            'gold', 'silver', 'bronze'のいずれか
        """
        try:
            # 最新の解答履歴を取得（最大3件）
            if self.db.db_type == 'postgresql':
                history = self.db.execute_query("""
                    SELECT is_correct, answered_at
                    FROM user_answers
                    WHERE user_id = %s AND question_id = %s
                    ORDER BY answered_at DESC
                    LIMIT 3
                """, (user_id, question_id))
            else:
                history = self.db.execute_query("""
                    SELECT is_correct, answered_at
                    FROM user_answers
                    WHERE user_id = ? AND question_id = ?
                    ORDER BY answered_at DESC
                    LIMIT 3
                """, (user_id, question_id))
            
            if not history:
                return 'bronze'  # 未解答
            
            # PostgreSQLの場合はbool、SQLiteの場合はintに変換
            correct_list = []
            for h in history:
                is_correct = h['is_correct']
                if isinstance(is_correct, bool):
                    correct_list.append(is_correct)
                else:
                    correct_list.append(bool(is_correct))
            
            # 連続正解数をチェック
            consecutive_correct = 0
            for is_correct in correct_list:
                if is_correct:
                    consecutive_correct += 1
                else:
                    break
            
            # 達成度判定
            if consecutive_correct >= 2:
                return 'gold'
            elif consecutive_correct >= 1:
                return 'silver'
            else:
                return 'bronze'
                
        except Exception as e:
            logger.error(f"達成度取得エラー (user_id={user_id}, question_id={question_id}): {e}")
            return 'bronze'
    
    def get_mock_exam_coverage(self, user_id: int) -> Dict:
        """模擬試験の網羅度を取得
        
        Returns:
            年度・問題番号ごとの達成度マップ
        """
        try:
            # すべての模擬試験問題を取得
            if self.db.db_type == 'postgresql':
                questions = self.db.execute_query("""
                    SELECT id, question_id
                    FROM questions
                    ORDER BY question_id
                """)
            else:
                questions = self.db.execute_query("""
                    SELECT id, question_id
                    FROM questions
                    ORDER BY question_id
                """)
            
            if not questions:
                return {'coverage_map': {}, 'summary': self._empty_summary()}
            
            # question_idから年度と問題番号を抽出
            coverage_map = defaultdict(dict)
            
            for q in questions:
                question_id = q['question_id']
                db_id = q['id']
                
                # question_idをパース（例: "2024_s_q1" -> year="2024春", num=1）
                parsed = self._parse_question_id(question_id)
                if not parsed:
                    continue
                
                year_season = parsed['year_season']
                question_num = parsed['question_num']
                
                # 達成度を取得
                achievement = self.get_question_achievement(user_id, db_id)
                
                if year_season not in coverage_map:
                    coverage_map[year_season] = {}
                
                coverage_map[year_season][question_num] = {
                    'achievement': achievement,
                    'question_id': question_id,
                    'db_id': db_id
                }
            
            # サマリー統計を計算
            summary = self._calculate_summary(coverage_map)
            
            return {
                'coverage_map': dict(coverage_map),
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"網羅度取得エラー (user_id={user_id}): {e}")
            return {'coverage_map': {}, 'summary': self._empty_summary()}
    
    def get_questions_by_achievement(self, user_id: int, achievement_level: str) -> List[Dict]:
        """指定された達成度の問題リストを取得
        
        Args:
            user_id: ユーザーID
            achievement_level: 'gold', 'silver', 'bronze'
        
        Returns:
            問題リスト
        """
        try:
            # すべての問題を取得
            if self.db.db_type == 'postgresql':
                questions = self.db.execute_query("""
                    SELECT id, question_id, question_text, genre
                    FROM questions
                    ORDER BY question_id
                """)
            else:
                questions = self.db.execute_query("""
                    SELECT id, question_id, question_text, genre
                    FROM questions
                    ORDER BY question_id
                """)
            
            if not questions:
                return []
            
            # フィルタリング
            filtered_questions = []
            for q in questions:
                achievement = self.get_question_achievement(user_id, q['id'])
                if achievement == achievement_level:
                    filtered_questions.append({
                        'id': q['id'],
                        'question_id': q['question_id'],
                        'question_text': q['question_text'],
                        'genre': q['genre'],
                        'achievement': achievement
                    })
            
            return filtered_questions
            
        except Exception as e:
            logger.error(f"達成度別問題取得エラー (user_id={user_id}, level={achievement_level}): {e}")
            return []
    
    def _parse_question_id(self, question_id: str) -> Optional[Dict]:
        """question_idをパースして年度・季節・問題番号を抽出
        
        例: "2024_s_q1" -> {'year': '2024', 'season': '春', 'year_season': '2024春', 'question_num': 1}
        """
        try:
            parts = question_id.split('_')
            if len(parts) < 3:
                return None
            
            year = parts[0]
            season_code = parts[1]
            question_num_str = parts[2].replace('q', '')
            
            # 季節コードを日本語に変換
            season_map = {
                's': '春',
                'a': '秋',
                'spring': '春',
                'autumn': '秋',
                'fall': '秋'
            }
            
            season = season_map.get(season_code.lower(), season_code)
            year_season = f"{year}{season}"
            question_num = int(question_num_str)
            
            return {
                'year': year,
                'season': season,
                'year_season': year_season,
                'question_num': question_num
            }
            
        except Exception as e:
            logger.error(f"question_idパースエラー ({question_id}): {e}")
            return None
    
    def _calculate_summary(self, coverage_map: Dict) -> Dict:
        """網羅度のサマリー統計を計算"""
        total = 0
        gold_count = 0
        silver_count = 0
        bronze_count = 0
        
        for year_season, questions in coverage_map.items():
            for question_num, data in questions.items():
                total += 1
                achievement = data['achievement']
                if achievement == 'gold':
                    gold_count += 1
                elif achievement == 'silver':
                    silver_count += 1
                else:
                    bronze_count += 1
        
        return {
            'total': total,
            'gold': gold_count,
            'silver': silver_count,
            'bronze': bronze_count,
            'gold_rate': round((gold_count / total * 100) if total > 0 else 0, 2),
            'silver_rate': round((silver_count / total * 100) if total > 0 else 0, 2),
            'bronze_rate': round((bronze_count / total * 100) if total > 0 else 0, 2)
        }
    
    def _empty_summary(self) -> Dict:
        """空のサマリーデータを返す"""
        return {
            'total': 0,
            'gold': 0,
            'silver': 0,
            'bronze': 0,
            'gold_rate': 0.0,
            'silver_rate': 0.0,
            'bronze_rate': 0.0
        }
    
    def get_achievement_progress(self, user_id: int) -> Dict:
        """達成度の進捗状況を取得（ダッシュボード用）"""
        try:
            coverage_data = self.get_mock_exam_coverage(user_id)
            summary = coverage_data['summary']
            
            # 進捗率計算（金＋銀の割合）
            progress_rate = round(
                ((summary['gold'] + summary['silver']) / summary['total'] * 100) 
                if summary['total'] > 0 else 0, 
                2
            )
            
            return {
                'summary': summary,
                'progress_rate': progress_rate,
                'next_goal': self._get_next_goal(summary)
            }
            
        except Exception as e:
            logger.error(f"進捗状況取得エラー (user_id={user_id}): {e}")
            return {
                'summary': self._empty_summary(),
                'progress_rate': 0.0,
                'next_goal': 'まずは1問解いてみましょう！'
            }
    
    def _get_next_goal(self, summary: Dict) -> str:
        """次の目標を提案"""
        total = summary['total']
        gold = summary['gold']
        
        if total == 0:
            return 'まずは1問解いてみましょう！'
        elif gold == 0:
            return '初めての金メダルを目指しましょう！'
        elif gold < total * 0.5:
            return '金メダルを50%以上にしましょう！'
        elif gold < total * 0.8:
            return '金メダルを80%以上にしましょう！'
        elif gold < total:
            return '全問題で金メダルを目指しましょう！'
        else:
            return '完璧です！この調子で復習を続けましょう！'
