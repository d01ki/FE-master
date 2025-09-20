# Render デプロイガイド

## 環境変数設定

Renderの管理画面で以下を設定：

```
DATABASE_TYPE=postgresql
DATABASE_URL=<RenderのPostgreSQL接続URL>
SECRET_KEY=<ランダムな秘密鍵>
```

## デプロイ手順

1. **PostgreSQLデータベースを作成**
   - RenderダッシュボードでPostgreSQLインスタンスを作成
   - Internal Database URLをコピー

2. **Web Serviceを作成**
   - GitHubリポジトリを選択
   - `main`ブランチを選択
   - 環境変数を設定

3. **初回起動後**
   - 管理者アカウントでログイン
   - JSON問題ファイルをアップロード

## データベース機能

- **自動初期化**: アプリ起動時にテーブルを自動作成
- **フォールバック**: PostgreSQLが使えない場合はSQLiteに自動切り替え
- **画像サポート**: image_urlカラムで画像表示対応

## 注意事項

- `SECRET_KEY`は安全なランダム文字列を使用してください
- 初回起動時、デフォルト管理者アカウントが作成されます
- **本番環境では必ず管理者パスワードを変更してください**