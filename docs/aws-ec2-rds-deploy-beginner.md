# EC2 + RDS デプロイ手順（初心者向け）

このドキュメントは、`FE-master` アプリケーションを AWS の EC2 と RDS（Postgres）で動かすための、初心者向けの手順を一から丁寧に説明します。

前提
- AWS アカウントを持っていること
- ローカルに `git`、`aws` CLI、`ssh` がインストールされていること
- このリポジトリがローカルにクローン済みであること

目次
- 準備
- 重要ファイルの説明
- デプロイ実行手順（簡易）
- 起動後の動作確認
- トラブルシューティング
- 運用上の注意

1) 準備

- AWS CLI のセットアップ
  1. AWS IAM でアクセスキーを作成（EC2/RDS/EC2-KeyPair/SG 作成が可能な権限）
  2. ローカルで `aws configure` を実行し、`AWS_ACCESS_KEY_ID` と `AWS_SECRET_ACCESS_KEY` を設定

- ローカルのブランチを最新にする
```bash
git checkout feature/docker-aws-deployment
git pull origin feature/docker-aws-deployment
```

- 必要な準備ファイル（ローカル）
  - `requirements.txt`（このリポジトリに追加済み）
  - `.env.sample`（例の環境変数ファイルが追加済み）

2) 重要ファイルの説明

- `deploy-aws.sh` - EC2・VPC・RDS を作成して EC2 インスタンスを起動するスクリプト。実行時に RDS のマスターパスワードを環境変数 `RDS_MASTER_PASSWORD` で渡すかプロンプトで入力します。
- `user-data.sh` - EC2 起動時に実行されるスクリプト。リポジトリをクローンし `.env` を作成して `docker compose` でアプリを起動します。`deploy-aws.sh` が `DB_ENDPOINT` と `DB_PASSWORD` を注入します。
- `docker-compose.yaml` - コンテナ定義。EC2 上で `docker compose` により起動されます。

3) デプロイ実行手順（簡易）

- 1. RDS マスターパスワードの用意（例：安全なパスワードを生成）
```bash
export RDS_MASTER_PASSWORD='Your$ecurePassw0rd!'
```

- 2. AWS 認証が動作するか確認
```bash
aws sts get-caller-identity
```

- 3. `deploy-aws.sh` を実行（スクリプトが VPC・サブネット・RDS・EC2 を作成します）
```bash
./deploy-aws.sh
```

スクリプトは自動的に以下を行います:
- 既存の同名リソースがあれば再利用
- RDS の作成（または既存 RDS の再利用）
- `user-data.sh` 内のプレースホルダを RDS エンドポイントとパスワードで置換
- EC2 インスタンスを起動し、`docker compose` でアプリを立ち上げる

4) 起動後の確認

- EC2 のパブリックIP を取得してブラウザでアクセス（ポート 5000）
  - スクリプト実行後に表示される `EC2 Public IP` を確認
  - ブラウザで `http://<EC2_PUBLIC_IP>:5000` を開く

- SSH 接続してログ確認
```bash
ssh -i fe-master-key.pem ec2-user@<EC2_PUBLIC_IP>
sudo tail -f /var/log/cloud-init-output.log
docker compose -f docker-compose.yaml ps
docker compose -f docker-compose.yaml logs -f app
```

- DB 接続確認
  - RDS のエンドポイントはデプロイ時に表示されます
  - `psql` 等で接続できるか確認（ローカルからは公開されていないことが多いので EC2 経由で行う）

5) トラブルシューティング（よくある問題）

- EC2 に `docker compose` が入っていない/権限がない
  - `user-data.sh` は `docker compose` をインストールしますが、AMI により一部コマンドが異なることがあります。
  - SSH で入り `docker compose version` を確認。

- コンテナが CrashLoop する
  - `docker compose -f docker-compose.yaml logs app` でログを確認
  - `.env`（`DATABASE_URL`・`SECRET_KEY`）が正しく設定されているか確認

- RDS に接続できない
  - セキュリティグループで EC2 の SG が RDS のポート（5432）を許可していること

6) 運用上の注意（初心者向け）

- 秘密情報は環境変数で渡してください（`deploy-aws.sh` は `RDS_MASTER_PASSWORD` を扱います）。長期的には AWS Secrets Manager を使うことを推奨します。
- バックアップ: RDS の自動バックアップ設定とスナップショット取得を確認してください。
- セキュリティ: SSH アクセスは自分の IP のみに制限してください（`deploy-aws.sh` は現在自分の IP を自動で許可します）。

7) 付録: よく使うコマンド

- 現在の EC2 状態確認
```bash
aws ec2 describe-instances --filters "Name=tag:Name,Values=fe-master-api"
```

- RDS エンドポイント確認
```bash
aws rds describe-db-instances --db-instance-identifier fe-master-db --query 'DBInstances[0].Endpoint.Address' --output text
```

---

この手順で不明点があれば、どの箇所で詰まったか教えてください。必要であれば `deploy-aws.sh` を実行する前に追加の安全チェックや Dry-Run オプションをスクリプトに追加します。
