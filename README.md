# 基本情報技術者試験 学習アプリ（認証統合版）

## 概要

基本情報技術者試験の学習をサポートするWebアプリケーションです。
mainブランチの全機能（模擬試験、ランダム問題、履歴、管理者画面）にユーザー認証システムを統合しました。

## 主な機能

### ユーザー機能
- **ユーザー登録・ログイン**: セキュアな認証システム
- **ダッシュボード**: 学習状況の一覧表示
- **ランダム問題**: データベースからランダムに問題を出題
- **ジャンル別演習**: ジャンル毎の集中学習
- **模擬試験**: 年度別・制限時間付きの本格模擬試験
- **学習履歴**: 解答履歴と成績の分析

### 管理者機能
- **問題管理**: JSON形式での問題データのアップロード
- **データベース管理**: 問題データの初期化・管理
- **統計情報**: 問題数、ジャンル数等の確認

## 技術スタック

- **Backend**: Flask (Python)
- **Database**: PostgreSQL (本番環境) / SQLite (開発環境)
- **Authentication**: Flask-Session + Werkzeug Security
- **Frontend**: HTML5, Tailwind CSS, JavaScript
- **Deployment**: Render.com

## デプロイ

### Render.com での設定

1. **Web Service として作成**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`

2. **環境変数の設定**
   ```
   DATABASE_URL=<PostgreSQL接続URL>
   SECRET_KEY=<安全なランダム文字列>
   ADMIN_PASSWORD=<管理者パスワード>
   ```

3. **PostgreSQLデータベース**
   - Render PostgreSQL サービスを作成
   - DATABASE_URL を自動設定

## ローカル開発

```bash
# 依存関係のインストール
pip install -r requirements.txt

# ローカル実行（SQLite使用）
python app.py
```

## ファイル構成

```
├── app.py                    # メインアプリケーション
├── auth.py                   # 認証システム
├── database.py               # データベース管理
├── question_manager.py       # 問題管理システム
├── utils.py                  # ユーティリティ関数
├── requirements.txt          # 依存関係
├── templates/               # HTMLテンプレート
│   ├── auth/               # 認証関連テンプレート
│   ├── base.html           # ベーステンプレート
│   ├── dashboard.html      # ダッシュボード
│   ├── question.html       # 問題表示
│   ├── mock_exam_*.html    # 模擬試験関連
│   ├── history.html        # 学習履歴
│   └── admin.html          # 管理画面
├── static/                 # 静的ファイル
└── json_questions/         # JSON問題データ
```

## データベース設計

### Users テーブル
- ユーザー情報と認証データ
- 管理者フラグ

### Questions テーブル
- 問題文、選択肢、正解、解説
- ジャンル分類

### User_answers テーブル
- ユーザーの解答履歴
- 正解/不正解の記録

## 使用方法

1. **初回設定**
   - アプリにアクセス
   - ユーザー登録
   - 管理者による問題データのアップロード

2. **学習開始**
   - ログイン後、ダッシュボードから各機能にアクセス
   - ランダム問題や模擬試験で学習
   - 履歴画面で進捗確認

3. **問題データ形式**
   ```json
   [
     {
       "question_id": "Q001",
       "question_text": "問題文",
       "choices": {
         "ア": "選択肢1",
         "イ": "選択肢2",
         "ウ": "選択肢3",
         "エ": "選択肢4"
       },
       "correct_answer": "ア",
       "explanation": "解説文",
       "genre": "基礎理論"
     }
   ]
   ```

## セキュリティ機能

- パスワードハッシュ化（Werkzeug Security）
- セッション管理
- CSRF保護
- 管理者権限の分離

## ライセンス

MIT License

## 更新履歴

- v2.0: ユーザー認証システム統合
- v1.0: 基本機能実装（mainブランチ）