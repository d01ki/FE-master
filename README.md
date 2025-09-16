# FE Master - 基本情報技術者試験学習アプリ

PostgreSQL対応のユーザー認証機能付き基本情報技術者試験学習アプリ

## 🚀 新機能

### ユーザー認証システム
- **ユーザー登録・ログイン機能**
- **セッション管理（Flask-Login）**
- **ユーザー別学習履歴**
- **管理者権限システム**

### セキュリティ
- パスワードハッシュ化（Werkzeug）
- セッションベース認証
- ログイン必須ページ保護

## 📋 機能

- **ユーザー管理**: 登録・ログイン・ログアウト
- **ダッシュボード**: 学習状況の可視化
- **ランダム問題**: 手軽に問題練習
- **問題演習**: サンプル問題での学習
- **学習履歴**: 個人の進捗管理（開発中）
- **管理機能**: 管理者向け統計・ユーザー管理
- **レスポンシブデザイン**: 全デバイス対応
- **データベース**: PostgreSQL/SQLite両対応

## 🛠️ セットアップ

### 必要要件
- Python 3.8+
- PostgreSQL (本番環境推奨)
- SQLite (開発環境・フォールバック)

### インストール

```bash
git clone https://github.com/d01ki/FE-master.git
cd FE-master
git checkout user-auth-postgresql

# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# 依存関係インストール
pip install -r requirements.txt

# アプリケーション起動
python app.py
```

## 🔐 認証情報

### デフォルトアカウント（自動作成）
- **管理者**: `admin` / `admin123`

### 新規ユーザー登録
1. `/register` にアクセス
2. ユーザー名（3文字以上）
3. パスワード（6文字以上）
4. パスワード確認
5. メールアドレス（任意）

## 🌐 デプロイ（Render/Heroku）

### 環境変数
```
DATABASE_URL=postgresql://username:password@host:port/database
SECRET_KEY=your_secret_key_here
```

### 設定
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python app.py`

## 📊 データベース構造

### テーブル（自動作成）
- **users**: ユーザー情報・権限
- **questions**: 問題データ
- **user_answers**: ユーザー回答履歴

### データベース対応
- **PostgreSQL**: 本番環境（自動検出）
- **SQLite**: 開発環境・フォールバック

## 🎯 使用方法

### 1. 初回アクセス
1. アプリケーションにアクセス
2. ログイン画面にリダイレクト
3. 新規登録またはデモアカウントでログイン

### 2. 学習開始
1. **ダッシュボード**: 学習状況を確認
2. **ランダム問題**: 問題を解いて学習
3. **管理機能**: 管理者は統計情報を確認

### 3. 機能利用
- ログアウトは右上のアイコンから
- モバイル表示では ☰ メニューから操作

## 📁 プロジェクト構造

```
FE-master/
├── app.py                    # メインアプリケーション
├── requirements.txt          # 依存関係
├── templates/
│   ├── auth/                # 認証テンプレート
│   │   ├── login.html       # ログイン画面
│   │   └── register.html    # 登録画面
│   ├── dashboard.html       # ダッシュボード
│   ├── question.html        # 問題表示
│   ├── admin.html          # 管理画面
│   └── base.html           # ベーステンプレート
└── json_questions/         # 問題データフォルダ
```

## 🔧 開発者向け情報

### ローカル開発
- SQLiteを自動使用（ファイル自動作成）
- `python app.py` で起動
- デフォルト管理者アカウント自動作成
- サンプル問題も自動作成

### 本番環境
- `DATABASE_URL`でPostgreSQL自動選択
- セキュリティキー設定必須
- テーブル自動作成
- 管理者アカウント自動作成

### 技術スタック
- **Backend**: Flask + Flask-Login
- **Database**: PostgreSQL (psycopg2-binary) / SQLite
- **Frontend**: Tailwind CSS + Font Awesome
- **Security**: Werkzeug (パスワードハッシュ)

## 🚨 重要な変更点

### ログイン機能追加により：
- **すべてのページがログイン必須**
- **未認証ユーザーは自動的にログイン画面へ**
- **セッション管理でログイン状態を保持**
- **管理者権限による機能制限**

### 削除予定ファイル
- `templates/login.html` (重複)
- `templates/register.html` (重複)
- `auth.py` (app.pyに統合)
- `database.py` (app.pyに統合)

## 📝 ライセンス

MIT License

## 🤝 コントリビューション

Issue、Pull Request お待ちしています！

---

**基本情報技術者試験の合格を応援します！** 🎯📚

### 🔗 リンク
- [デモサイト](https://fe-master.onrender.com) *(デプロイ時)*
- [GitHub](https://github.com/d01ki/FE-master)
