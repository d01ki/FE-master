# 🔧 環境変数設定

本番環境で設定が必要な環境変数の一覧です。

## 必須設定

### セキュリティ関連
```bash
SECRET_KEY=your-cryptographically-strong-secret-key-here
ADMIN_PASSWORD=your-secure-admin-password
```

### データベース設定
```bash
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://username:password@host:5432/database_name
```

### サーバー設定
```bash
FLASK_ENV=production
DEBUG=false
PORT=5000
HOST=0.0.0.0
```

## セキュリティ注意事項

⚠️ **重要**: 本番環境では以下を必ず変更してください：
- `SECRET_KEY`: 暗号化強度の高いランダムな文字列
- `ADMIN_PASSWORD`: 強固なパスワード
- PostgreSQLの認証情報

## 開発環境

開発時は `docker-compose.override.yml` で自動設定されるため、
環境変数の設定は不要です。