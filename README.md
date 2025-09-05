# FE-Master - 基本情報技術者過去問アプリ

基本情報技術者試験の過去問を効率的に学習できるWebアプリケーションです。

## 主要機能

- 📚 分野別問題学習
- ⏱️ 模擬試験（タイマー付き）
- 📊 学習ダッシュボード
- 🎯 類似問題推薦
- 👤 ユーザー認証・履歴管理

## 技術スタック

### バックエンド
- FastAPI (Python)
- PostgreSQL + pgvector
- JWT認証
- OpenAI Embeddings

### フロントエンド
- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router
- Axios

## 開発セットアップ

### 前提条件
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### バックエンドセットアップ

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .envファイルを編集してデータベース接続情報等を設定

# データベースマイグレーション
alembic upgrade head

# 開発サーバー起動
uvicorn app.main:app --reload
```

### フロントエンドセットアップ

```bash
cd frontend
npm install
npm run dev
```

### データベースセットアップ

```sql
-- PostgreSQLでpgvector拡張を有効化
CREATE EXTENSION IF NOT EXISTS vector;
```

## デプロイ

### Render

1. Renderでアカウント作成
2. PostgreSQLデータベース作成
3. Web Serviceを作成し、このリポジトリを接続
4. 環境変数を設定

### 環境変数

```
DATABASE_URL=postgresql://...
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-key
ALLOWED_ORIGINS=https://your-frontend-domain.com
```

## API ドキュメント

開発サーバー起動後、以下のURLでSwagger UIにアクセス可能：
- http://localhost:8000/docs

## ライセンス

MIT License

## 著作権・法的注意

過去問のテキストは著作物である可能性があります。利用規約と著作権表示を確認の上、適切にご利用ください。