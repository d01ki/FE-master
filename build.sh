#!/usr/bin/env bash
# Renderのビルドスクリプト

set -e  # エラーが発生したら即座に停止

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🗄️ Initializing database..."
python -c "
from config import Config
from database import DatabaseManager

# Configクラスからデータベース設定を取得
db_config = Config.get_db_config()
print(f'Database Type: {db_config[\"DATABASE_TYPE\"]}')

db = DatabaseManager(db_config)
db.init_database()
print('✅ Database initialized successfully!')
"

echo "✅ Build completed successfully!"
