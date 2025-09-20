# 📸 選択肢画像表示機能 実装ガイド

## 🎯 機能概要

### **新機能**
- **選択肢画像表示**: 選択肢に画像を表示できる機能を追加
- **2×2グリッドレイアウト**: 画像選択肢は美しい2×2グリッドで表示
- **ハイブリッド表示**: テキストと画像の混在も対応
- **レスポンシブデザイン**: モバイル・デスクトップ両対応

---

## 📋 JSONデータ形式

### **新しいフィールド構造**

```json
{
  "question_id": "2024_s_q1",  // 統一形式: 旧 "2024_s_問1" → 新 "2024_s_q1"
  "question_text": "問題文",
  "choices": {
    "ア": "選択肢テキスト1",
    "イ": "選択肢テキスト2",
    "ウ": "選択肢テキスト3",
    "エ": "選択肢テキスト4"
  },
  "correct_answer": "ウ",
  "explanation": "解説文",
  "genre": "ジャンル名",
  "image_url": "/static/images/questions/2024_s_q1.png",  // 問題画像
  "choice_images": {  // 🆕 新フィールド: 選択肢画像
    "ア": "/static/images/answers/2024_s_a1_1.png",
    "イ": "/static/images/answers/2024_s_a1_2.png",
    "ウ": "/static/images/answers/2024_s_a1_3.png",
    "エ": "/static/images/answers/2024_s_a1_4.png"
  }
}
```

### **画像なしの場合**

```json
{
  "question_id": "2024_s_q2",
  "question_text": "問題文",
  "choices": {
    "ア": "選択肢テキスト1",
    "イ": "選択肢テキスト2",
    "ウ": "選択肢テキスト3",
    "エ": "選択肢テキスト4"
  },
  "correct_answer": "イ",
  "explanation": "解説文",
  "genre": "ジャンル名",
  "image_url": "null",  // または省略
  "choice_images": null  // または省略
}
```

---

## 🗂️ 画像ファイルの配置ルール

### **ディレクトリ構造**

```
static/
├── images/
│   ├── questions/           # 問題の画像
│   │   ├── 2024_s_q1.png
│   │   ├── 2024_s_q2.png
│   │   └── ...
│   └── answers/             # 選択肢の画像
│       ├── 2024_s_a1_1.png  # 問1 - ア
│       ├── 2024_s_a1_2.png  # 問1 - イ
│       ├── 2024_s_a1_3.png  # 問1 - ウ
│       ├── 2024_s_a1_4.png  # 問1 - エ
│       ├── 2024_s_a2_1.png  # 問2 - ア
│       └── ...
```

### **命名規則**

#### **問題画像**
- フォーマット: `{year}_{season}_q{number}.png`
- 例:
  - `2024_s_q1.png` (2024年春期 問1)
  - `2024_a_q15.png` (2024年秋期 問15)

#### **選択肢画像**
- フォーマット: `{year}_{season}_a{number}_{choice_number}.png`
- 選択肢番号:
  - `1` = ア
  - `2` = イ
  - `3` = ウ
  - `4` = エ
- 例:
  - `2024_s_a1_1.png` (2024年春期 問1 選択肢ア)
  - `2024_s_a1_2.png` (2024年春期 問1 選択肢イ)

---

## 🔧 データベーススキーマの変更

### **新しいカラム: `choice_images`**

#### **PostgreSQL**
```sql
ALTER TABLE questions ADD COLUMN choice_images JSON;
```

#### **SQLite**
```sql
ALTER TABLE questions ADD COLUMN choice_images TEXT;
```

### **データ型**
- PostgreSQL: `JSON`
- SQLite: `TEXT` (JSON文字列として保存)

---

## 🎨 UIの動作

### **表示パターン**

#### **パターン1: 選択肢に画像がある場合**
```
┌─────────────┬─────────────┐
│   ア: 画像  │   イ: 画像  │
│             │             │
└─────────────┴─────────────┘
┌─────────────┬─────────────┐
│   ウ: 画像  │   エ: 画像  │
│             │             │
└─────────────┴─────────────┘
```
- 2×2グリッドレイアウト
- 各カードに画像を表示
- ラベル（ア、イ、ウ、エ）は左上に配置

#### **パターン2: 選択肢がテキストのみの場合**
```
┌─────────────────────────────┐
│ ア. 選択肢テキスト1          │
└─────────────────────────────┘
┌─────────────────────────────┐
│ イ. 選択肢テキスト2          │
└─────────────────────────────┘
```
- 従来の縦並びリスト表示

---

## 🚀 実装済みの変更

### **1. データベース (database.py)**
✅ `choice_images`カラムを追加（PostgreSQL/SQLite対応）
✅ 選択肢画像データの保存・取得機能
✅ 画像URLのバリデーション

### **2. QuestionManager (question_manager.py)**
✅ 選択肢画像データの処理
✅ JSONパース機能の追加
✅ 既存機能との互換性維持

### **3. UIテンプレート (templates/question.html)**
✅ 2×2グリッドレイアウトの実装
✅ 条件分岐表示（画像/テキスト）
✅ レスポンシブデザイン
✅ 既存デザインとの統一

---

## 📦 使用例

### **JSONデータの準備**

```json
[
  {
    "question_id": "2024_s_q1",
    "question_text": "次の真理値表を完成させる論理演算はどれか。",
    "choices": {
      "ア": "XOR",
      "イ": "AND",
      "ウ": "OR",
      "エ": "NAND"
    },
    "correct_answer": "ウ",
    "explanation": "真理値表から判断すると...",
    "genre": "基礎論理",
    "image_url": "/static/images/questions/2024_s_q1.png",
    "choice_images": {
      "ア": "/static/images/answers/2024_s_a1_1.png",
      "イ": "/static/images/answers/2024_s_a1_2.png",
      "ウ": "/static/images/answers/2024_s_a1_3.png",
      "エ": "/static/images/answers/2024_s_a1_4.png"
    }
  }
]
```

### **画像ファイルの配置**

```bash
# 問題画像
static/images/questions/2024_s_q1.png

# 選択肢画像
static/images/answers/2024_s_a1_1.png  # ア
static/images/answers/2024_s_a1_2.png  # イ
static/images/answers/2024_s_a1_3.png  # ウ
static/images/answers/2024_s_a1_4.png  # エ
```

---

## ✅ 動作確認チェックリスト

### **準備**
- [ ] `static/images/questions/` ディレクトリを作成
- [ ] `static/images/answers/` ディレクトリを作成
- [ ] 画像ファイルを配置
- [ ] JSONデータを更新

### **機能テスト**
- [ ] 選択肢画像が2×2グリッドで表示される
- [ ] テキスト選択肢は縦並びで表示される
- [ ] モバイルで1列表示になる
- [ ] 画像クリックで選択できる
- [ ] 正解/不正解が正しく表示される

### **エラーハンドリング**
- [ ] 画像読み込みエラー時の処理
- [ ] 画像がない選択肢はテキスト表示
- [ ] nullデータの適切な処理

---

## 🔄 既存データの移行手順

### **Step 1: question_idの変換**

既存のJSONファイルで一括置換:
```bash
# 例: sedコマンドで一括変換
sed -i 's/"2024_s_問/"2024_s_q/g' questions.json
sed -i 's/"2024_a_問/"2024_a_q/g' questions.json
```

### **Step 2: choice_imagesの追加**

画像がある問題にのみ`choice_images`フィールドを追加:
```json
"choice_images": {
  "ア": "/static/images/answers/2024_s_a1_1.png",
  "イ": "/static/images/answers/2024_s_a1_2.png",
  "ウ": "/static/images/answers/2024_s_a1_3.png",
  "エ": "/static/images/answers/2024_s_a1_4.png"
}
```

### **Step 3: データベースの更新**

アプリを再起動すると自動的にスキーマが更新されます:
```bash
python app.py
```

---

## 🎯 注意事項

### **重要なポイント**

1. **画像ファイル名は厳密に従う**
   - `2024_s_a1_1.png` (OK)
   - `2024_s_a01_1.png` (NG - ゼロパディング不要)

2. **choice_imagesは選択肢がある場合のみ**
   - テキスト選択肢の場合は省略またはnull

3. **既存のUIデザインを維持**
   - グラデーション、アニメーション等はそのまま

4. **レスポンシブ対応**
   - モバイルでは1列表示に自動切替

---

## 📊 ファイル変更サマリー

| ファイル | 変更内容 | 重要度 |
|---------|---------|-------|
| `database.py` | choice_imagesフィールド追加 | 🔴 必須 |
| `question_manager.py` | データ処理ロジック更新 | 🔴 必須 |
| `templates/question.html` | UI更新（グリッド表示） | 🔴 必須 |
| JSONファイル | question_id形式変更 | 🟡 推奨 |
| 画像ファイル | 配置とリネーム | 🟡 推奨 |

---

## 🆘 トラブルシューティング

### **Q: 画像が表示されない**
A: 以下を確認してください:
1. 画像ファイルのパスが正しいか
2. ファイル名のスペルミスがないか
3. ブラウザのコンソールでエラーを確認

### **Q: レイアウトが崩れる**
A: 
1. キャッシュをクリア (Ctrl+Shift+R)
2. CSSが正しく読み込まれているか確認
3. ブラウザの互換性を確認

### **Q: データベースエラーが出る**
A:
1. choice_imagesカラムが追加されているか確認
2. アプリを再起動してスキーマを更新

---

## 🎉 完成！

これで選択肢画像表示機能の実装が完了しました。

### **実装された機能**
✅ 選択肢画像の2×2グリッド表示
✅ テキスト選択肢との共存
✅ レスポンシブデザイン
✅ 既存UIデザインの維持
✅ 画像URLのバリデーション

### **次のアクション**
1. JSONデータと画像ファイルを準備
2. `static/images/`に画像を配置
3. アプリを起動して動作確認
4. 問題なければmainブランチにマージ

---

質問や問題があれば、お気軽にお知らせください！
