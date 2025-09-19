"""
ユーティリティ関数
共通で使用される関数をまとめたモジュール
"""

import re
import sqlite3

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
        
        # ソート用のキーを追加（年度と季節で並び替え）
        season_order = 0 if season == "spring" else 1 if season == "autumn" else 2
        sort_key = year * 10 + season_order
        
        return {
            'filename': filename,
            'year': year,
            'era_year': era_year,
            'season': season,
            'season_jp': season_jp,
            'display_name': f'{year}年{season_jp}',
            'sort_key': sort_key
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
