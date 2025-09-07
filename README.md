# 基本情報技術者試験 学習アプリ (FE Master)

Flask + SQLite + Tailwind CSS を使用した現代的な学習プラットフォーム

## 🚀 主な機能

### ✅ 完全実装済み

- **📚 問題管理システム**
  - JSONファイルからの問題データ一括アップロード
  - 年度別過去問の管理（例：2025r07_kamoku_a_spring.json）
  - 重複チェック機能付きの問題登録

- **🎯 ジャンル別演習**
  - 8つの主要ジャンルに対応
  - ジャンル別正答率の可視化
  - 苦手分野の特定と集中学習

- **📝 模擬試験機能**
  - 年度別過去問からの模擬試験生成
  - リアルタイム採点システム
  - 詳細な解答解説表示

- **📊 学習分析・統計**
  - 個人学習進捗の追跡
  - ジャンル別パフォーマンス分析
  - 学習履歴の詳細記録

- **🎨 モダンUI/UX**
  - ダークテーマデザイン
  - レスポンシブレイアウト
  - アニメーション効果とインタラクティブな要素

- **🔒 管理機能**
  - セキュアな管理者認証
  - データベース管理ツール
  - ファイルアップロード管理

## 📁 プロジェクト構成

```
FE-master/
├── app.py                 # メインアプリケーション
├── run.py                 # アプリケーション起動スクリプト
├── requirements.txt       # Python依存関係
├── fe_exam.db            # SQLiteデータベース（自動作成）
├── uploads/              # アップロードファイル保存先
├── json_questions/       # JSON問題ファイル保存先
├── templates/            # HTMLテンプレート
│   ├── base.html         # ベーステンプレート（ダークテーマ）
│   ├── dashboard.html    # ダッシュボード
│   ├── genre_practice.html # ジャンル別演習
│   ├── practice.html     # 練習問題画面
│   ├── mock_exam_select.html # 模擬試験選択
│   ├── mock_exam_practice.html # 模擬試験実施
│   ├── history.html      # 学習履歴
│   ├── admin.html        # 管理画面
│   ├── admin_login.html  # 管理者ログイン
│   ├── question.html     # 個別問題表示
│   └── error.html        # エラーページ
├── utils/                # ユーティリティ
│   ├── database.py       # データベース管理
│   ├── question_manager.py # 問題管理クラス
│   └── pdf_processor.py  # PDF処理（サンプル生成）
└── static/               # 静的ファイル（CSS/JS/画像）
```

## 🛠️ セットアップ手順

### 1. 必要な環境
- Python 3.8以上
- pip（Python パッケージインストーラー）

### 2. インストール

```bash
# リポジトリをクローン
git clone https://github.com/d01ki/FE-master.git
cd FE-master

# 依存関係をインストール
pip install -r requirements.txt

# アプリケーションを起動
python run.py
```

### 3. アクセス
- アプリケーション: http://localhost:5000
- 管理画面: http://localhost:5000/admin/login
  - デフォルトパスワード: `fe2025admin`

## 📋 使用方法

### 1. 問題データの準備

推奨JSONファイル形式：
```json
[
  {
    "question_id": "問１",
    "question_text": "問題文...",
    "choices": {
      "ア": "選択肢1",
      "イ": "選択肢2", 
      "ウ": "選択肢3",
      "エ": "選択肢4"
    },
    "correct_answer": "エ",
    "explanation": "解説文...",
    "genre": "基礎理論"
  }
]
```

### 2. 学習の流れ

1. **管理画面で問題をアップロード**
   - JSON形式の過去問ファイルをアップロード
   - 年度別ファイル名推奨：`2025r07_kamoku_a_spring.json`

2. **ジャンル別演習で苦手分野を特定**
   - 8つのジャンルから選択
   - 正答率を確認して弱点を把握

3. **模擬試験で実力測定**
   - 年度別過去問から選択
   - 本番形式での練習

4. **学習履歴で進捗確認**
   - 日別統計の確認
   - 詳細な解答履歴の閲覧

## 🎯 対応ジャンル

1. **基礎理論** - 数学、論理演算、情報理論
2. **アルゴリズムとプログラミング** - データ構造、アルゴリズム、プログラム設計
3. **コンピュータシステム** - ハードウェア、アーキテクチャ、システム構成
4. **技術要素** - ヒューマンインターフェース、マルチメディア
5. **ネットワーク** - ネットワーク方式、通信プロトコル、インターネット
6. **データベース** - データモデル、正規化、SQL、トランザクション
7. **セキュリティ** - 情報セキュリティ、暗号化、認証
8. **システム開発** - 開発プロセス、設計手法、テスト
9. **マネジメント** - プロジェクト管理、サービスマネジメント

## 🔧 技術仕様

### バックエンド
- **Flask**: Webフレームワーク
- **SQLite**: データベース
- **Python 3.8+**: プログラミング言語

### フロントエンド
- **Tailwind CSS**: CSSフレームワーク
- **Font Awesome**: アイコンライブラリ
- **Vanilla JavaScript**: インタラクティブ機能

### データベース設計

```sql
-- 問題テーブル
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT UNIQUE,
    question_text TEXT NOT NULL,
    choices TEXT NOT NULL,  -- JSON形式
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    genre TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 解答履歴テーブル
CREATE TABLE user_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER,
    user_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions (id)
);
```

## 🎨 UI/UX特徴

### ダークテーマデザイン
- モダンで目に優しいダークカラーパレット
- グラデーション効果とアニメーション
- レスポンシブデザイン対応

### インタラクティブ要素
- ホバーエフェクト
- スムーズなトランジション
- プログレスバーアニメーション
- リアルタイムフィードバック

### ユーザビリティ
- 直感的なナビゲーション
- 明確な視覚的フィードバック
- アクセシビリティ配慮

## 🔒 セキュリティ

- 管理者認証システム
- SQLインジェクション対策
- XSS（クロスサイトスクリプティング）対策
- ファイルアップロード制限

## 📊 パフォーマンス

- データベースクエリ最適化
- 効率的なファイル管理
- クライアントサイドキャッシュ活用

## 🚀 今後の拡張予定

- [ ] ユーザー認証システム
- [ ] マルチユーザー対応
- [ ] 学習計画機能
- [ ] AI駆動の学習推奨システム
- [ ] モバイルアプリ対応
- [ ] REST API提供

## 📝 更新履歴

### v2.0.0 (2025-09-06)
- ✨ **JSONアップロード機能を完全修正**
  - エラーハンドリングの改善
  - 文字エンコーディング対応強化
  - 重複チェック機能の実装

- 🎯 **ジャンル別演習機能を新規追加**
  - 8つの主要ジャンルに対応
  - ジャンル別正答率の可視化
  - 苦手分野の特定機能

- 📝 **模擬試験機能の年度選択対応**
  - 年度別JSONファイルからの試験生成
  - ファイル名パターン解析機能
  - "2025年春期"形式での表示

- 🎨 **UIの大幅改善**
  - ダークテーマの採用
  - モダンなデザインシステム
  - アニメーション効果の追加
  - レスポンシブデザインの改善

- 🔧 **アーキテクチャの改善**
  - QuestionManagerクラスの機能拡張
  - データベース操作の最適化
  - エラーハンドリングの強化

### v1.0.0 (初期リリース)
- 基本的な問題管理機能
- 簡易的な学習機能
- 基本的な管理画面

## 🤝 コントリビューション

プロジェクトへの貢献を歓迎します！

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 📞 サポート

質問や問題がある場合は、以下の方法でお気軽にお問い合わせください：

- GitHub Issues: [Issues](https://github.com/d01ki/FE-master/issues)
- Email: [your-email@example.com]

## 🙏 謝辞

- 基本情報技術者試験の過去問を提供するIPA（情報処理推進機構）
- Tailwind CSS、Flask、その他のオープンソースライブラリの開発者の皆様

---

**⭐ このプロジェクトが役に立ったら、ぜひスターをお願いします！**