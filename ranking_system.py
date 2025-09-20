"""
ランキングシステム - 総合ポイント計算とランキング管理
正答率（精度）+ 解答量（経験値）+ 最近の活動（アクティブさ）を合成したスコア
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class RankingSystem:
    # スコア計算のデフォルト重み（チューニング可能）
    DEFAULT_WEIGHTS = {
        'accuracy': 0.4,      # 正答率の重み（40%）
        'volume': 0.35,       # 解答量の重み（35%）
        'activity': 0.25      # 最近の活動の重み（25%）
    }
    
    def __init__(self, db_manager, weights: Optional[Dict[str, float]] = None):
        self.db = db_manager
        self.weights = weights or self.DEFAULT_WEIGHTS
        
    def calculate_accuracy_score(self, user_id: int) -> float:
        """正答率スコアを計算（0-100点）"""
        try:
            if self.db.db_type == 'postgresql':
                result = self.db.execute_query("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
                    FROM user_answers
                    WHERE user_id = %s
                """, (user_id,))
            else:
                result = self.db.execute_query("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
                    FROM user_answers
                    WHERE user_id = ?
                """, (user_id,))
            
            if result and result[0]['total'] > 0:
                accuracy = (result[0]['correct'] / result[0]['total']) * 100
                return round(accuracy, 2)
            return 0.0
            
        except Exception as e:
            logger.error(f"正答率計算エラー (user_id={user_id}): {e}")
            return 0.0
    
    def calculate_volume_score(self, user_id: int) -> float:
        """解答量スコアを計算（0-100点）
        解答数に応じてスコアを算出。1000問で満点と仮定
        """
        try:
            if self.db.db_type == 'postgresql':
                result = self.db.execute_query("""
                    SELECT COUNT(*) as total
                    FROM user_answers
                    WHERE user_id = %s
                """, (user_id,))
            else:
                result = self.db.execute_query("""
                    SELECT COUNT(*) as total
                    FROM user_answers
                    WHERE user_id = ?
                """, (user_id,))
            
            if result:
                total_answers = result[0]['total']
                # 1000問を満点として計算（それ以上は100点で頭打ち）
                score = min((total_answers / 1000) * 100, 100)
                return round(score, 2)
            return 0.0
            
        except Exception as e:
            logger.error(f"解答量計算エラー (user_id={user_id}): {e}")
            return 0.0
    
    def calculate_activity_score(self, user_id: int, days: int = 30) -> float:
        """最近の活動スコアを計算（0-100点）
        直近30日間の活動を評価
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            if self.db.db_type == 'postgresql':
                result = self.db.execute_query("""
                    SELECT COUNT(*) as recent_count
                    FROM user_answers
                    WHERE user_id = %s AND answered_at >= %s
                """, (user_id, cutoff_date))
            else:
                result = self.db.execute_query("""
                    SELECT COUNT(*) as recent_count
                    FROM user_answers
                    WHERE user_id = ? AND answered_at >= ?
                """, (user_id, cutoff_date.strftime('%Y-%m-%d %H:%M:%S')))
            
            if result:
                recent_count = result[0]['recent_count']
                # 30日で300問を満点として計算（1日平均10問）
                score = min((recent_count / 300) * 100, 100)
                return round(score, 2)
            return 0.0
            
        except Exception as e:
            logger.error(f"活動度計算エラー (user_id={user_id}): {e}")
            return 0.0
    
    def calculate_total_score(self, user_id: int) -> Dict[str, float]:
        """総合スコアを計算"""
        accuracy = self.calculate_accuracy_score(user_id)
        volume = self.calculate_volume_score(user_id)
        activity = self.calculate_activity_score(user_id)
        
        # 重み付け合計
        total = (
            accuracy * self.weights['accuracy'] +
            volume * self.weights['volume'] +
            activity * self.weights['activity']
        )
        
        return {
            'accuracy_score': accuracy,
            'volume_score': volume,
            'activity_score': activity,
            'total_score': round(total, 2),
            'weights': self.weights
        }
    
    def get_user_rank(self, user_id: int) -> Optional[int]:
        """ユーザーの順位を取得"""
        try:
            # 全ユーザーのスコアを計算
            users = self.get_all_users()
            scores = []
            
            for user in users:
                score_data = self.calculate_total_score(user['id'])
                scores.append({
                    'user_id': user['id'],
                    'total_score': score_data['total_score']
                })
            
            # スコアでソート
            scores.sort(key=lambda x: x['total_score'], reverse=True)
            
            # ユーザーの順位を探す
            for idx, score_info in enumerate(scores, 1):
                if score_info['user_id'] == user_id:
                    return idx
            
            return None
            
        except Exception as e:
            logger.error(f"順位計算エラー (user_id={user_id}): {e}")
            return None
    
    def get_ranking(self, limit: int = 100, exclude_admin: bool = True) -> List[Dict]:
        """ランキングリストを取得
        
        Args:
            limit: 取得する最大人数
            exclude_admin: 管理者を除外するか
        
        Returns:
            ランキングリスト
        """
        try:
            users = self.get_all_users(exclude_admin=exclude_admin)
            ranking = []
            
            for user in users:
                score_data = self.calculate_total_score(user['id'])
                ranking.append({
                    'rank': 0,  # 後で設定
                    'user_id': user['id'],
                    'username': user['username'],
                    'total_score': score_data['total_score'],
                    'accuracy_score': score_data['accuracy_score'],
                    'volume_score': score_data['volume_score'],
                    'activity_score': score_data['activity_score']
                })
            
            # スコアでソート
            ranking.sort(key=lambda x: x['total_score'], reverse=True)
            
            # 順位を設定
            for idx, entry in enumerate(ranking[:limit], 1):
                entry['rank'] = idx
            
            return ranking[:limit]
            
        except Exception as e:
            logger.error(f"ランキング取得エラー: {e}")
            return []
    
    def get_all_users(self, exclude_admin: bool = True) -> List[Dict]:
        """全ユーザーを取得"""
        try:
            if exclude_admin:
                if self.db.db_type == 'postgresql':
                    users = self.db.execute_query("""
                        SELECT id, username, is_admin
                        FROM users
                        WHERE is_admin = FALSE
                    """)
                else:
                    users = self.db.execute_query("""
                        SELECT id, username, is_admin
                        FROM users
                        WHERE is_admin = 0
                    """)
            else:
                users = self.db.execute_query("""
                    SELECT id, username, is_admin
                    FROM users
                """)
            
            return users or []
            
        except Exception as e:
            logger.error(f"ユーザー取得エラー: {e}")
            return []
    
    def get_user_statistics(self, user_id: int) -> Dict:
        """ユーザーの詳細統計を取得"""
        try:
            # 基本統計
            if self.db.db_type == 'postgresql':
                stats = self.db.execute_query("""
                    SELECT 
                        COUNT(*) as total_answers,
                        SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
                        COUNT(DISTINCT question_id) as unique_questions
                    FROM user_answers
                    WHERE user_id = %s
                """, (user_id,))
            else:
                stats = self.db.execute_query("""
                    SELECT 
                        COUNT(*) as total_answers,
                        SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_answers,
                        COUNT(DISTINCT question_id) as unique_questions
                    FROM user_answers
                    WHERE user_id = ?
                """, (user_id,))
            
            if not stats:
                return self._empty_statistics()
            
            stat = stats[0]
            
            # スコア計算
            score_data = self.calculate_total_score(user_id)
            
            # 順位取得
            rank = self.get_user_rank(user_id)
            
            return {
                'total_answers': stat['total_answers'],
                'correct_answers': stat['correct_answers'],
                'unique_questions': stat['unique_questions'],
                'accuracy_rate': round((stat['correct_answers'] / stat['total_answers'] * 100) if stat['total_answers'] > 0 else 0, 2),
                'rank': rank,
                'scores': score_data
            }
            
        except Exception as e:
            logger.error(f"統計取得エラー (user_id={user_id}): {e}")
            return self._empty_statistics()
    
    def _empty_statistics(self) -> Dict:
        """空の統計データを返す"""
        return {
            'total_answers': 0,
            'correct_answers': 0,
            'unique_questions': 0,
            'accuracy_rate': 0.0,
            'rank': None,
            'scores': {
                'accuracy_score': 0.0,
                'volume_score': 0.0,
                'activity_score': 0.0,
                'total_score': 0.0,
                'weights': self.weights
            }
        }
