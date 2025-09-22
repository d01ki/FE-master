<div align="center">

# 🎓 FE Master

### 基本情報技術者試験 学習アプリケーション

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**効率的な学習で基本情報技術者試験の合格を目指す**

</div>

---

## ✨ 特徴

<table>
<tr>
<td width="33%" align="center">

### 🎯 ランダム問題
毎日異なる問題で<br>飽きずに学習

</td>
<td width="33%" align="center">

### 📊 ジャンル別演習
苦手分野を<br>集中的に克服

</td>
<td width="33%" align="center">

### 📝 過去問演習
本番形式で<br>実力を確認

</td>
</tr>
</table>

### 🚀 主な機能

- **📱 レスポンシブデザイン** - PC・スマホどちらでも快適に学習
- **📊 学習履歴管理** - あなたの進捗を詳細に追跡
- **🖼️ 画像対応** - 図表付き問題も完全サポート
- **🔒 ユーザー認証** - 個人の学習データを安全に保管
- **🏆 ランキング・実績システム** - ゲーミフィケーションで学習を楽しく

---

## 🛠️ 技術スタック

<div align="center">

| カテゴリ | 技術 |
|:---:|:---|
| **Backend** | Python, Flask |
| **Database** | PostgreSQL, SQLite |
| **Frontend** | HTML5, Tailwind CSS, JavaScript |
| **Deployment** | Render.com |

</div>

---

## 🚀 クイックスタート

### ローカル開発環境の構築

```bash
# リポジトリをクローン
git clone https://github.com/d01ki/FE-master.git
cd FE-master

# 仮想環境を作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt

# 環境変数を設定（.envファイルを作成）
cp .env.example .env
# .envファイルを編集して必要な設定を行う

# アプリケーションを起動
python app.py
```

🎉 http://localhost:5002 でアクセスできます！

---

## 🌐 本番環境へのデプロイ（Render）

### 1. 必要な環境変数の設定

Renderのダッシュボードで以下の環境変数を設定してください：

```bash
# 必須の環境変数
SECRET_KEY=<ランダムな長い文字列>
ADMIN_PASSWORD=<強力なパスワード>
DATABASE_URL=<PostgreSQLのURL>

# オプション（推奨）
FLASK_ENV=production
```

### 2. データベースのマイグレーション

初回デプロイ時、またはDBスキーマ変更後：

**方法1: Renderのシェルから実行**
```bash
# Renderダッシュボード → Shell を開いて実行
python
>>> from database import DatabaseManager
>>> from app import app
>>> db_manager = DatabaseManager(app.config)
>>> db_manager.init_database()
>>> exit()
```

**方法2: Build Commandに追加**
```bash
# Renderの設定画面で Build Command を設定
pip install -r requirements.txt && python -c "from database import DatabaseManager; db = DatabaseManager({'DATABASE_URL': __import__('os').environ.get('DATABASE_URL')}); db.init_database()"
```

### 3. セキュリティチェックリスト

- [ ] `SECRET_KEY` は強力でランダムな値に設定済み
- [ ] `ADMIN_PASSWORD` はデフォルト値から変更済み
- [ ] `DATABASE_URL` は本番用PostgreSQLに接続
- [ ] HTTPSが有効化されている（Renderは自動設定）
- [ ] `.env` ファイルは `.gitignore` に追加されている

---

## 🔐 セキュリティに関する注意事項

### コミット履歴からの機密情報削除

もしコミット履歴にパスワードなどの機密情報が含まれている場合：

```bash
# git-filter-repoを使用して履歴から削除
pip install git-filter-repo
git filter-repo --path app.py --invert-paths
```

⚠️ **注意**: これはGitの履歴を書き換える危険な操作です。実行前に必ずバックアップを取ってください。

### 推奨されるセキュリティ対策

1. **環境変数の使用**: すべての機密情報は環境変数で管理
2. **HTTPS強制**: 本番環境では必ずHTTPSを使用
3. **定期的なパスワード変更**: 管理者パスワードは定期的に変更
4. **依存パッケージの更新**: セキュリティパッチは速やかに適用

---

## 📊 システムアーキテクチャ

詳細なシステム構成図は [ARCHITECTURE.md](docs/ARCHITECTURE.md) をご参照ください。

---

## 🤝 貢献

プルリクエストを歓迎します！

1. フォークする
2. ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. プッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

---

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

---

## 🐛 トラブルシューティング

### よくある問題と解決方法

#### ログインできない（user1などの既存ユーザー）

**原因**: SQLiteからPostgreSQLへの移行により、データベースが空になった

**解決策**:
1. 新しいユーザーを作成してログイン
2. または、以前のSQLiteデータをPostgreSQLにインポート

#### マイグレーションエラー

**原因**: データベーススキーマが最新でない

**解決策**:
```bash
# Renderのシェルから実行
python -c "from app import db_manager; db_manager.init_database()"
```

---

<div align="center">

**Made with ❤️ by FE Master Team**

⭐ このプロジェクトが役に立ったら、スターをお願いします！

</div>
