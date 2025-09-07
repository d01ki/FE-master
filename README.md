# 🎯 基本情報技術者試験 学習アプリ

基本情報技術者試験の効率的な学習を支援するWebアプリケーションです。

## ✨ 特徴

- **モダンなUI/UX**: グラスモーフィズムデザインで洗練されたインターフェース
- **ジャンル別演習**: 分野ごとに集中学習が可能
- **模擬試験機能**: 本番と同じ形式での実力測定
- **学習履歴**: 詳細な進捗管理と成績分析
- **レスポンシブ対応**: スマートフォン、タブレット、PCで最適表示
- **自動問題読み込み**: JSONファイルから問題を自動インポート

## 🚀 クイックスタート

### 1. リポジトリのクローン
```bash
git clone https://github.com/d01ki/FE-master.git
cd FE-master
```

### 2. 仮想環境の作成と有効化
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 依存関係のインストール
```bash
pip install Flask
```

### 4. アプリケーションの起動
```bash
python app.py
```

### 5. ブラウザでアクセス
```
http://127.0.0.1:5000
```

## 🔍 データベース診断・修復

JSONファイルが読み込まれない、または問題が表示されない場合は、診断スクリプトを実行してください：

### データベース状態の確認
```bash
python db_diagnostic.py
```

このスクリプトは以下を行います：
- ✅ データベースファイルの存在確認
- ✅ テーブル構造の確認
- ✅ 問題数とジャンル別統計の表示
- ✅ JSONファイルの検証
- ✅ 強制的な問題読み込み

### 問題の解決手順

1. **診断実行**:
   ```bash
   python db_diagnostic.py
   ```

2. **JSONファイル強制読み込み**:
   - 診断スクリプトで `y` を入力して強制読み込みを実行

3. **アプリケーション再起動**:
   ```bash
   python app.py
   ```

## 📁 プロジェクト構造

```
FE-master/
├── app.py                      # メインアプリケーション（SQLite用）
├── app_postgresql.py           # PostgreSQL対応版（Render用）
├── db_diagnostic.py            # データベース診断・修復スクリプト
├── requirements.txt            # Python依存関係
├── fe_exam.db                  # SQLiteデータベース（自動生成）
├── json_questions/             # 問題ファイル格納フォルダ
│   └── *.json                  # 問題データ（JSON形式）
├── templates/                  # HTMLテンプレート
│   ├── base.html              # ベースレイアウト
│   ├── dashboard.html         # ダッシュボード
│   ├── practice.html          # ジャンル別演習
│   ├── mock_exam_practice.html # 模擬試験
│   └── ...
└── static/                     # 静的ファイル（CSS、JS、画像）
```

## 🗄️ データベース構成

### SQLite（開発用）
- **ファイル**: `fe_exam.db`
- **自動作成**: アプリケーション初回起動時

### PostgreSQL（本番用）
- **Render**: 自動でPostgreSQLデータベースを使用
- **環境変数**: `DATABASE_URL`で接続情報を取得

### テーブル構造

#### questions テーブル
```sql
CREATE TABLE questions (
    id INTEGER PRIMARY KEY,
    question_id TEXT UNIQUE NOT NULL,
    question_text TEXT NOT NULL,
    choices TEXT NOT NULL,          -- JSON形式の選択肢
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    genre TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### user_answers テーブル
```sql
CREATE TABLE user_answers (
    id INTEGER PRIMARY KEY,
    question_id INTEGER,
    user_answer TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    answered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions (id)
);
```

## 📝 問題ファイル形式

`json_questions/` フォルダにJSONファイルを配置すると自動で読み込まれます。

### ファイル名例
- `2025r07_spring.json`
- `2024r06_autumn.json`
- `custom_questions.json`

### JSON形式
```json
[
  {
    "question_id": "Q001",
    "question_text": "アルゴリズムの計算量を表すビッグO記法について正しいものはどれか。",
    "choices": {
      "ア": "O(1)は定数時間を表し、最も効率的である",
      "イ": "O(n²)はO(n)より常に高速である",
      "ウ": "O(log n)は指数時間を表す",
      "エ": "ビッグO記法は最悪計算量のみを表現する"
    },
    "correct_answer": "ア",
    "explanation": "O(1)は定数時間を表し、入力サイズに関係なく一定時間で処理が完了するため最も効率的です。",
    "genre": "アルゴリズム"
  }
]
```

### 必須フィールド
- `question_text`: 問題文
- `choices`: 選択肢（ア、イ、ウ、エ）
- `correct_answer`: 正解（ア、イ、ウ、エのいずれか）

### 任意フィールド
- `question_id`: 問題ID（未指定時は自動生成）
- `explanation`: 解説文
- `genre`: ジャンル名（未指定時は「その他」）

## 🚀 Renderへのデプロイ

### 1. PostgreSQL対応
本プロジェクトはRenderでのデプロイに対応しています：

- **アプリケーション**: `app_postgresql.py`を使用
- **データベース**: PostgreSQLを自動選択
- **環境変数**: `DATABASE_URL`で接続

### 2. デプロイ手順
1. **Renderアカウント作成**: [render.com](https://render.com)
2. **PostgreSQLサービス作成**: 新しいPostgreSQLデータベースを作成
3. **Webサービス作成**: GitHubリポジトリを接続
4. **ビルド設定**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app_postgresql.py`
5. **環境変数設定**:
   - `DATABASE_URL`: PostgreSQLの接続URL（自動設定）
   - `SECRET_KEY`: ランダムな秘密鍵

## 🛠️ 開発

### デバッグモード
```bash
export FLASK_ENV=development  # Windows: set FLASK_ENV=development
python app.py
```

### ログ確認
```bash
tail -f app.log  # アプリケーションログ
```

### テスト用問題追加
```bash
# json_questions/ フォルダに新しいJSONファイルを追加
# アプリケーション再起動で自動読み込み
```

## 🔧 トラブルシューティング

### 問題が表示されない
1. **診断実行**: `python db_diagnostic.py`
2. **JSONファイル確認**: `json_questions/` フォルダの存在確認
3. **強制読み込み**: 診断スクリプトで `y` を選択

### ジャンル別演習で1問しか進まない
1. **ブラウザ更新**: F5キーまたはCtrl+R
2. **キャッシュクリア**: ブラウザのキャッシュを削除
3. **JavaScript確認**: ブラウザのコンソールでエラー確認

### データベースエラー
1. **ファイル削除**: `fe_exam.db` を削除
2. **再起動**: アプリケーションを再起動（自動再作成）
3. **診断実行**: `python db_diagnostic.py`

## 📊 機能詳細

### ダッシュボード
- 📈 学習統計の表示
- 🎯 ジャンル別成績
- 📚 最近の学習履歴
- 🚀 クイックアクション

### ジャンル別演習
- 🔍 分野別問題選択
- ⚡ リアルタイム判定
- 📝 詳細な解説表示
- 📊 進捗追跡

### 模擬試験
- ⏰ 60分タイマー
- 📝 本番形式の問題
- 🎯 合格判定（60%以上）
- 📊 詳細な結果分析

### 学習履歴
- 📈 時系列での成績推移
- 🎯 ジャンル別正答率
- 📊 詳細な統計情報
- 🔍 弱点分析

## 🎨 UI/UX特徴

### デザインシステム
- **グラスモーフィズム**: 半透明ガラス効果
- **グラデーション**: 美しい色彩の組み合わせ
- **アニメーション**: スムーズな画面遷移
- **レスポンシブ**: 全デバイス対応

### カラーパレット
- **プライマリ**: Blue → Purple グラデーション
- **セカンダリ**: Orange → Red グラデーション
- **アクセント**: Green、Purple、Pink
- **背景**: Slate-900 → Slate-800 グラデーション

## 📄 ライセンス

MIT License

## 👨‍💻 作者

[@d01ki](https://github.com/d01ki)

## 🤝 貢献

Issue、Pull Requestお待ちしています！

## 📞 サポート

問題が発生した場合は、以下を実行してIssueに情報を添付してください：

```bash
python db_diagnostic.py > diagnostic_report.txt
```

---

**基本情報技術者試験の合格を応援します！頑張ってください！** 🎯📚