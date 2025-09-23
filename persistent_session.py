"""
セッション管理改善 - データベースベースのセッション
Renderの無料枠でスリープしてもログイン状態を維持
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import session, request, redirect, url_for, flash

class DatabaseSessionManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.init_session_table()
    
    def init_session_table(self):
        """セッションテーブルの初期化"""
        if self.db.db_type == 'postgresql':
            query = """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                user_data JSON NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        else:
            query = """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                user_data TEXT NOT NULL,
                expires_at DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        
        try:
            self.db.execute_query(query)
            # インデックス作成
            self.db.execute_query("CREATE INDEX IF NOT EXISTS idx_session_token ON user_sessions(session_token)")
            self.db.execute_query("CREATE INDEX IF NOT EXISTS idx_session_expires ON user_sessions(expires_at)")
        except Exception as e:
            print(f"Session table init error: {e}")
    
    def generate_session_token(self, user_id):
        """セッショントークンの生成"""
        import secrets
        timestamp = str(datetime.utcnow().timestamp())
        random_part = secrets.token_hex(16)
        raw_token = f"{user_id}_{timestamp}_{random_part}"
        return hashlib.sha256(raw_token.encode()).hexdigest()
    
    def create_session(self, user_id, user_data, expires_hours=24):
        """新しいセッションの作成"""
        session_token = self.generate_session_token(user_id)
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        # 既存のセッションをクリーンアップ
        self.cleanup_user_sessions(user_id)
        
        if self.db.db_type == 'postgresql':
            query = """
            INSERT INTO user_sessions (user_id, session_token, user_data, expires_at)
            VALUES (%s, %s, %s, %s)
            """
            params = (user_id, session_token, json.dumps(user_data), expires_at)
        else:
            query = """
            INSERT INTO user_sessions (user_id, session_token, user_data, expires_at)
            VALUES (?, ?, ?, ?)
            """
            params = (user_id, session_token, json.dumps(user_data), expires_at.isoformat())
        
        try:
            self.db.execute_query(query, params)
            return session_token
        except Exception as e:
            print(f"Session creation error: {e}")
            return None
    
    def get_session_data(self, session_token):
        """セッションデータの取得"""
        if not session_token:
            return None
            
        if self.db.db_type == 'postgresql':
            query = """
            SELECT user_id, user_data, expires_at 
            FROM user_sessions 
            WHERE session_token = %s AND expires_at > NOW()
            """
        else:
            query = """
            SELECT user_id, user_data, expires_at 
            FROM user_sessions 
            WHERE session_token = ? AND expires_at > datetime('now')
            """
        
        try:
            result = self.db.execute_query(query, (session_token,))
            if result:
                session_data = result[0]
                # アクセス時間を更新
                self.update_last_accessed(session_token)
                return {
                    'user_id': session_data['user_id'],
                    'user_data': json.loads(session_data['user_data']),
                    'expires_at': session_data['expires_at']
                }
        except Exception as e:
            print(f"Session retrieval error: {e}")
        
        return None
    
    def update_last_accessed(self, session_token):
        """最終アクセス時間の更新"""
        if self.db.db_type == 'postgresql':
            query = "UPDATE user_sessions SET last_accessed = NOW() WHERE session_token = %s"
        else:
            query = "UPDATE user_sessions SET last_accessed = datetime('now') WHERE session_token = ?"
        
        try:
            self.db.execute_query(query, (session_token,))
        except Exception as e:
            print(f"Session update error: {e}")
    
    def extend_session(self, session_token, hours=24):
        """セッションの延長"""
        new_expires = datetime.utcnow() + timedelta(hours=hours)
        
        if self.db.db_type == 'postgresql':
            query = "UPDATE user_sessions SET expires_at = %s WHERE session_token = %s"
            params = (new_expires, session_token)
        else:
            query = "UPDATE user_sessions SET expires_at = ? WHERE session_token = ?"
            params = (new_expires.isoformat(), session_token)
        
        try:
            self.db.execute_query(query, params)
        except Exception as e:
            print(f"Session extension error: {e}")
    
    def delete_session(self, session_token):
        """セッションの削除（ログアウト）"""
        query = "DELETE FROM user_sessions WHERE session_token = %s" if self.db.db_type == 'postgresql' else "DELETE FROM user_sessions WHERE session_token = ?"
        try:
            self.db.execute_query(query, (session_token,))
        except Exception as e:
            print(f"Session deletion error: {e}")
    
    def cleanup_user_sessions(self, user_id, keep_recent=3):
        """ユーザーの古いセッションをクリーンアップ"""
        if self.db.db_type == 'postgresql':
            query = """
            DELETE FROM user_sessions 
            WHERE user_id = %s AND id NOT IN (
                SELECT id FROM user_sessions 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            )
            """
        else:
            query = """
            DELETE FROM user_sessions 
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM user_sessions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            )
            """
        
        try:
            self.db.execute_query(query, (user_id, user_id, keep_recent))
        except Exception as e:
            print(f"Session cleanup error: {e}")
    
    def cleanup_expired_sessions(self):
        """期限切れセッションの一括削除"""
        if self.db.db_type == 'postgresql':
            query = "DELETE FROM user_sessions WHERE expires_at < NOW()"
        else:
            query = "DELETE FROM user_sessions WHERE expires_at < datetime('now')"
        
        try:
            result = self.db.execute_query(query)
            if result:
                print(f"Cleaned up {result} expired sessions")
        except Exception as e:
            print(f"Session cleanup error: {e}")

def persistent_login_required(f):
    """データベースベースのログイン確認デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import current_app
        
        session_manager = getattr(current_app, 'session_manager', None)
        if not session_manager:
            return redirect(url_for('auth.login'))
        
        # ブラウザからセッショントークンを取得
        session_token = session.get('session_token')
        session_data = session_manager.get_session_data(session_token)
        
        if not session_data:
            # セッションが無効な場合はログインページへ
            session.clear()
            flash('セッションが期限切れです。再度ログインしてください。', 'warning')
            return redirect(url_for('auth.login'))
        
        # セッションデータをFlaskセッションに復元
        for key, value in session_data['user_data'].items():
            session[key] = value
        
        # アクティブなユーザーのセッションを延長
        session_manager.extend_session(session_token)
        
        return f(*args, **kwargs)
    
    return decorated_function

def create_persistent_session(session_manager, user_id, user_data):
    """永続的セッションの作成"""
    session_token = session_manager.create_session(user_id, user_data)
    if session_token:
        session['session_token'] = session_token
        session.permanent = True
        return True
    return False

def destroy_persistent_session(session_manager):
    """永続的セッションの削除"""
    session_token = session.get('session_token')
    if session_token:
        session_manager.delete_session(session_token)
    session.clear()
