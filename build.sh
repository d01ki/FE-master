#!/usr/bin/env bash
# Renderのビルドスクリプト

set -e  # エラーが発生したら即座に停止

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🗄️ Initializing database..."
python -c "
from database import DatabaseManager
import os

config = {
    'DATABASE_URL': os.environ.get('DATABASE_URL'),
    'DATABASE_TYPE': 'postgresql' if os.environ.get('DATABASE_URL') else 'sqlite',
    'DATABASE': 'fe_exam.db'
}

db = DatabaseManager(config)
db.init_database()
print('✅ Database initialized successfully!')
"

echo "✅ Build completed successfully!"
