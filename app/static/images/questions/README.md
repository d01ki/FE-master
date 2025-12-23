# 問題画像フォルダ（移動済み）

⚠️ **重要**: このフォルダは現在使用されていません。

## 新しい画像保存場所

画像ファイルは認証が必要な保護されたディレクトリに移動されました：

- **問題画像**: `/protected_images/questions/`
- **解答画像**: `/protected_images/answers/`

### セキュリティについて

画像は `static` フォルダの外に配置されているため、ブラウザから直接アクセスすることはできません。
認証されたユーザーのみが専用のルート経由で画像を閲覧できます。

### 画像ファイルの配置方法

1. **管理画面からアップロード（推奨）**:
   - 管理者でログイン → 「管理」→「問題アップロード」
   - 「画像アップロード」セクションで画像を選択してアップロード

2. **直接配置**:
   ```bash
   # 問題画像
   cp /path/to/image.png /home/iniad/FE-master/protected_images/questions/
   
   # 解答画像
   cp /path/to/answer.png /home/iniad/FE-master/protected_images/answers/
   ```

### アクセス方法

- 認証が必要: ログインしていないユーザーは画像にアクセスできません
- 専用ルート: `/images/questions/<filename>` と `/images/answers/<filename>`
- 直接URL: ブラウザから直接アクセスしても403 Forbiddenまたは404 Not Foundが返されます

## 対応画像形式

- PNG (`.png`)
- JPEG (`.jpg`, `.jpeg`)
- GIF (`.gif`)
- SVG (`.svg`)

## データベース設定

問題データに以下のように画像URLを登録：
```json
{
  "question_id": "FE_2025_Q01",
  "image_url": "/static/images/questions/2025_s_q14.png",
  ...
}
```

システムが自動的にファイル名を抽出し、保護されたルート経由で配信します。
