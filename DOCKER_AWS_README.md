# FE Master - AWS Docker デプロイメント

## 🏗️ システムアーキテクチャ

### 現在のアーキテクチャ (Docker Development)

```mermaid
graph TB
    User[👤 User] --> LB[🌐 Load Balancer<br/>localhost:5000]
    
    LB --> App[🐳 Flask Application<br/>Python 3.11]
    
    App --> DB[(🗄️ PostgreSQL 15<br/>Database)]
    App --> Static[📁 Static Files<br/>CSS/JS/Images]
    
    subgraph "Docker Compose Stack"
        App
        DB
        Static
    end
    
    subgraph "Application Structure"
        App --> Auth[🔐 Authentication<br/>Session-based]
        App --> API[🔌 API Routes<br/>Practice/Admin/Main]
        App --> Templates[📄 Jinja2 Templates<br/>Bootstrap UI]
    end
    
    subgraph "Data Flow"
        Auth --> Session[📝 User Sessions]
        API --> QuestionMgr[❓ Question Manager]
        QuestionMgr --> QuestDB[(Questions Table)]
        Auth --> UserMgr[👥 User Manager]
        UserMgr --> UserDB[(Users Table)]
        QuestionMgr --> AnswerDB[(Answers Table)]
    end
```

### 学習フロー図

```mermaid
flowchart LR
    Start([🚀 Start]) --> Login{🔐 Login?}
    Login -->|Yes| Role{👤 Role?}
    Login -->|No| Register[📝 Register]
    Register --> Login
    
    Role -->|Admin| AdminDash[👨‍💼 Admin Dashboard]
    Role -->|User| UserDash[📊 User Dashboard]
    
    AdminDash --> UserMgmt[👥 User Management]
    AdminDash --> DataUpload[📤 Data Upload]
    AdminDash --> SystemStats[📈 System Stats]
    
    UserDash --> Practice[🎯 Practice Mode]
    UserDash --> History[📚 History]
    UserDash --> Stats[📊 User Stats]
    
    Practice --> RandomQ[🎲 Random Questions]
    Practice --> GenreQ[🏷️ Genre Questions]
    
    RandomQ --> Answer[✍️ Answer Question]
    GenreQ --> Answer
    Answer --> Result[✅ Check Result]
    Result --> Save[💾 Save Answer]
    Save --> Practice
    
    History --> Review[👀 Review Answers]
```

### AWS デプロイメント環境

```mermaid
architecture-beta
    group aws(cloud)[AWS Cloud]
    
    service internet(internet)[Internet] in aws
    service cloudfront(cdn)[CloudFront CDN] in aws
    service alb(elb)[Application Load Balancer] in aws
    service ecs(container)[ECS Fargate Cluster] in aws
    service rds(database)[RDS PostgreSQL] in aws
    service s3(storage)[S3 Bucket] in aws
    service secrets(disk)[Secrets Manager] in aws
    service logs(logs)[CloudWatch Logs] in aws
    
    internet:R --> cloudfront:L
    cloudfront:R --> alb:L
    alb:R --> ecs:L
    ecs:R --> rds:L
    ecs:D --> s3:U
    ecs:B --> secrets:T
    ecs:B --> logs:T
```

### AWS インフラストラクチャ詳細

```mermaid
graph TB
    subgraph "🌍 External Access"
        User[👤 Users]
        Domain[🌐 Custom Domain<br/>fe-master.example.com]
    end
    
    User --> Domain
    Domain --> CDN
    
    subgraph "📡 Content Delivery"
        CDN[☁️ CloudFront<br/>Global CDN]
        S3Static[📦 S3 Bucket<br/>Static Assets]
    end
    
    CDN --> ALB
    CDN --> S3Static
    
    subgraph "🔀 Load Balancing"
        ALB[⚖️ Application Load Balancer<br/>Multi-AZ]
        TG[🎯 Target Groups<br/>Health Checks]
    end
    
    ALB --> TG
    
    subgraph "🐳 Container Platform"
        subgraph "ECS Cluster"
            direction TB
            Service[📋 ECS Service<br/>Auto Scaling]
            TaskA[📦 Task A<br/>Flask App]
            TaskB[📦 Task B<br/>Flask App]
            TaskC[📦 Task C<br/>Flask App]
        end
        
        Service --> TaskA
        Service --> TaskB 
        Service --> TaskC
        TG --> Service
    end
    
    subgraph "🗄️ Database Layer"
        RDS[(🗄️ RDS PostgreSQL<br/>Multi-AZ)]
        ReadReplica[(📖 Read Replica<br/>Read Scaling)]
    end
    
    TaskA --> RDS
    TaskB --> RDS
    TaskC --> RDS
    RDS --> ReadReplica
    
    subgraph "🔐 Security & Config"
        Secrets[🔒 Secrets Manager<br/>DB Credentials]
        IAM[👤 IAM Roles<br/>Service Permissions]
    end
    
    Service --> Secrets
    Service --> IAM
    
    subgraph "📊 Monitoring & Logs"
        CloudWatch[📈 CloudWatch<br/>Metrics & Alarms]
        LogGroups[📝 Log Groups<br/>Application Logs]
    end
    
    Service --> CloudWatch
    Service --> LogGroups
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
        CPU[⚙️ CPU Utilization]
        Memory[💾 Memory Usage]  
        Latency[⏱️ Response Time]
        Errors[❌ Error Rate]
        DBConn[🔗 DB Connections]
    end
    
    CloudWatch --> CPU
    CloudWatch --> Memory
    CloudWatch --> Latency
    CloudWatch --> Errors
    CloudWatch --> DBConn
    
    Alarms --> AutoScaling[📈 Auto Scaling]
    Logs --> Analysis[🔍 Log Analysis]
```

## 📋 デプロイメント手順

### ステップ 1: 環境準備
```bash
# AWS CLI設定
aws configure

# Terraform インフラ作成 (optional)
terraform init
terraform plan
terraform apply

# 環境変数設定
cp .env.aws.example .env.production
# .env.production を編集
```

### ステップ 2: コンテナデプロイ

### ステップ 2: コンテナデプロイ
```bash
# 1. イメージビルドとプッシュ
docker build -t fe-master .
docker tag fe-master:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/fe-master:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/fe-master:latest

# 2. ECS サービス作成/更新
aws ecs create-service \
    --cluster fe-master-cluster \
    --service-name fe-master-service \
    --task-definition fe-master:1 \
    --desired-count 2 \
    --launch-type FARGATE

# 3. デプロイメント確認
aws ecs describe-services \
    --cluster fe-master-cluster \
    --services fe-master-service
```

### ステップ 3: ドメイン設定
```bash
# Route 53 でDNS設定
aws route53 create-hosted-zone --name fe-master.example.com

# SSL証明書取得 (ACM)
aws acm request-certificate \
    --domain-name fe-master.example.com \
    --validation-method DNS
```

## 💰 AWS コスト見積もり

### 月間コスト概算

```mermaid
pie title AWS Monthly Cost Breakdown
    "ECS Fargate (2 tasks)" : 45
    "RDS PostgreSQL (t4g.medium)" : 25
    "Application Load Balancer" : 20
    "CloudFront CDN" : 10
    "S3 Storage" : 5
    "Other Services" : 10
```

- **ECS Fargate**: ~$45/月 (0.5 vCPU, 1GB RAM × 2 tasks)
- **RDS PostgreSQL**: ~$25/月 (db.t4g.medium)
- **Application Load Balancer**: ~$20/月
- **CloudFront**: ~$10/月 (1TB転送)
- **S3**: ~$5/月 (100GB storage)
- **その他**: ~$10/月 (CloudWatch, Secrets Manager等)

**総計**: ~$115/月

### コスト最適化のポイント

```mermaid
mindmap
  root(💰 Cost Optimization)
    Compute
      Reserved Instances
      Spot Instances
      Right Sizing
    Storage
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