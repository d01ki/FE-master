#!/bin/bash
yum update -y
yum install -y docker git

# Dockerサービス開始
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Docker Composeインストール
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# プロジェクトクローン（実際のリポジトリURLに変更してください）
cd /home/ec2-user
git clone https://github.com/d01ki/FE-master.git
cd FE-master

# 環境変数設定（RDSエンドポイントは自動取得）
cat > .env << EOF
DATABASE_URL=postgresql://postgres:YourSecurePassword123!@DB_ENDPOINT_PLACEHOLDER:5432/postgres
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)
EOF

# Dockerコンテナ起動
docker-compose -f docker-compose.prod.yml up -d