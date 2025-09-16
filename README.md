# FE Master - 基本情報技術者試験学習アプリ

PostgreSQL対応のユーザー認証機能付き基本情報技術者試験学習アプリ

## 🚀 新機能

### ユーザー認証システム
- **ユーザー登録・ログイン機能**
- **セッション管理**
- **ユーザー別学習履歴**
- **管理者権限システム**

### セキュリティ
- パスワードハッシュ化
- セッションベース認証
- CSRF保護

## 📋 機能

- **ユーザー管理**: 登録・ログイン・ログアウト
- **ジャンル別演習**: 分野ごとに集中学習
- **ランダム問題**: 手軽に問題練習
- **学習履歴**: 個人の進捗管理
- **レスポンシブデザイン**: 全デバイス対応
- **データベース**: PostgreSQL/SQLite両対応

## 🛠️ セットアップ

### 必要要件
- Python 3.8+
- PostgreSQL (本番環境)
- SQLite (開発環境)

### インストール

```bash
git clone https://github.com/d01ki/FE-master.git
cd FE-master
git checkout user-auth-postgresql

# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# アプリケーション起動
python app_postgresql.py
```

## 🔐 認証情報

### デフォルトアカウント
- **管理者**: `admin` / `admin123`

### 新規ユーザー登録
1. `/register` にアクセス
2. ユーザー名（3文字以上）
3. パスワード（6文字以上）
4. パスワード確認

## 🌐 デプロイ（Render）

### 環境変数
```
DATABASE_URL=your_postgresql_url
SECRET_KEY=your_secret_key
```

### 設定
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python app_postgresql.py`

## 📊 データベース構造

### テーブル
- **users**: ユーザー情報
- **questions**: 問題データ
- **user_answers**: ユーザー回答履歴

## 🎯 使用方法

1. **ログイン**: `/login` でログイン
2. **ダッシュボード**: `/dashboard` で学習状況確認
3. **問題演習**: ジャンル別またはランダム
4. **履歴確認**: `/history` で過去の回答を確認

## 📁 プロジェクト構造

```
FE-master/
├── app_postgresql.py      # メインアプリケーション
├── auth.py               # 認証モジュール
├── database.py           # データベース管理
├── requirements.txt      # 依存関係
├── templates/
│   ├── auth/            # 認証テンプレート
│   │   ├── login.html
│   │   └── register.html
│   └── dashboard.html   # ダッシュボード
└── json_questions/      # 問題データ
```

## 🔧 開発者向け

### ローカル開発
- SQLiteを使用（データベースファイル自動作成）
- `python app_postgresql.py` で起動
- デフォルト管理者アカウントが自動作成

### 本番環境
- PostgreSQLを使用
- 環境変数 `DATABASE_URL` が必要
- セキュリティキー設定必須

## 📝 ライセンス

MIT License

## 🤝 コントリビューション

Issue、Pull Request お待ちしています！

---

**基本情報技術者試験の合格を応援します！** 🎯📚
