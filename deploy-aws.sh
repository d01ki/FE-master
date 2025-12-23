#!/bin/bash
set -e

echo "🚀 FE Master AWS デプロイメント開始"

# AWS CLI設定確認
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLIが設定されていません。'aws configure'を実行してください。"
    exit 1
fi

echo "✅ AWS CLI設定確認完了"

# 1. キーペア作成（存在する場合は再利用）
echo "🔑 キーペア確認..."
if ! aws ec2 describe-key-pairs --key-names fe-master-key &> /dev/null; then
  aws ec2 create-key-pair --key-name fe-master-key --query 'KeyMaterial' --output text > fe-master-key.pem
  chmod 400 fe-master-key.pem
  echo "✅ キーペア作成完了"
else
  echo "ℹ️  キーペア 'fe-master-key' は既に存在します（再利用します）"
fi

# 2. VPC作成
echo "🏠 VPC 確認/作成..."
# 再実行可能に: 既存の VPC がタグ名で存在するかチェックして再利用
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=fe-master-vpc" --query 'Vpcs[0].VpcId' --output text 2>/dev/null || true)
if [ -n "$VPC_ID" ] && [ "$VPC_ID" != "None" ]; then
  echo "ℹ️  既存の VPC を再利用します: $VPC_ID"
else
  VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 --query 'Vpc.VpcId' --output text)
  aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=fe-master-vpc
  echo "✅ VPC作成完了: $VPC_ID"
fi

# 3. インターネットゲートウェイ
echo "🌐 インターネットゲートウェイ作成中..."
IGW_ID=$(aws ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text)
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID
echo "✅ インターネットゲートウェイ作成完了: $IGW_ID"

# 4. サブネット作成
echo "📡 サブネット確認/作成..."
# 既存サブネットを探して再利用、なければ作成
PUBLIC_SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=fe-master-public-subnet" --query 'Subnets[0].SubnetId' --output text 2>/dev/null || true)
if [ -z "$PUBLIC_SUBNET_ID" ] || [ "$PUBLIC_SUBNET_ID" = "None" ]; then
  PUBLIC_SUBNET_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
  aws ec2 create-tags --resources $PUBLIC_SUBNET_ID --tags Key=Name,Value=fe-master-public-subnet
fi

PRIVATE_SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=fe-master-private-subnet" --query 'Subnets[0].SubnetId' --output text 2>/dev/null || true)
if [ -z "$PRIVATE_SUBNET_ID" ] || [ "$PRIVATE_SUBNET_ID" = "None" ]; then
  PRIVATE_SUBNET_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
  aws ec2 create-tags --resources $PRIVATE_SUBNET_ID --tags Key=Name,Value=fe-master-private-subnet
fi

PRIVATE_SUBNET_2_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=fe-master-private-subnet-2" --query 'Subnets[0].SubnetId' --output text 2>/dev/null || true)
if [ -z "$PRIVATE_SUBNET_2_ID" ] || [ "$PRIVATE_SUBNET_2_ID" = "None" ]; then
  PRIVATE_SUBNET_2_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.3.0/24 --availability-zone us-east-1b --query 'Subnet.SubnetId' --output text)
  aws ec2 create-tags --resources $PRIVATE_SUBNET_2_ID --tags Key=Name,Value=fe-master-private-subnet-2
fi

echo "✅ サブネット確認完了: public=$PUBLIC_SUBNET_ID private1=$PRIVATE_SUBNET_ID private2=$PRIVATE_SUBNET_2_ID"

# 5. ルートテーブル設定
echo "🛤️  ルートテーブル設定中..."
ROUTE_TABLE_ID=$(aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC_ID" "Name=association.subnet-id,Values=$PUBLIC_SUBNET_ID" --query 'RouteTables[0].RouteTableId' --output text 2>/dev/null || true)
if [ -z "$ROUTE_TABLE_ID" ] || [ "$ROUTE_TABLE_ID" = "None" ]; then
  ROUTE_TABLE_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID --query 'RouteTable.RouteTableId' --output text)
  aws ec2 create-route --route-table-id $ROUTE_TABLE_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
  aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_ID --route-table-id $ROUTE_TABLE_ID
fi
echo "✅ ルートテーブル設定完了: $ROUTE_TABLE_ID"

# 6. セキュリティグループ作成
echo "🛡️  セキュリティグループ作成中..."
API_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=sg-api" "Name=vpc-id,Values=$VPC_ID" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || true)
if [ -z "$API_SG_ID" ] || [ "$API_SG_ID" = "None" ]; then
  API_SG_ID=$(aws ec2 create-security-group --group-name sg-api --description "Security group for API server" --vpc-id $VPC_ID --query 'GroupId' --output text)
  aws ec2 authorize-security-group-ingress --group-id $API_SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 || true
  aws ec2 authorize-security-group-ingress --group-id $API_SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0 || true
  aws ec2 authorize-security-group-ingress --group-id $API_SG_ID --protocol tcp --port 5000 --cidr 0.0.0.0/0 || true
  aws ec2 authorize-security-group-ingress --group-id $API_SG_ID --protocol tcp --port 22 --cidr $(curl -s https://checkip.amazonaws.com/)/32 || true
else
  echo "ℹ️  既存の API セキュリティグループを再利用: $API_SG_ID"
fi

DB_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=sg-db" "Name=vpc-id,Values=$VPC_ID" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || true)
if [ -z "$DB_SG_ID" ] || [ "$DB_SG_ID" = "None" ]; then
  DB_SG_ID=$(aws ec2 create-security-group --group-name sg-db --description "Security group for database" --vpc-id $VPC_ID --query 'GroupId' --output text)
  aws ec2 authorize-security-group-ingress --group-id $DB_SG_ID --protocol tcp --port 5432 --source-group $API_SG_ID || true
else
  echo "ℹ️  既存の DB セキュリティグループを再利用: $DB_SG_ID"
fi
echo "✅ セキュリティグループ設定完了"

# 7. RDS作成
echo "🗄️  RDS作成中..."
echo "🗄️ RDS 確認/作成..."
# RDS のパスワードは環境変数 RDS_MASTER_PASSWORD から取得する（無ければプロンプト）
if [ -z "$RDS_MASTER_PASSWORD" ]; then
  read -s -p "Enter RDS master password: " RDS_MASTER_PASSWORD
  echo
fi

aws rds describe-db-instances --db-instance-identifier fe-master-db &> /dev/null || EXISTS_RDS=0
if [ "$EXISTS_RDS" != "0" ]; then
  echo "ℹ️  既存の RDS インスタンスを作成します"
  aws rds create-db-subnet-group \
    --db-subnet-group-name fe-master-db-subnet-group \
    --db-subnet-group-description "Subnet group for FE Master database" \
    --subnet-ids $PRIVATE_SUBNET_ID $PRIVATE_SUBNET_2_ID || true

  aws rds create-db-instance \
    --db-instance-identifier fe-master-db \
    --db-instance-class db.t4g.micro \
    --engine postgres \
    --master-username postgres \
    --master-user-password "$RDS_MASTER_PASSWORD" \
    --allocated-storage 20 \
    --vpc-security-group-ids $DB_SG_ID \
    --db-subnet-group-name fe-master-db-subnet-group \
    --backup-retention-period 7 \
    --no-multi-az \
    --no-publicly-accessible || true

  echo "⏳ RDS作成完了待ち（約5-10分）..."
  aws rds wait db-instance-available --db-instance-identifier fe-master-db || true
  echo "✅ RDS作成完了"
else
  echo "ℹ️  既存の RDS インスタンスを再利用します"
fi

# 8. EC2インスタンス作成
echo "🖥️  EC2インスタンス作成中..."
DB_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier fe-master-db --query 'DBInstances[0].Endpoint.Address' --output text)

# user-data.shのRDSエンドポイントを更新
if [ -f user-data.sh ]; then
  sed -i "s/DB_ENDPOINT_PLACEHOLDER/$DB_ENDPOINT/g" user-data.sh || true
fi
if [ -n "$RDS_MASTER_PASSWORD" ]; then
  if [ -f user-data.sh ]; then
    sed -i "s/DB_PASSWORD_PLACEHOLDER/$RDS_MASTER_PASSWORD/g" user-data.sh || true
  fi
fi

# EC2 インスタンス起動（既存の同名インスタンスがあれば再利用）
EXISTING_INSTANCE=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=fe-master-api" "Name=instance-state-name,Values=running,stopped" --query 'Reservations[0].Instances[0].InstanceId' --output text 2>/dev/null || true)
if [ -n "$EXISTING_INSTANCE" ] && [ "$EXISTING_INSTANCE" != "None" ]; then
  echo "ℹ️  既存の EC2 インスタンスを再利用します: $EXISTING_INSTANCE"
  INSTANCE_ID=$EXISTING_INSTANCE
else
  INSTANCE_ID=$(aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t3.micro \
    --key-name fe-master-key \
    --security-group-ids $API_SG_ID \
    --subnet-id $PUBLIC_SUBNET_ID \
    --associate-public-ip-address \
    --user-data file://user-data.sh \
    --query 'Instances[0].InstanceId' --output text)

  aws ec2 create-tags --resources $INSTANCE_ID --tags Key=Name,Value=fe-master-api || true
fi

# インスタンス起動待ち
echo "⏳ インスタンス起動待ち..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID || true

EC2_PUBLIC_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo ""
echo "🎉 デプロイメント完了!"
echo "================================="
echo "EC2 Public IP: $EC2_PUBLIC_IP"
echo "アプリケーションURL: http://$EC2_PUBLIC_IP:5000"
echo "SSH接続: ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP"
echo ""
echo "📝 重要な情報:"
echo "- VPC ID: $VPC_ID"
echo "- API Security Group: $API_SG_ID" 
echo "- DB Security Group: $DB_SG_ID"
echo "- RDS Endpoint: $DB_ENDPOINT"
echo ""
echo "⏰ アプリケーションの初期化に数分かかる場合があります。"
echo "🔍 進行状況確認: ssh -i fe-master-key.pem ec2-user@$EC2_PUBLIC_IP 'sudo tail -f /var/log/cloud-init-output.log'"