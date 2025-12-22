# FE Master - AWS Docker デプロイメント

## 🐳 Docker環境について

このプロジェクトはDocker化されており、以下の環境で動作可能です：
- ローカル開発環境（SQLite + Redis）
- AWS本番環境（PostgreSQL + ElastiCache）

### 🚀 クイックスタート

```bash
# 1. リポジトリをクローン
git clone https://github.com/d01ki/FE-master.git
cd FE-master

# 2. Dockerで起動
docker-compose up -d

# 3. ブラウザでアクセス
open http://localhost:5000
```

### 📁 ファイル構成

```
├── Dockerfile              # メインアプリケーション
├── docker-compose.yml      # 開発環境用構成
├── .dockerignore           # Dockerビルド除外設定
├── .env.docker            # Docker開発環境用変数
└── .env.aws.example       # AWS本番環境テンプレート
```

### 🔧 AWS デプロイメント

#### 1. ECS (推奨)
```bash
# イメージビルドとプッシュ
docker build -t fe-master .
docker tag fe-master:latest your-account.dkr.ecr.region.amazonaws.com/fe-master:latest
docker push your-account.dkr.ecr.region.amazonaws.com/fe-master:latest
```

#### 2. EC2 + Docker
```bash
# EC2インスタンスでDockerをインストール後
git clone https://github.com/d01ki/FE-master.git
cd FE-master
cp .env.aws.example .env
# .envファイルを本番用に編集
docker-compose --profile production up -d
```

### 🗄️ データベース設定

#### 開発環境（SQLite）
```yaml
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///fe_exam.db
```

#### 本番環境（AWS RDS PostgreSQL）
```yaml
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### 📋 必要なAWSリソース

1. **ECR** - Dockerイメージレジストリ
2. **ECS** - コンテナ実行環境
3. **RDS** - PostgreSQLデータベース
4. **ElastiCache** - Redisキャッシュ
5. **Application Load Balancer** - ロードバランサー
6. **Route 53** - DNS管理

### 🔒 セキュリティ設定

本番環境では以下の環境変数を必ず設定してください：

```bash
SECRET_KEY=cryptographically-strong-secret-key
ADMIN_PASSWORD=secure-admin-password
DATABASE_URL=postgresql://user:password@host:5432/db
REDIS_URL=redis://cache-host:6379
```

### 🔍 ヘルスチェック

アプリケーションには以下のヘルスチェックエンドポイントがあります：
- `GET /` - アプリケーションが正常に動作しているかチェック

### 📊 監視とログ

- CloudWatchでログとメトリクスを監視
- ECSタスクのヘルスチェックでアプリケーション状態を監視
- ALBのヘルスチェックでロードバランシング

### 🚨 トラブルシューティング

1. **データベース接続エラー**
   ```bash
   # データベース設定を確認
   echo $DATABASE_URL
   ```

2. **Redis接続エラー**
   ```bash
   # Redis設定を確認
   echo $REDIS_URL
   ```

3. **ポート設定エラー**
   ```bash
   # ポート設定を確認
   echo $PORT
   ```