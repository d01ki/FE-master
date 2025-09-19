# 基本情報技術者試験 学習アプリ - FE Master

## 🎯 概要
基本情報技術者試験の学習を効率化するWebアプリケーション

## ✨ 最新の変更 (feature/image-support)

### 🔧 機能改善

#### 1. **アプリケーション構造の改善**
- **app.pyのモジュール化**: 長大だったapp.pyを機能ごとに分割
  - `routes/main_routes.py` - メインページ (ホーム、ダッシュボード)
  - `routes/practice_routes.py` - 練習問題関連
  - `routes/exam_routes.py` - 模擬試験関連
  - `routes/admin_routes.py` - 管理者機能
  - app.pyはシンプルなエントリーポイントとして維持

#### 2. **ジャンル別演習の修正** ✅
- **問題**: ジャンル別演習で全問題が表示される不具合
- **解決**: `question_manager.get_questions_by_genre(genre)`を正しく実装
- **結果**: 指定されたジャンルの問題のみが表示されるように修正

#### 3. **画像表示機能の追加** 🖼️
- **模擬試験**: 既に実装済み ✅
- **ランダム問題**: 既に実装済み ✅  
- **ジャンル別演習**: 画像表示コードを追加 ✅

### 📁 ファイル構成

```
FE-master/
├── app.py                      # メインアプリケーション（簡素化）
├── routes/                     # ルーティングモジュール
│   ├── __init__.py
│   ├── main_routes.py         # メインページ
│   ├── practice_routes.py     # 練習問題
│   ├── exam_routes.py         # 模擬試験
│   └── admin_routes.py        # 管理機能
├── database.py                # データベース管理
├── question_manager.py        # 問題管理
├── auth.py                    # 認証機能
├── helper_functions.py        # ヘルパー関数
├── templates/                 # HTMLテンプレート
│   ├── practice.html         # ジャンル別演習（画像対応）
│   ├── question.html         # ランダム問題（画像対応）
│   └── mock_exam_practice.html # 模擬試験（画像対応）
└── static/
    └── images/               # 画像ファイル格納
```

### 🔍 技術仕様

#### JSONデータフォーマット
```json
{
  "question_id": "問5",
  "question_text": "問題文...",
  "choices": {
    "ア": "選択肢1",
    "イ": "選択肢2",
    "ウ": "選択肢3",
    "エ": "選択肢4"
  },
  "correct_answer": "ア",
  "explanation": "解説文...",
  "genre": "ソフトウェア",
  "image_url": "/static/images/2025_s_q6.png"
}
```

#### 画像表示の実装
- `image_url`が存在し、"null"や"None"でない場合に画像を表示
- エラー時のフォールバック処理を実装
- レスポンシブデザイン対応

### 🚀 デプロイ方法

```bash
# 1. 依存関係のインストール
pip install -r requirements.txt

# 2. アプリケーション起動
python app.py
```

### 📝 開発者向け情報

#### 新しいルートの追加方法
1. `routes/`ディレクトリに新しいBlueprint作成
2. `routes/__init__.py`でインポート
3. `app.py`でBlueprint登録

例:
```python
# routes/new_routes.py
from flask import Blueprint
new_bp = Blueprint('new', __name__)

@new_bp.route('/new')
def new_page():
    return render_template('new.html')
```

#### 画像付き問題の追加
1. 画像を`static/images/`に配置
2. JSONの`image_url`に相対パスを指定
3. 管理画面からJSONをアップロード

### 🐛 バグ修正

- ✅ ジャンル別演習でジャンルフィルタリングが機能しない問題を修正
- ✅ 画像がランダム問題とジャンル別演習で表示されない問題を修正
- ✅ app.pyが長すぎる問題を解決（モジュール化）

### 📊 テスト

以下の動作確認を行ってください：

1. **ジャンル別演習**
   - ジャンルを選択して問題が正しく絞り込まれるか
   - 画像付き問題で画像が表示されるか

2. **ランダム問題**
   - 画像付き問題で画像が表示されるか

3. **模擬試験**
   - 画像付き問題で画像が表示されるか

### 🔄 マイグレーション注意事項

既存のデプロイ環境では、以下の手順で更新してください：

1. **バックアップ**
   ```bash
   # データベースのバックアップ
   cp fe_exam.db fe_exam.db.backup
   ```

2. **コード更新**
   ```bash
   git pull origin feature/image-support
   ```

3. **依存関係更新**
   ```bash
   pip install -r requirements.txt --upgrade
   ```

4. **アプリケーション再起動**
   ```bash
   # Renderの場合は自動デプロイ
   # 手動の場合
   python app.py
   ```

### 🎨 今後の改善案

- [ ] 画像のアップロード機能を管理画面に追加
- [ ] 画像のリサイズ・最適化機能
- [ ] 問題検索機能の強化
- [ ] 学習履歴の可視化改善

---

## 📦 環境構築

### 必要な環境変数
```bash
# 本番環境
DATABASE_URL=postgresql://...
SECRET_KEY=your-secret-key
ADMIN_PASSWORD=your-admin-password

# 開発環境（SQLite使用）
SECRET_KEY=dev-secret-key
ADMIN_PASSWORD=admin123
```

### ローカル開発
```bash
# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# アプリケーション起動
python app.py
```

### 本番環境 (Render.com)
1. GitHubリポジトリ連携
2. 環境変数設定
3. 自動デプロイ

---

## 📄 ライセンス
MIT License

## 👨‍💻 開発者
FE Master Team