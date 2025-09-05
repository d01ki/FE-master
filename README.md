# FE-Master - 基本情報技術者試験 過去問学習アプリ

基本情報技術者試験の過去問を効率的に学習できるWebアプリケーションです。

## 🚀 クイックスタート

### 1. 必要なライブラリをインストール
```bash
pip install -r requirements.txt
```

### 2. アプリケーションを起動
```bash
python3 app.py
```

### 3. ブラウザでアクセス
- **メインページ**: http://localhost:8000
- **API ドキュメント**: http://localhost:8000/docs
- **問題一覧 API**: http://localhost:8000/api/problems

## 📱 主要機能

### 🎓 学習機能
- **分野別問題学習**: システム構成要素、データベース、ネットワーク、アルゴリズム、セキュリティ
- **解答・解説表示**: 各問題に詳細な解説付き
- **学習履歴記録**: 解答履歴と正答率を自動記録

### 📊 統計・分析
- **学習進捗の可視化**: 総問題数、正答率、分野別成績
- **弱点分野の特定**: カテゴリ別の成績分析
- **学習効果の測定**: 時間経過による成績向上を追跡

## 🔧 技術スタック

- **バックエンド**: FastAPI (Python)
- **データベース**: SQLite (簡単セットアップ)
- **API ドキュメント**: Swagger UI / ReDoc
- **デプロイ**: スタンドアロン実行可能

## 📚 サンプル問題

アプリケーションには以下のサンプル問題が含まれています：

1. **システム性能** - スループットに関する問題
2. **データベース** - 正規化に関する問題
3. **ネットワーク** - TCP/IPモデルに関する問題
4. **アルゴリズム** - ソートアルゴリズムの計算量
5. **セキュリティ** - ファイアウォールの機能

## 💻 API 使用例

### 問題一覧を取得
```bash
curl http://localhost:8000/api/problems
```

### 特定の問題を取得
```bash
curl http://localhost:8000/api/problems/1
```

### カテゴリ別問題を取得
```bash
curl "http://localhost:8000/api/problems?category=データベース"
```

### 解答を送信
```bash
curl -X POST "http://localhost:8000/api/problems/1/answer" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "selected_index=0"
```

### 統計情報を取得
```bash
curl http://localhost:8000/api/stats
```

## 📁 ファイル構成

```
FE-master/
├── app.py                 # メインアプリケーション
├── requirements.txt       # 依存ライブラリ
├── README.md             # このファイル
├── fe_master.db          # SQLiteデータベース (自動生成)
└── backend/              # 詳細なバックエンド実装
    ├── app/
    ├── scripts/
    └── alembic/
```

## 🛠️ トラブルシューティング

### ライブラリインストールエラー
```bash
# pipを更新
pip install --upgrade pip

# 個別インストール
pip install fastapi uvicorn pydantic
```

### ポートが使用中の場合
アプリケーションはデフォルトでポート8000を使用します。変更する場合は`app.py`内の`PORT`変数を編集してください。

### データベースリセット
```bash
# データベースファイルを削除して再作成
rm fe_master.db
python3 app.py
```

## 📝 ライセンス

MIT License - 教育目的での使用を推奨します。

## ⚠️ 注意事項

- このアプリケーションは教育・学習目的で作成されています
- サンプル問題はオリジナルで作成されています
- 実際の過去問を使用する場合は著作権と利用規約を確認してください

## 🌐 開発者向け情報

より詳細な開発情報や拡張機能については`backend/`ディレクトリ内のドキュメントを参照してください。

---

📚 **Happy Learning!** 基本情報技術者試験の合格を目指して頑張ってください！
