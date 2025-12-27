<div align="center">

# FE Master

### 基本情報技術者試験 学習アプリケーション

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**効率的な学習で基本情報技術者試験の合格を目指す**

</div>

---

## 特徴

<table>
<tr>
<td width="33%" align="center">

### ランダム問題
毎日異なる問題で<br>飽きずに学習

</td>
<td width="33%" align="center">

### ジャンル別演習
苦手分野を<br>集中的に克服

</td>
<td width="33%" align="center">

### 模擬試験
本番形式で<br>実力を確認

</td>
</tr>
</table>

### 主な機能

- **レスポンシブデザイン** - PC・スマホどちらでも快適に学習
- **学習履歴管理** - あなたの進捗を詳細に追跡
- **画像対応** - 図表付き問題も完全サポート
- **ユーザー認証** - 個人の学習データを安全に保管

---

## 技術スタック

<div align="center">

| カテゴリ | 技術 |
|:---:|:---|
| **Backend** | Python 3.11+, Flask 2.3+ |
| **Database** | MySQL 8.0+ |
| **Frontend** | HTML5, Tailwind CSS, JavaScript |
| **Container** | Docker, Docker Compose |
| **Architecture** | Application Factory Pattern |

</div>

## プロジェクト構成

```
app/
├── core/         # コア機能 (認証、設定、DB等)
├── routes/       # ルーティング
├── templates/    # Jinja2テンプレート
├── static/       # 静的ファイル (CSS/JS/画像)
└── scripts/      # ユーティリティスクリプト
```

---

## 🚀 クイックスタート

### Docker での起動 (推奨)

```bash
# リポジトリをクローン
git clone https://github.com/d01ki/FE-master.git
cd FE-master

# Docker で一発起動
docker-compose up -d
```

http://localhost:5000 でアクセスできます！

### 🎯 使い方

1. **アカウント作成**: 新規登録ページでアカウントを作成
2. **ランダム問題**: すぐに問題演習を開始
3. **ジャンル別演習**: 苦手分野を集中的に学習
4. **学習履歴**: 進捗状況を確認・分析

> 💡 管理者機能（問題アップロード等）については、設定ファイルを参照してください

### ローカル開発

```bash
# 仮想環境を作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt

# アプリケーションを起動
python app.py
```

http://localhost:5002 でアクセスできます！

---

## デプロイ

詳しいデプロイ手順は [Wiki](https://github.com/d01ki/FE-master/wiki) をご覧ください。

---

## 貢献

プルリクエストを歓迎します！

1. フォークする
2. ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. プッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

---

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

---

<div align="center">

**Made with care by FE Master Team**

このプロジェクトが役に立ったら、スターをお願いします！

</div>
