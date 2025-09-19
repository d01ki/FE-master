<div align="center">

# 🎓 FE Master

### 基本情報技術者試験 学習アプリケーション

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**効率的な学習で基本情報技術者試験の合格を目指す**

[Demo](https://fe-master.onrender.com) ・ [GitHub](https://github.com/d01ki/FE-master) ・ [Wiki](https://github.com/d01ki/FE-master/wiki)

</div>

---

## ✨ 特徴

<table>
<tr>
<td width="33%" align="center">

### 🎯 ランダム問題
毎日異なる問題で<br>飽きずに学習

</td>
<td width="33%" align="center">

### 📊 ジャンル別演習
苦手分野を<br>集中的に克服

</td>
<td width="33%" align="center">

### 📝 模擬試験
本番形式で<br>実力を確認

</td>
</tr>
</table>

### 🚀 主な機能

- **📱 レスポンシブデザイン** - PC・スマホどちらでも快適に学習
- **📊 学習履歴管理** - あなたの進捗を詳細に追跡
- **🖼️ 画像対応** - 図表付き問題も完全サポート
- **🔒 ユーザー認証** - 個人の学習データを安全に保管
- **🛠️ 管理機能** - 簡単な問題管理インターフェース

---

## 🛠️ 技術スタック

<div align="center">

| カテゴリ | 技術 |
|:---:|:---|
| **Backend** | Python, Flask |
| **Database** | PostgreSQL, SQLite |
| **Frontend** | HTML5, Tailwind CSS, JavaScript |
| **Deployment** | Render.com |
| **Auth** | Flask-Session, Werkzeug |

</div>

---

## 🚀 クイックスタート

### 💻 ローカル環境

```bash
# リポジトリをクローン
git clone https://github.com/d01ki/FE-master.git
cd FE-master

# 仮想環境を作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt

# アプリケーションを起動
python app.py
```

🎉 http://localhost:5002 でアクセスできます！

### 🔑 デフォルト管理者アカウント

- **ユーザー名**: `admin`
- **パスワード**: `admin123`

⚠️ **本番環境では必ずパスワードを変更してください**

---

## 📸 スクリーンショット

<div align="center">

### 🏠 ダッシュボード

*学習進捗を一目で確認*

### 📝 問題画面

*直感的なインターフェースで学習*

### 📈 学習履歴

*詳細な統計と解説で復習も完璧*

</div>

---

## 🛡️ セキュリティ

- **パスワードハッシュ化** - Werkzeugを使用した安全なパスワード管理
- **セッション管理** - Flask-Sessionによる安全なセッション
- **データ保護** - PostgreSQLでのデータ暗号化対応

---

## 🌐 デプロイ

### Render.com へのデプロイ

1. **環境変数を設定**
   ```
   DATABASE_TYPE=postgresql
   DATABASE_URL=<PostgreSQL接続URL>
   SECRET_KEY=<ランダムな文字列>
   ```

2. **自動デプロイが開始されます**

詳しい手順は[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)をご覧ください。

---

## 📚 ドキュメント

- **[Wiki](https://github.com/d01ki/FE-master/wiki)** - 詳細な開発情報
- **[Issues](https://github.com/d01ki/FE-master/issues)** - バグ報告・機能リクエスト
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - デプロイガイド

---

## 🤝 貢献

プルリクエストを歓迎します！

1. フォークする
2. ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. プッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

---

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)をご覧ください。

---

<div align="center">

**Made with ❤️ by FE Master Team**

⭐ このプロジェクトが役に立ったら、スターをお願いします！

</div>