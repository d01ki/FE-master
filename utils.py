"""
ユーティリティ関数
共通で使用される関数をまとめたモジュール
"""

import re
import sqlite3
from urllib.parse import urlparse

# PostgreSQLライブラリのインポート（エラー時は無視）
try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

def parse_filename_info(filename):
    """ファイル名から年度と期の情報を抽出"""
    pattern = r'(\d{4})r(\d{2})_[^_]+_[^_]+_(\w+)\.json'
    match = re.match(pattern, filename)
    if match:
        year = int(match.group(1))
        era_year = int(match.group(2))
        season = match.group(3)
        season_jp = "春期" if season == "spring" else "秋期" if season == "autumn" else season
        return {
            'year': year,
            'era_year': era_year,
            'season': season,
            'season_jp': season_jp,
            'display_name': f'{year}年{season_jp}'
        }
    return None

def is_postgresql(database_url):
    """PostgreSQLかどうかを判定"""
    return database_url and database_url.startswith('postgres') and PSYCOPG2_AVAILABLE

def get_db_connection(database_url=None, database_file=None):
    """データベース接続を取得"""
    if is_postgresql(database_url):
        conn = psycopg2.connect(database_url)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    else:
        conn = sqlite3.connect(database_file)
        conn.row_factory = sqlite3.Row
        return conn

def validate_image_url(url):
    """
    画像URLの妥当性を検証
    
    Args:
        url (str): 検証するURL
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if not url:
        return True, None  # 空のURLは許可（オプション項目）
    
    # 空白や無効な値をチェック
    if url.strip().lower() in ['null', 'none', '']:
        return True, None
    
    try:
        # URLの基本的な構造を検証
        parsed = urlparse(url)
        
        # スキームがhttpまたはhttpsであることを確認
        if parsed.scheme not in ['http', 'https']:
            return False, f"無効なURLスキーム: {parsed.scheme}（httpまたはhttpsのみ許可）"
        
        # ドメインが存在することを確認
        if not parsed.netloc:
            return False, "URLにドメインが含まれていません"
        
        # 許可されたドメインのリスト（必要に応じて拡張）
        allowed_domains = [
            'githubusercontent.com',
            'github.com',
            'imgur.com',
            'cloudinary.com',
            's3.amazonaws.com',
            'storage.googleapis.com',
            # アプリケーション独自のドメイン
            'fe-master.onrender.com',
            'localhost',
            '127.0.0.1'
        ]
        
        # ドメインの検証（部分一致を許可）
        domain_valid = any(allowed_domain in parsed.netloc for allowed_domain in allowed_domains)
        
        if not domain_valid:
            # 警告を返すが、エラーとはしない（柔軟性のため）
            return True, f"注意: {parsed.netloc} は信頼されたドメインリストに含まれていません"
        
        # 画像ファイル拡張子の検証（オプション）
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp']
        path_lower = parsed.path.lower()
        
        has_valid_extension = any(path_lower.endswith(ext) for ext in valid_extensions)
        if not has_valid_extension and parsed.path:
            return True, f"注意: URLに画像ファイル拡張子が含まれていません"
        
        return True, None
        
    except Exception as e:
        return False, f"URL検証エラー: {str(e)}"

def sanitize_image_url(url):
    """
    画像URLをサニタイズ
    
    Args:
        url (str): サニタイズするURL
    
    Returns:
        str or None: サニタイズされたURL、または無効な場合はNone
    """
    if not url:
        return None
    
    # 空白を削除
    url = url.strip()
    
    # 無効な値をNoneに変換
    if url.lower() in ['null', 'none', '']:
        return None
    
    # 基本的なXSS対策: スクリプトタグなどを含むURLを拒否
    dangerous_patterns = [
        'javascript:',
        'data:text/html',
        '<script',
        'onerror=',
        'onclick=',
    ]
    
    url_lower = url.lower()
    for pattern in dangerous_patterns:
        if pattern in url_lower:
            return None
    
    return url
