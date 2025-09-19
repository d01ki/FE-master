# 画像ファイル格納ディレクトリ

このディレクトリには、問題に関連する図表や画像ファイルを格納します。

## ファイル命名規則

画像ファイルは以下の命名規則に従って配置してください：

```
{年度}_{期}_{問題番号}.png
```

### 例：
- `2025_s_q3.png` - 2025年春期の問3の画像
- `2024_a_q15.png` - 2024年秋期の問15の画像

### 年度と期の表記：
- 春期：`_s` (spring)
- 秋期：`_a` (autumn)

## 使用方法

JSONファイルで画像URLを指定する場合：

```json
{
  "question_id": "問3",
  "question_text": "次の図を参照して答えよ。",
  "choices": {
    "ア": "選択肢1",
    "イ": "選択肢2",
    "ウ": "選択肢3",
    "エ": "選択肢4"
  },
  "correct_answer": "イ",
  "explanation": "解説文...",
  "genre": "基礎理論",
  "image_url": "/static/images/2025_s_q3.png"
}
```

画像が不要な問題では、`image_url`フィールドを省略するか、`null`を設定してください：

```json
{
  "question_id": "問1",
  "question_text": "問題文...",
  "choices": {...},
  "correct_answer": "エ",
  "explanation": "解説文...",
  "genre": "アルゴリズムとプログラミング",
  "image_url": null
}
```
