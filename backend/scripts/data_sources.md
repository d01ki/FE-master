# 基本情報技術者試験 問題データ取得方法

基本情報技術者試験の過去問データを取得する方法をまとめます。

## 1. 公式ソース

### IPA（情報処理推進機構）公式
- **URL**: https://www.ipa.go.jp/shiken/kubun/fe.html
- **提供内容**: 過去問題、解答例
- **形式**: PDF
- **利用条件**: 公式利用規約に従う
- **特徴**: 最も信頼性が高い、公式解答あり

### 実装方針
```python
# PDFから問題を抽出する場合
import PyPDF2
import re

def extract_from_ipa_pdf(pdf_path):
    # PDFを解析して問題データを抽出
    pass
```

## 2. 過去問サイト

### 注意事項
⚠️ **重要**: 以下のサイトを利用する前に必ず確認してください：
- 利用規約
- robots.txt
- 著作権情報
- サーバー負荷への配慮

### 主要な過去問サイト例
1. **過去問道場**
   - 多くの問題が掲載
   - 解説付き
   - ユーザー投稿型

2. **ITパスポート試験ドットコム**
   - 基本情報も一部カバー
   - 解説充実

### スクレイピング実装例
`backend/scripts/scraper_fe_kakomon.py` に実装済み

## 3. 手動データ作成

### 現在の実装
`backend/scripts/sample_data.py`
- 手動で作成したサンプル問題5問
- 開発・テスト用途
- すぐに動作確認可能

### 利点
- 著作権の問題なし
- カスタマイズ可能
- 品質管理しやすい

## 4. 推奨データ取得フロー

### Phase 1: MVP開発
```bash
# 手動サンプルデータで開発
cd backend
python scripts/sample_data.py
```

### Phase 2: 少量データ取得
```bash
# 公式PDFから手動で数十問抽出
python scripts/extract_from_pdf.py official_problems.pdf
```

### Phase 3: 大量データ取得
```bash
# 利用規約確認後、適切なスクレイピング
python scripts/scraper_fe_kakomon.py
```

## 5. データ品質管理

### バリデーション
- 問題文の完整性
- 選択肢の正確性
- 正解の妥当性
- カテゴリ分類の適切性

### 実装例
```python
def validate_problem_data(problem):
    required_fields = ['text_md', 'choices_json', 'answer_index']
    for field in required_fields:
        if not problem.get(field):
            return False
    return True
```

## 6. 法的・倫理的考慮事項

### 著作権
- 問題文は著作物の可能性
- 公式問題の無断複製は避ける
- フェアユース（引用）の範囲で利用

### 利用規約遵守
- robots.txtの確認
- アクセス頻度の制限
- User-Agentの適切な設定

### 推奨アプローチ
1. 公式ソースを優先
2. 許可されている範囲での利用
3. オリジナル問題の作成も検討
4. 教育目的であることを明示

## 7. 技術実装

### 必要なライブラリ
```bash
pip install requests beautifulsoup4 PyPDF2 html2text
```

### データベース保存
```python
from app.models.problem import Problem
from app.services.similarity import update_problem_embedding

def save_problem(problem_data, db):
    problem = Problem(**problem_data)
    db.add(problem)
    db.commit()
    update_problem_embedding(db, problem)
```

## 8. 次のステップ

1. **現在**: 手動サンプルデータで動作確認
2. **短期**: 公式PDFから少量データ抽出
3. **中期**: 適切な過去問サイトとの連携
4. **長期**: オリジナル問題作成システム

---

**注意**: このドキュメントは教育目的の参考情報です。実際の運用では必ず法的要件と利用規約を確認してください。
