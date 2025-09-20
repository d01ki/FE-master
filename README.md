# 🎓 基本情報技術者試験 学習アプリ

基本情報技術者試験の学習をサポートするWebアプリケーションです。

## ✨ 機能

- 🎲 **ランダム問題練習**: ランダムに問題を出題
- 📚 **ジャンル別演習**: 苦手分野を集中的に学習
- 📋 **過去問試験**: 本番形式で実力確認
- 👑 **達成度管理**: 習得状況を視覚化
- 🏆 **ランキング機能**: 他のユーザーと競い合う
- 📈 **学習履歴**: 学習進捗を追跡

## 🚀 Renderへのデプロイ手順

### 1. PostgreSQLデータベースの作成

1. Renderダッシュボードで **New +** → **PostgreSQL** を選択
2. データベース名を入力（例: `fe-exam-db`）
3. **Create Database** をクリック
4. **Internal Database URL** をコピー（後で使用）

### 2. Webサービスの作成

1. Renderダッシュボードで **New +** → **Web Service** を選択
2. GitHubリポジトリを連携
3. 以下の設定を入力:

   - **Name**: `fe-exam-app`（任意）
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`

### 3. 環境変数の設定

RenderのWebサービス設定で、**Environment** タブに移動し、以下の環境変数を追加:

```bash
# 必須設定
DATABASE_URL=<PostgreSQLのInternal Database URL>
SECRET_KEY=<ランダムな長い文字列>

# 初回起動時のみ（管理者アカウント作成後は削除可）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<安全なパスワード>

# その他の設定
FLASK_ENV=production
DEBUG=False
PORT=10000
```

### 4. デプロイ

1. **Create Web Service** をクリック
2. デプロイが完了するまで待つ
3. アプリケーションURLにアクセス

### 5. 初回セットアップ

1. アプリケーシャンにアクセス
2. 管理者アカウントでログイン（`ADMIN_USERNAME`と`ADMIN_PASSWORD`）
3. 管理画面から問題データをアップロード
4. **セキュリティのため**: セットアップ完了後、`ADMIN_PASSWORD`環境変数を削除

## 🔒 セキュリティ機能

- ✅ パスワードはハッシュ化されて保存
- ✅ 環境変数で機密情報を管理
- ✅ "admin"ユーザー名の新規登録をブロック
- ✅ セッションベースの認証

## 🛠️ ローカル開発

### 前提条件

- Python 3.8+
- PostgreSQL（本番環境）またはSQLite（開発環境）

### セットアップ

1. リポジトリをクローン:
```bash
git clone https://github.com/yourusername/FE-master.git
cd FE-master
```

2. 仮想環境を作成:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 依存パッケージをインストール:
```bash
pip install -r requirements.txt
```

4. `.env`ファイルを作成（`.env.example`をコピー）:
```bash
cp .env.example .env
```

5. `.env`を編集して設定を更新

6. アプリケーションを起動:
```bash
python app.py
```

7. ブラウザで `http://localhost:5002` にアクセス

## 📝 環境変数の詳細

| 変数名 | 説明 | 必須 |
|---------|------|------|
| `DATABASE_URL` | データベース接続URL | ◯ |
| `SECRET_KEY` | Flaskのsecret key | ◯ |
| `ADMIN_USERNAME` | 管理者ユーザー名 | 初回のみ |
| `ADMIN_PASSWORD` | 管理者パスワード | 初回のみ |
| `FLASK_ENV` | 環境（production/development） | - |
| `DEBUG` | デバッグモード | - |
| `PORT` | ポート番号 | - |

## 💡 使い方

1. **ユーザー登録**: 新規アカウントを作成
2. **問題演習**: ランダムまたはジャンル別で問題を解く
3. **過去問試験**: 本番形式で試験を受ける
4. **達成度確認**: 習得状況をチェック
5. **ランキング**: 他の学習者と比較

## 👥 貢献

Pull Requestを歓迎します！大きな変更の場合は、まずIssueで討論してください。

## 📝 ライセンス

MIT License

## 🚀 技術スタック

- **Backend**: Flask (Python)
- **Database**: PostgreSQL / SQLite
- **Frontend**: Tailwind CSS, Alpine.js
- **Deployment**: Render
