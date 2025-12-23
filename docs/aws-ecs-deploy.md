# AWS ECS (Fargate) Deployment Guide

このドキュメントは、`FE-master` アプリを AWS ECS (Fargate) へデプロイする手順をまとめたものです。

前提
- AWS アカウントと適切な IAM 権限（ECR/ECS/RDS/SecretsManager 等）を持っていること
- `AWS_ACCESS_KEY_ID` と `AWS_SECRET_ACCESS_KEY` を GitHub Secrets に設定していること
- 既に ECS クラスターとサービス（Fargate）が存在すること（作成方法は別途記載）

必須 GitHub Secrets
- `AWS_REGION` - 例: `us-east-1`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `ECR_REPOSITORY` - ECR リポジトリ名
- `ECS_CLUSTER` - ECS クラスター名
- `ECS_SERVICE` - ECS サービス名

ワークフロー（.github/workflows/ecs-deploy.yml）
- コミット/プッシュ時に自動で Docker イメージをビルドして ECR へ push
- 現行のタスク定義を取得し、コンテナイメージを更新した新しいタスク定義を登録
- ECS サービスを新しいタスク定義で更新してデプロイを行う

RDS
- DB は RDS（Postgres）を使用する想定です。`deploy-aws.sh` に RDS 作成スクリプトを用意していますが、本番では RDS のパラメータ（パスワード等）は Secrets Manager を使って管理してください。

S3（アップロード）
- アップロード機能を S3 に切り替えることを推奨します。`uploads/` を S3 に置き換え、Flask のアップロード処理を S3 に対応させてください（`boto3` を使用）。

参考コマンド
- ローカルで構成を検証する:
```bash
docker compose -f docker-compose.yaml config
```
- ECR リポジトリ作成:
```bash
aws ecr create-repository --repository-name <repo-name>
```

次のステップ
1. Secrets を GitHub に登録
2. ECR リポジトリと ECS クラスター/サービスを準備
3. `ecs-deploy.yml` を main ブランチへマージ
4. プッシュして自動デプロイを確認

問題や追加で自動化したい箇所（CloudFormation/Cloud Development Kit の導入など）があれば教えてください。
