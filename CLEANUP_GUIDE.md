# 🗑️ 削除推奨ファイル

以下のファイルはmainブランチにマージする前に削除することを推奨します：

## 開発用ドキュメント（不要）
- `FINAL_FIX_SUMMARY.md` - 開発メモ
- `FIXES_SUMMARY.md` - 開発メモ

## 未使用フォルダ（確認して削除）
- `backend/` - 未使用の場合は削除
- `utils/` - utils.pyと重複している場合は削除

## 削除方法

```bash
# ローカルで削除
git rm FINAL_FIX_SUMMARY.md
git rm FIXES_SUMMARY.md
git rm -r backend/  # 未使用の場合のみ
git rm -r utils/    # utils.pyと重複の場合のみ

# コミット
git commit -m "Remove unnecessary files"

# プッシュ
git push origin feature/image-support
```

## 注意事項

削除する前に、各ファイル/フォルダが本当に不要かどうか確認してください。
