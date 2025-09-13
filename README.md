# 基本情報技術者試験 学習アプリ

Flask + PostgreSQL + Tailwind CSSを使用した基本情報技術者試験の学習プラットフォームです。

## 新機能（user-auth-postgresql ブランチ）

### ✅ 完了済み
- **ユーザー認証機能**
  - 新規登録・ログイン・ログアウト
  - パスワードのハッシュ化（bcrypt）
  - ユーザーデータの分離
- **PostgreSQL対応**
  - SQLiteからPostgreSQLへの移行
  - ユーザー毎のデータ管理
- **UI改善**
  - フッターから技術スタック表記を削除
  - ユーザー認証用のログイン・登録画面追加
  - レスポンシブデザイン対応

### 🚀 主な機能

1. **ユーザー管理**
   - 安全な新規登録（パスワード強度チェック付き）
   - ログイン認証
   - ユーザー毎のデータ分離

2. **問題管理**
   - JSON形式での問題アップロード
   - 問題の重複チェック
   - ジャンル別問題整理

3. **学習機能**
   - ジャンル別演習
   - 模擬試験
   - 個人の学習履歴追跡

4. **管理機能**
   - 管理者専用画面
   - 問題アップロード
   - ユーザー統計表示

## セットアップ

### 前提条件
- Python 3.8+
- PostgreSQL 12+

### インストール

1. リポジトリをクローン
```bash
git clone https://github.com/d01ki/FE-master.git
cd FE-master
git checkout user-auth-postgresql
```

2. 仮想環境を作成・有効化
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 依存関係をインストール
```bash
pip install -r requirements.txt
```

4. PostgreSQLデータベースを設定
```sql
CREATE DATABASE fe_exam_db;
CREATE USER fe_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE fe_exam_db TO fe_user;
```

5. 環境変数を設定
```bash
# .env ファイルを作成
echo "DATABASE_URL=postgresql://fe_user:your_password@localhost:5432/fe_exam_db" > .env
echo "SECRET_KEY=your-secret-key-here" >> .env
echo "ADMIN_PASSWORD=your-admin-password" >> .env
```

6. アプリケーションを起動
```bash
python app.py
```

## 使用方法

### 一般ユーザー
1. `/register` から新規登録
2. `/login` からログイン
3. ダッシュボードで学習状況を確認
4. ジャンル別演習や模擬試験を実施

### 管理者
1. `/admin/login` から管理者ログイン
2. JSON形式の問題ファイルをアップロード
3. ユーザー統計を確認

## データベース構造

### テーブル構成
- `users`: ユーザー情報
- `questions`: 問題データ
- `user_answers`: ユーザーの解答履歴

## デプロイ

### Render.com での展開

1. `DATABASE_URL` を PostgreSQL の接続URLに設定
2. `SECRET_KEY` を安全なランダム文字列に設定
3. `ADMIN_PASSWORD` を管理者パスワードに設定

## 変更点（fix-ui-issues から）

- ✅ PostgreSQL対応（SQLiteから移行）
- ✅ ユーザー認証システム追加
- ✅ ユーザー毎のデータ分離
- ✅ サンプル問題生成機能を削除
- ✅ フッターのFlask + SQLite等の表記を削除
- ✅ 新規登録・ログイン画面追加
- ✅ セキュリティ強化（bcryptによるパスワードハッシュ化）

## 技術スタック

- **Backend**: Flask 2.3.3
- **Database**: PostgreSQL
- **Authentication**: Flask-Login + bcrypt
- **Frontend**: Tailwind CSS + Font Awesome
- **Deployment**: Gunicorn

## ライセンス

MIT License

## 貢献

プルリクエストやイシューの報告は歓迎します。

---

**注意**: このブランチ（user-auth-postgresql）は本格的なユーザー認証とPostgreSQL対応を含む改良版です。本番環境での使用を想定しています。
