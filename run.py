#!/usr/bin/env python3
"""
基本情報技術者試験 学習アプリ
起動スクリプト

使用方法:
    python run.py [--port PORT] [--host HOST] [--debug]
    
例:
    python run.py
    python run.py --port 8080
    python run.py --host 0.0.0.0 --port 5000 --debug
"""

import argparse
import os
import sys
from app import app

def main():
    """アプリケーションを起動"""
    parser = argparse.ArgumentParser(description='基本情報技術者試験 学習アプリ')
    parser.add_argument('--host', default='localhost', help='ホストアドレス (デフォルト: localhost)')
    parser.add_argument('--port', type=int, default=5000, help='ポート番号 (デフォルト: 5000)')
    parser.add_argument('--debug', action='store_true', help='デバッグモードで起動')
    
    args = parser.parse_args()
    
    # 環境変数の設定
    if args.debug:
        os.environ['FLASK_ENV'] = 'development'
        os.environ['FLASK_DEBUG'] = '1'
    
    print("=" * 60)
    print("🎓 基本情報技術者試験 学習アプリ")
    print("=" * 60)
    print(f"📡 ホスト: {args.host}")
    print(f"🔌 ポート: {args.port}")
    print(f"🐛 デバッグモード: {'有効' if args.debug else '無効'}")
    print(f"🌐 URL: http://{args.host}:{args.port}")
    print("=" * 60)
    print("📝 管理者パスワード: fe2025admin")
    print("🛑 停止するには Ctrl+C を押してください")
    print("=" * 60)
    
    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=args.debug
        )
    except KeyboardInterrupt:
        print("\n\n🛑 アプリケーションを停止しました")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
