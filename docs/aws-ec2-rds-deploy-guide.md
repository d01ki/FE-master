# EC2 + RDS デプロイ手順書（初心者向け・詳細）

この手順書は `FE-master` リポジトリを AWS の EC2（Docker実行）と RDS（Postgres）で動かすための、初心者にも分かりやすい手順を1からまとめたものです。

目次
- 概要と前提
- 事前準備（IAM, AWS CLI, ブランチ）
- ローカル検証（必須チェック）
- デプロイ手順（実行）
- 起動後の確認とトラブルシュート
- 後片付け（リソース削除）
- 運用上の注意点と推奨設定

---

## 概要と前提

- 目的: EC2 上で Docker Compose によって Flask アプリを稼働させ、Postgres は RDS を利用する構成です。
- 前提:
  - AWS アカウント
  - ローカルに `git`, `aws` CLI, `docker`, `docker compose`, `ssh` がインストールされていること
  - このリポジトリをクローン済みであること（対象ブランチ: `feature/docker-aws-deployment`）
  - 適切な IAM 権限を持つアクセスキー（EC2, RDS, VPC, SG, KeyPair 作成権限など）

---

## 事前準備

1) ローカルブランチを最新にする
```bash
git fetch origin
git checkout feature/docker-aws-deployment
git pull origin feature/docker-aws-deployment
```

2) AWS CLI 設定確認
```bash
aws sts get-caller-identity
```
期待する出力: アカウントID と ARN が返る。エラーなら `aws configure` を実行して認証情報を設定してください。

3) 必要な変数を用意
- RDS マスター パスワード（強力なパスワードを用意）：`RDS_MASTER_PASSWORD`
- （任意）`AWS_REGION` を環境に合わせて指定

4) ローカルでのファイル確認
- `requirements.txt` が存在すること（このリポジトリでは追加済み）。
- `.env.sample` を参照して、必要な環境変数を把握してください。

---

## ローカル検証（本番を実行前に必ず行う）

1) Docker イメージがビルドできるか確認
```bash
docker build -t fe-master:local .
```
もしビルドが失敗したら、ログを読み `requirements.txt` の依存を確認してください。

2) docker compose 設定検証
```bash
docker compose -f docker-compose.yaml config
```
設定のマージや環境変数の参照に問題がないか確認します。

3) ローカルで起動確認（開発環境で）
```bash
docker compose -f docker-compose.yaml up --build
```
ブラウザで `http://localhost:5000/health` にアクセスして `status: healthy` が返るか確認します。

4) `.env` ファイルの作成（テスト用）
`.env.sample` をコピーして必要値を埋めてください。本番では `user-data.sh` が自動的に作成します。
```bash
cp .env.sample .env
# 編集してパスワードや DB ホストを設定
```

---

## デプロイ手順（EC2 + RDS）

※ 以下は安全に実行するための順序です。スクリプト `deploy-aws.sh` が多くの手順を自動化しますが、実行前に必ず確認してください。

1) RDS マスターパスワードを設定
```bash
export RDS_MASTER_PASSWORD='Your$ecurePassw0rd!'
```

2) AWS 認証確認
```bash
aws sts get-caller-identity
```

3) 実行（スクリプト）
```bash
./deploy-aws.sh
```
スクリプトのポイント:
- 既存の同名リソース（VPC, Subnet, Security Group, RDS, EC2）を検出して再利用します。
- RDS を新規作成する場合は作成後に待機してから EC2 を起動します。
- `user-data.sh` の `DB_ENDPOINT_PLACEHOLDER` と `DB_PASSWORD_PLACEHOLDER` を自動で埋めます。

4) 実行中に表示される情報を控える
- EC2 Public IP（後で SSH 接続・ブラウザ確認）
- RDS Endpoint

注意: `deploy-aws.sh` は作成済みリソースの再利用に対応しますが、既存リソースに意図しない副作用を与えないか事前に `aws ... describe-*` コマンドで確認してください。

---

## 起動後の確認

1) EC2 へ SSH で接続
```bash
ssh -i fe-master-key.pem ec2-user@<EC2_PUBLIC_IP>
```

2) cloud-init ログで初期化確認
```bash
sudo tail -n 200 /var/log/cloud-init-output.log
```
確認ポイント:
- `.env` が `/home/ec2-user/FE-master/.env` として作成されているか
- `docker compose` によるコンテナ起動ログ

3) コンテナ稼働確認
```bash
docker compose -f docker-compose.yaml ps
docker compose -f docker-compose.yaml logs -f app
```

4) アプリ確認
- ブラウザで `http://<EC2_PUBLIC_IP>:5000` を開き、ページが表示されるか確認。
- ユーザ登録・ログイン・問題表示ページなど主要なページをクリックして遷移確認を行ってください（画面遷移で 404 / 500 が出ないかを確認）。

---

## よくあるトラブル & 対処法

- コンテナが起動しない (CrashLoop):
  - `docker compose -f docker-compose.yaml logs app` を確認。`DATABASE_URL` が間違っている、`psycopg2` がない等のエラーを確認。

- DB 接続失敗:
  - RDS のセキュリティグループが EC2 の SG からのアクセス（ポート 5432）を許可しているか。`aws ec2 describe-security-groups --group-ids <sg>` で確認。

- page not found / 500 エラー:
  - アプリのテンプレート読み込みエラーやルート名の衝突。EC2 の `docker compose` ログを参照し、Traceback を掘る。

---

## 後片付け（不要になった場合の削除コマンド）

> 注意: 以下のコマンドは **リソースを完全に削除** します。課金対象リソースが消えますので慎重に実行してください。

- EC2 インスタンス削除
```bash
INSTANCE_ID=<id>
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
```

- RDS 削除
```bash
aws rds delete-db-instance --db-instance-identifier fe-master-db --skip-final-snapshot
```

- セキュリティグループ削除
```bash
aws ec2 delete-security-group --group-id <sg-id>
```

- VPC と関連リソースを削除する場合は、依存関係が複雑になるため AWS コンソールの VPC Wizard から確認・削除を推奨します。

---

## 運用上の注意点と推奨改善（実務）

1) シークレット管理
- `RDS_MASTER_PASSWORD` や `SECRET_KEY` は AWS Secrets Manager や SSM Parameter Store に保管し、EC2 の user-data で参照する方法に移行してください。

2) HTTPS 化
- 公開サービスにする場合は ALB（Application Load Balancer）＋ACM（証明書）で HTTPS 終端することを強く推奨します。

3) ログと監視
- CloudWatch Logs にアプリや Docker のログを送る設定を検討してください。EC2 に CloudWatch エージェントを導入するか、コンテナログの集約を行います。

4) バックアップ
- RDS の自動バックアップ（日次）とスナップショットを設定してください。uploads ディレクトリを使う場合は定期的に EBS スナップショットを取得するか、uploads を別ストレージに移すことを検討してください。

5) セキュリティ
- SSH のアクセス元を限定（`deploy-aws.sh` は自分の IP を自動で許可します）。
- 不要なポートは閉じる。OS レベルの自動アップデートとファイアウォールの設定を確認。

---

この手順書は、必要に応じて `deploy-aws.sh` の Dry-Run バージョンや、RDS スキーマ移行の `pg_dump/pg_restore` スクリプトを追加できます。どの部分を更に自動化/補足したいか教えてください。
