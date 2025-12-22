#!/bin/bash
# データベースバックアップスクリプト

# 設定
DB_FILE="fe_exam.db"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/fe_exam_backup_$TIMESTAMP.db"

# バックアップディレクトリ作成
mkdir -p $BACKUP_DIR

# SQLiteデータベースのバックアップ作成
if [ -f "$DB_FILE" ]; then
    echo "=== データベースバックアップ開始 ==="
    echo "ソース: $DB_FILE"
    echo "保存先: $BACKUP_FILE"
    
    # ファイルコピーでバックアップ
    cp "$DB_FILE" "$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        echo "✅ バックアップ完了: $BACKUP_FILE"
        
        # バックアップファイルのサイズ確認
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo "バックアップサイズ: $BACKUP_SIZE"
        
        # 過去7日より古いバックアップファイルを削除
        find $BACKUP_DIR -name "fe_exam_backup_*.db" -mtime +7 -delete
        echo "古いバックアップファイルを削除しました"
        
    else
        echo "❌ バックアップ失敗"
        exit 1
    fi
else
    echo "❌ データベースファイルが見つかりません: $DB_FILE"
    exit 1
fi

echo "=== バックアップ一覧 ==="
ls -la $BACKUP_DIR/fe_exam_backup_*.db 2>/dev/null || echo "バックアップファイルがありません"