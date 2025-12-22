# FE Master - AWS デプロイメント

## 🏗️ システムアーキテクチャ

### AWS デプロイメント構成

```mermaid
graph TB
    subgraph "🌐 Internet"
        User[👤 Users]
    end
    
    subgraph "AWS VPC (10.0.0.0/16)"
        subgraph "🌍 Public Subnet (10.0.1.0/24)"
            EC2[🖥️ EC2 Instance<br/>Docker + Flask App<br/>Security Group: sg-api]
        end
        
        subgraph "🔒 Private Subnet (10.0.2.0/24)"
            RDS[(🗄️ RDS PostgreSQL<br/>Security Group: sg-db)]
        end
    end
    
    User --> EC2
    EC2 --> RDS
```

### セキュリティグループ構成

```mermaid
graph LR
    subgraph "🛡️ Security Groups"
        subgraph "sg-api (EC2)"
            HTTP[HTTP: 80<br/>Source: 0.0.0.0/0]
            HTTPS[HTTPS: 443<br/>Source: 0.0.0.0/0]
            SSH[SSH: 22<br/>Source: My IP]
            App[App: 5000<br/>Source: 0.0.0.0/0]
        end
        
        subgraph "sg-db (RDS)"
            PostgreSQL[PostgreSQL: 5432<br/>Source: sg-api]
        end
    end
```

## 📋 AWS デプロイメント手順

### 1. 事前準備

```bash
# AWS CLI設定
aws configure

# キーペア作成（EC2接続用）
aws ec2 create-key-pair --key-name fe-master-key --query 'KeyMaterial' --output text > fe-master-key.pem
chmod 400 fe-master-key.pem
```

### 2. VPCとネットワーク作成

```bash
# VPC作成
VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 --query 'Vpc.VpcId' --output text)
aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=fe-master-vpc

# インターネットゲートウェイ作成
IGW_ID=$(aws ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text)
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID

# パブリックサブネット作成
PUBLIC_SUBNET_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
aws ec2 create-tags --resources $PUBLIC_SUBNET_ID --tags Key=Name,Value=fe-master-public-subnet

# プライベートサブネット作成
PRIVATE_SUBNET_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
aws ec2 create-tags --resources $PRIVATE_SUBNET_ID --tags Key=Name,Value=fe-master-private-subnet

# プライベートサブネット作成（DB用、別AZ）
PRIVATE_SUBNET_2_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.3.0/24 --availability-zone us-east-1b --query 'Subnet.SubnetId' --output text)
aws ec2 create-tags --resources $PRIVATE_SUBNET_2_ID --tags Key=Name,Value=fe-master-private-subnet-2

# ルートテーブル設定
ROUTE_TABLE_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID --query 'RouteTable.RouteTableId' --output text)
aws ec2 create-route --route-table-id $ROUTE_TABLE_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_ID --route-table-id $ROUTE_TABLE_ID
```

### 3. セキュリティグループ作成

```bash
# API用セキュリティグループ（sg-api）
API_SG_ID=$(aws ec2 create-security-group --group-name sg-api --description "Security group for API server" --vpc-id $VPC_ID --query 'GroupId' --output text)

# APIセキュリティグループのルール設定
aws ec2 authorize-security-group-ingress --group-id $API_SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $API_SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $API_SG_ID --protocol tcp --port 5000 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $API_SG_ID --protocol tcp --port 22 --cidr $(curl -s https://checkip.amazonaws.com/)/32

# DB用セキュリティグループ（sg-db）
DB_SG_ID=$(aws ec2 create-security-group --group-name sg-db --description "Security group for database" --vpc-id $VPC_ID --query 'GroupId' --output text)

# DBセキュリティグループのルール設定（APIサーバーからのアクセスのみ）
aws ec2 authorize-security-group-ingress --group-id $DB_SG_ID --protocol tcp --port 5432 --source-group $API_SG_ID
```

### 4. RDS作成

```bash
# DBサブネットグループ作成
aws rds create-db-subnet-group \
  --db-subnet-group-name fe-master-db-subnet-group \
  --db-subnet-group-description "Subnet group for FE Master database" \
  --subnet-ids $PRIVATE_SUBNET_ID $PRIVATE_SUBNET_2_ID

# PostgreSQLインスタンス作成
aws rds create-db-instance \
  --db-instance-identifier fe-master-db \
  --db-instance-class db.t4g.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password YourSecurePassword123! \
  --allocated-storage 20 \
  --vpc-security-group-ids $DB_SG_ID \
  --db-subnet-group-name fe-master-db-subnet-group \
  --backup-retention-period 7 \
  --no-multi-az \
  --no-publicly-accessible

# RDS作成完了待ち（5-10分程度）
aws rds wait db-instance-available --db-instance-identifier fe-master-db
```

### 5. EC2インスタンス作成

```bash
# RDSエンドポイント取得
DB_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier fe-master-db --query 'DBInstances[0].Endpoint.Address' --output text)

# ユーザーデータにRDSエンドポイントを設定
sed -i "s/DB_ENDPOINT_PLACEHOLDER/$DB_ENDPOINT/g" user-data.sh

# EC2インスタンス起動
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.micro \
  --key-name fe-master-key \
  --security-group-ids $API_SG_ID \
  --subnet-id $PUBLIC_SUBNET_ID \
  --associate-public-ip-address \
  --user-data file://user-data.sh \
  --query 'Instances[0].InstanceId' --output text)

aws ec2 create-tags --resources $INSTANCE_ID --tags Key=Name,Value=fe-master-api

# パブリックIPアドレス取得
EC2_PUBLIC_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "EC2 Public IP: $EC2_PUBLIC_IP"
```

## 🔄 デプロイメントフロー

### 自動デプロイメント

```bash
# デプロイスクリプト例（deploy.sh）
#!/bin/bash
set -e

# 1. コードの更新
ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP "cd FE-master && git pull origin main"

# 2. Dockerイメージの再ビルド
ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP "cd FE-master && docker-compose -f docker-compose.prod.yml build"

# 3. サービスの再起動
ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP "cd FE-master && docker-compose -f docker-compose.prod.yml up -d"

# 4. ヘルスチェック
sleep 30
curl -f http://$EC2_PUBLIC_IP:5000/ || exit 1
echo "デプロイメント完了!"
```

## 📊 監視とメンテナンス

### CloudWatchアラーム設定

```bash
# CPU使用率アラーム
aws cloudwatch put-metric-alarm \
  --alarm-name "fe-master-high-cpu" \
  --alarm-description "High CPU utilization" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --evaluation-periods 2

# RDS接続アラーム
aws cloudwatch put-metric-alarm \
  --alarm-name "fe-master-rds-connections" \
  --alarm-description "High database connections" \
  --metric-name DatabaseConnections \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=DBInstanceIdentifier,Value=fe-master-db \
  --evaluation-periods 2
```

## 🔒 セキュリティベストプラクティス

### SSL/TLS証明書設定（オプション）

```bash
# Let's Encryptで無料SSL証明書取得
ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP << 'EOF'
sudo yum install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Nginxリバースプロキシ設定
sudo tee /etc/nginx/conf.d/fe-master.conf << 'NGINX'
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

sudo systemctl reload nginx
EOF
```

## 💰 AWS コスト見積もり

### 月間コスト概算

```mermaid
pie title AWS Monthly Cost Breakdown
    "EC2 t3.micro" : 8
    "RDS t4g.micro" : 15  
    "Data Transfer" : 5
    "EBS Storage" : 3
    "Other" : 4
```

- **EC2 t3.micro**: ~$8.5/月 (730時間)
- **RDS t4g.micro**: ~$15/月 (Single-AZ)
- **EBS Storage**: ~$3/月 (30GB gp3)
- **Data Transfer**: ~$5/月 (100GB out)
- **その他**: ~$4/月 (CloudWatch等)

**総計**: ~$35/月

## 🚀 クイックスタート

### 開発環境
```bash
# 1. リポジトリクローン
git clone https://github.com/your-username/FE-master.git
cd FE-master

# 2. Docker起動
docker-compose up -d

# 3. アクセス
open http://localhost:5000
```

### AWS本番環境（一括実行）
```bash
# 1. deploy-aws.shスクリプトを実行
chmod +x deploy-aws.sh
./deploy-aws.sh

# 2. 接続確認
curl http://EC2-PUBLIC-IP:5000
```

## 🔧 トラブルシューティング

### よくある問題

1. **EC2インスタンスに接続できない**
   ```bash
   # セキュリティグループ確認
   aws ec2 describe-security-groups --group-ids $API_SG_ID
   
   # SSH接続テスト
   ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP
   ```

2. **RDSに接続できない**
   ```bash
   # RDS状態確認
   aws rds describe-db-instances --db-instance-identifier fe-master-db
   
   # セキュリティグループ確認
   aws ec2 describe-security-groups --group-ids $DB_SG_ID
   ```

3. **アプリケーションが起動しない**
   ```bash
   # Docker Composeログ確認
   ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP "cd FE-master && docker-compose -f docker-compose.prod.yml logs"
   
   # 環境変数確認
   ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP "cd FE-master && cat .env"
   ```

## 📝 メンテナンス

### 定期メンテナンス

```bash
# 1. バックアップ確認
aws rds describe-db-snapshots --db-instance-identifier fe-master-db

# 2. ログローテーション
ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP "docker system prune -f"

# 3. セキュリティアップデート
ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP "sudo yum update -y"
```

### スケーリング

```bash
# インスタンスタイプ変更
aws ec2 modify-instance-attribute \
  --instance-id $INSTANCE_ID \
  --instance-type Value=t3.small

# RDSスケールアップ
aws rds modify-db-instance \
  --db-instance-identifier fe-master-db \
  --db-instance-class db.t4g.small \
  --apply-immediately
```

## 💡 ベストプラクティス

### セキュリティ
- SSH接続は特定IPからのみ許可
- RDSは必ずプライベートサブネットに配置
- 定期的なセキュリティアップデート実施

### 可用性
- Multi-AZデプロイメント（コスト増）
- Auto Scalingの導入（トラフィック増加時）
- CloudWatchによる監視とアラート

### コスト最適化
- Reserved Instanceの利用
- 適切なインスタンスサイズの選択
- 不要なリソースの定期削除

---

> 📝 **注意**: 実際のデプロイメント前に、パスワードやドメイン名などの設定値を適切に変更してください。

## 📋 AWS デプロイメント手順

### 1. 事前準備

```bash
# AWS CLI設定
aws configure

# キーペア作成（EC2接続用）
aws ec2 create-key-pair --key-name fe-master-key --query 'KeyMaterial' --output text > fe-master-key.pem
chmod 400 fe-master-key.pem
```

### 2. VPCとネットワーク作成

```bash
# VPC作成
VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 --query 'Vpc.VpcId' --output text)
aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=fe-master-vpc

# インターネットゲートウェイ作成
IGW_ID=$(aws ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text)
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID

# パブリックサブネット作成
PUBLIC_SUBNET_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
aws ec2 create-tags --resources $PUBLIC_SUBNET_ID --tags Key=Name,Value=fe-master-public-subnet

# プライベートサブネット作成
PRIVATE_SUBNET_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
aws ec2 create-tags --resources $PRIVATE_SUBNET_ID --tags Key=Name,Value=fe-master-private-subnet

# プライベートサブネット作成（DB用、別AZ）
PRIVATE_SUBNET_2_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.3.0/24 --availability-zone us-east-1b --query 'Subnet.SubnetId' --output text)
aws ec2 create-tags --resources $PRIVATE_SUBNET_2_ID --tags Key=Name,Value=fe-master-private-subnet-2

# ルートテーブル設定
ROUTE_TABLE_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID --query 'RouteTable.RouteTableId' --output text)
aws ec2 create-route --route-table-id $ROUTE_TABLE_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_ID --route-table-id $ROUTE_TABLE_ID
```

### 3. セキュリティグループ作成

```bash
# API用セキュリティグループ（sg-api）
API_SG_ID=$(aws ec2 create-security-group --group-name sg-api --description "Security group for API server" --vpc-id $VPC_ID --query 'GroupId' --output text)

# APIセキュリティグループのルール設定
aws ec2 authorize-security-group-ingress --group-id $API_SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $API_SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $API_SG_ID --protocol tcp --port 5000 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $API_SG_ID --protocol tcp --port 22 --cidr $(curl -s https://checkip.amazonaws.com/)/32

# DB用セキュリティグループ（sg-db）
DB_SG_ID=$(aws ec2 create-security-group --group-name sg-db --description "Security group for database" --vpc-id $VPC_ID --query 'GroupId' --output text)

# DBセキュリティグループのルール設定（APIサーバーからのアクセスのみ）
aws ec2 authorize-security-group-ingress --group-id $DB_SG_ID --protocol tcp --port 5432 --source-group $API_SG_ID
```

### 4. RDS作成

```bash
# DBサブネットグループ作成
aws rds create-db-subnet-group \
  --db-subnet-group-name fe-master-db-subnet-group \
  --db-subnet-group-description "Subnet group for FE Master database" \
  --subnet-ids $PRIVATE_SUBNET_ID $PRIVATE_SUBNET_2_ID

# PostgreSQLインスタンス作成
aws rds create-db-instance \
  --db-instance-identifier fe-master-db \
  --db-instance-class db.t4g.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password YourSecurePassword123! \
  --allocated-storage 20 \
  --vpc-security-group-ids $DB_SG_ID \
  --db-subnet-group-name fe-master-db-subnet-group \
  --backup-retention-period 7 \
  --no-multi-az \
  --no-publicly-accessible

# RDS作成完了待ち（5-10分程度）
aws rds wait db-instance-available --db-instance-identifier fe-master-db
```

## 🐳 Docker環境について

このプロジェクトはDocker化されており、以下の環境で動作可能です：
- ローカル開発環境（SQLite + Redis）
- AWS本番環境（PostgreSQL + ElastiCache）

### 🚀 クイックスタート

```bash
# 1. リポジトリをクローン
git clone https://github.com/d01ki/FE-master.git
cd FE-master

# 2. Dockerで起動
docker-compose up -d

# 3. ブラウザでアクセス
open http://localhost:5000
```

### 📁 ファイル構成

```
├── Dockerfile              # メインアプリケーション
├── docker-compose.yml      # 開発環境用構成
├── .dockerignore           # Dockerビルド除外設定
├── .env.docker            # Docker開発環境用変数
└── .env.aws.example       # AWS本番環境テンプレート
```

### � AWS デプロイメント戦略

### デプロイメントフロー

```mermaid
gitGraph:
    commit id: "Development"
    branch feature
    checkout feature
    commit id: "Feature Work"
    commit id: "Local Testing"
    checkout main
    merge feature
    commit id: "Integration"
    commit id: "Build Docker Image"
    commit id: "Push to ECR"
    commit id: "Deploy to ECS"
    commit id: "Production Ready"
```

### CI/CD Pipeline

```mermaid
flowchart LR
    subgraph "🔄 CI/CD Pipeline"
        Code[💻 Code Push] --> Test[🧪 Unit Tests]
        Test --> Build[🏗️ Docker Build]
        Build --> Scan[🔍 Security Scan]
        Scan --> Push[📤 Push to ECR]
        Push --> Deploy[🚀 Deploy to ECS]
        Deploy --> Health[❤️ Health Check]
        Health --> Monitor[📊 Monitoring]
    end
    
    subgraph "🛡️ Security Gates"
        SAST[🔒 Static Analysis]
        DAST[🛡️ Dynamic Analysis] 
        Deps[📦 Dependency Check]
    end
    
    Test --> SAST
    Build --> Deps
    Deploy --> DAST
```

## 🔧 AWS 環境設定

### 1. ECR (Container Registry)
```bash
# ECRリポジトリ作成
aws ecr create-repository --repository-name fe-master

# Docker認証
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
```

### 2. ECS クラスター構成

```yaml
# ecs-cluster.yml
Resources:
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: fe-master-cluster
      CapacityProviders:
        - FARGATE
        - FARGATE_SPOT
      DefaultCapacityProviderStrategy:
        - CapacityProvider: FARGATE
          Weight: 1
        - CapacityProvider: FARGATE_SPOT
          Weight: 4
```

### 3. RDS データベース設定

```mermaid
graph TB
    subgraph "🗄️ Database Architecture"
        Primary[(🗄️ Primary DB<br/>Multi-AZ<br/>db.t4g.medium)]
        Replica[(📖 Read Replica<br/>Single-AZ<br/>db.t4g.small)]
        Backup[💾 Automated Backups<br/>7-day retention]
    end
    
    subgraph "🔐 Security"
        VPC[🏠 VPC<br/>10.0.0.0/16]
        PrivateSubnet[🔒 Private Subnets<br/>10.0.1.0/24, 10.0.2.0/24]
        SecurityGroup[🛡️ DB Security Group<br/>Port 5432 from ECS only]
    end
    
    Primary --> Replica
    Primary --> Backup
    Primary --> PrivateSubnet
    Replica --> PrivateSubnet
    PrivateSubnet --> SecurityGroup
```

### 4. セキュリティ設定

```mermaid
mindmap
  root(🛡️ Security)
    Network
      VPC Isolation
      Private Subnets
      Security Groups
      NACLs
    Application
      HTTPS Only
      Session Security
      Input Validation
      CSRF Protection
    Infrastructure
      IAM Roles
      Secrets Manager
      CloudTrail Logging
      GuardDuty
    Data
      Encryption at Rest
      Encryption in Transit
      Backup Encryption
      PII Protection
```

### 5. モニタリング設定

```mermaid
graph TB
    subgraph "📊 Monitoring Stack"
        CloudWatch[📈 CloudWatch<br/>Metrics & Dashboards]
        Alarms[🚨 CloudWatch Alarms<br/>Auto Scaling Triggers]
        Logs[📝 CloudWatch Logs<br/>Centralized Logging]
        XRay[🔍 X-Ray<br/>Distributed Tracing]
    end
    
    subgraph "🎯 Key Metrics"
## 💰 AWS コスト見積もり

### 月間コスト概算

```mermaid
pie title AWS Monthly Cost Breakdown
    "EC2 t3.micro" : 8
    "RDS t4g.micro" : 15  
    "Data Transfer" : 5
    "EBS Storage" : 3
    "Other" : 4
```

- **EC2 t3.micro**: ~$8.5/月 (730時間)
- **RDS t4g.micro**: ~$15/月 (Single-AZ)
- **EBS Storage**: ~$3/月 (30GB gp3)
- **Data Transfer**: ~$5/月 (100GB out)
- **その他**: ~$4/月 (CloudWatch等)

**総計**: ~$35/月

## 🚀 クイックスタート

### 開発環境
```bash
# 1. リポジトリクローン
git clone https://github.com/your-username/FE-master.git
cd FE-master

# 2. Docker起動
docker-compose up -d

# 3. アクセス
open http://localhost:5000
```

### AWS本番環境
```bash
# 1. 環境変数設定
export VPC_ID=vpc-xxxxxxxxx
export PUBLIC_SUBNET_ID=subnet-xxxxxxxxx  
export PRIVATE_SUBNET_ID=subnet-xxxxxxxxx
export API_SG_ID=sg-xxxxxxxxx
export DB_SG_ID=sg-xxxxxxxxx

# 2. 一括デプロイ
./scripts/deploy-aws.sh

# 3. 接続確認
curl http://EC2-PUBLIC-IP:5000
```

## 🔧 トラブルシューティング

### よくある問題

1. **EC2インスタンスに接続できない**
   ```bash
   # セキュリティグループ確認
   aws ec2 describe-security-groups --group-ids $API_SG_ID
   
   # SSH接続テスト
   ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP
   ```

2. **RDSに接続できない**
   ```bash
   # RDS状態確認
   aws rds describe-db-instances --db-instance-identifier fe-master-db
   
   # セキュリティグループ確認
   aws ec2 describe-security-groups --group-ids $DB_SG_ID
   ```

3. **アプリケーションが起動しない**
   ```bash
   # Docker Composeログ確認
   ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP "cd FE-master && docker-compose -f docker-compose.prod.yml logs"
   
   # 環境変数確認
   ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP "cd FE-master && cat .env"
   ```

## 📝 メンテナンス

### 定期メンテナンス

```bash
# 1. バックアップ確認
aws rds describe-db-snapshots --db-instance-identifier fe-master-db

# 2. ログローテーション
ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP "docker system prune -f"

# 3. セキュリティアップデート
ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP "sudo yum update -y"
```

### スケーリング

```bash
# インスタンスタイプ変更
aws ec2 modify-instance-attribute \
  --instance-id $INSTANCE_ID \
  --instance-type Value=t3.small

# RDSスケールアップ
aws rds modify-db-instance \
  --db-instance-identifier fe-master-db \
  --db-instance-class db.t4g.small \
  --apply-immediately
```
      Lifecycle Policies
      Compression
      Archiving
    Network
      CloudFront Optimization
      Regional Optimization
    Monitoring
      Cost Alerts
      Usage Analytics
      Resource Cleanup
```

## 🔄 運用・メンテナンス

### バックアップ戦略
- **RDS**: 自動バックアップ (7日保持)
- **S3**: Cross-Region Replication
- **ECS**: Blue-Green Deployment

### スケーリング戦略
- **水平スケーリング**: ECS Auto Scaling (CPU 70%閾値)
- **垂直スケーリング**: タスク定義のリソース調整
- **データベース**: Read Replica追加

### セキュリティ運用
- **定期的な脆弱性スキャン**
- **アクセスログの監視**
- **セキュリティパッチ適用**
- **IAM権限の定期レビュー**

---

> 💡 **ヒント**: 本格運用前にステージング環境で十分にテストを行い、監視・アラートの設定を確認してください。

## 🎯 クイックスタート

#### 1. ECS (推奨)
```bash
# イメージビルドとプッシュ
docker build -t fe-master .
docker tag fe-master:latest your-account.dkr.ecr.region.amazonaws.com/fe-master:latest
docker push your-account.dkr.ecr.region.amazonaws.com/fe-master:latest
```

#### 2. EC2 + Docker
```bash
# EC2インスタンスでDockerをインストール後
git clone https://github.com/d01ki/FE-master.git
cd FE-master
cp .env.aws.example .env
# .envファイルを本番用に編集
docker-compose --profile production up -d
```

### 🗄️ データベース設定

#### 開発環境（SQLite）
```yaml
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///fe_exam.db
```

#### 本番環境（AWS RDS PostgreSQL）
```yaml
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### 📋 必要なAWSリソース

1. **ECR** - Dockerイメージレジストリ
2. **ECS** - コンテナ実行環境
3. **RDS** - PostgreSQLデータベース
4. **ElastiCache** - Redisキャッシュ
5. **Application Load Balancer** - ロードバランサー
6. **Route 53** - DNS管理

### 🔒 セキュリティ設定

本番環境では以下の環境変数を必ず設定してください：

```bash
SECRET_KEY=cryptographically-strong-secret-key
ADMIN_PASSWORD=secure-admin-password
DATABASE_URL=postgresql://user:password@host:5432/db
REDIS_URL=redis://cache-host:6379
```

### 🔍 ヘルスチェック

アプリケーションには以下のヘルスチェックエンドポイントがあります：
- `GET /` - アプリケーションが正常に動作しているかチェック

### 📊 監視とログ

- CloudWatchでログとメトリクスを監視
- ECSタスクのヘルスチェックでアプリケーション状態を監視
- ALBのヘルスチェックでロードバランシング

### 🚨 トラブルシューティング

1. **データベース接続エラー**
   ```bash
   # データベース設定を確認
   echo $DATABASE_URL
   ```

2. **Redis接続エラー**
   ```bash
   # Redis設定を確認
   echo $REDIS_URL
   ```

3. **ポート設定エラー**
   ```bash
   # ポート設定を確認
   echo $PORT
   ```