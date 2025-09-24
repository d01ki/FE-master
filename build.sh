#!/usr/bin/env bash
# Renderのビルドスクリプト

set -e  # エラーが発生したら即座に停止

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🗄️ Initializing database..."
python - << 'PY'
from config import Config
from database import DatabaseManager

db_config = Config.get_db_config()
print(f"Database Type: {db_config['DATABASE_TYPE']}")
db = DatabaseManager(db_config)
db.init_database()
print('✅ Database initialized successfully!')
PY

echo "✅ Build completed successfully!"
