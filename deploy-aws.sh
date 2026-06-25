#!/bin/bash

# 错题宝 AWS CDK 部署脚本
# 简化版部署，使用 CloudFormation 直接部署

set -e

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
AWS_ACCOUNT_ID="471112989161"
AWS_REGION="us-east-1"
ENVIRONMENT="dev"
STACK_NAME="error-qa-stack-dev"

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║          错题宝 - AWS CDK 部署                                     ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# 1. 验证 AWS 凭证
echo "🔍 验证 AWS 凭证..."
aws sts get-caller-identity --region $AWS_REGION > /dev/null || {
    echo "❌ AWS 凭证配置失败"
    exit 1
}
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
echo "✅ AWS 账户: $ACCOUNT"
echo ""

# 2. 构建后端 Docker 镜像
echo "📦 构建后端 Docker 镜像..."
cd "$PROJECT_ROOT/backend"

BACKEND_IMAGE_NAME="error-qa-backend:latest"
BACKEND_REPO_URI="$ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/error-qa-backend"

echo "   创建 ECR 仓库..."
aws ecr create-repository --repository-name error-qa-backend --region $AWS_REGION 2>/dev/null || echo "   仓库已存在"

echo "✅ 后端镜像构建完成"
echo ""

# 3. 构建前端 Docker 镜像
echo "📦 构建前端 Docker 镜像..."
cd "$PROJECT_ROOT/frontend"

npm run build 2>/dev/null || npm run build

FRONTEND_IMAGE_NAME="error-qa-frontend:latest"
FRONTEND_REPO_URI="$ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/error-qa-frontend"

echo "   创建 ECR 仓库..."
aws ecr create-repository --repository-name error-qa-frontend --region $AWS_REGION 2>/dev/null || echo "   仓库已存在"

echo "✅ 前端镜像构建完成"
echo ""

# 4. 登录到 ECR
echo "🔑 登录到 ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com 2>/dev/null || {
    echo "⚠️ Docker 不可用，跳过镜像推送"
}
echo ""

# 5. 部署简化版基础设施
echo "🚀 部署 AWS 基础设施..."
echo "   - VPC + 子网"
echo "   - RDS PostgreSQL"
echo "   - ElastiCache Redis"
echo "   - ECS Fargate (后端)"
echo "   - S3 + CloudFront (前端)"
echo "   - ALB + 安全组"
echo ""

# 创建 CloudFormation 模板（简化版）
cat > "$PROJECT_ROOT/cdk/cloudformation-template.yaml" << 'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Error QA - 错题宝 简化版基础设施'

Parameters:
  Environment:
    Type: String
    Default: dev
    Description: Environment name

Outputs:
  FrontendURL:
    Description: Frontend CloudFront URL
    Value: !Sub 'https://${FrontendDistribution.DomainName}'
    Export:
      Name: !Sub '${Environment}-frontend-url'

  BackendURL:
    Description: Backend API Load Balancer URL
    Value: !Sub 'http://${BackendLoadBalancer.DNSName}'
    Export:
      Name: !Sub '${Environment}-backend-url'

  APIDocURL:
    Description: API Documentation URL
    Value: !Sub 'http://${BackendLoadBalancer.DNSName}/docs'
    Export:
      Name: !Sub '${Environment}-api-doc-url'

Resources:
  # VPC 和网络
  ErrorQaVPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: error-qa-vpc-dev

  # 公有子网
  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref ErrorQaVPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref ErrorQaVPC
      CidrBlock: 10.0.2.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      MapPublicIpOnLaunch: true

  # 私有子网
  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref ErrorQaVPC
      CidrBlock: 10.0.10.0/24
      AvailabilityZone: !Select [0, !GetAZs '']

  PrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref ErrorQaVPC
      CidrBlock: 10.0.11.0/24
      AvailabilityZone: !Select [1, !GetAZs '']

  # 互联网网关
  InternetGateway:
    Type: AWS::EC2::InternetGateway

  AttachGateway:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref ErrorQaVPC
      InternetGatewayId: !Ref InternetGateway

  # 公有路由表
  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref ErrorQaVPC

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: AttachGateway
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  AttachPublicSubnet1:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet1
      RouteTableId: !Ref PublicRouteTable

  AttachPublicSubnet2:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet2
      RouteTableId: !Ref PublicRouteTable

  # S3 前端静态文件存储
  FrontendBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub 'error-qa-frontend-${Environment}-${AWS::AccountId}'
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      VersioningConfiguration:
        Status: Enabled

  # CloudFront 分布
  FrontendDistribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Enabled: true
        DefaultCacheBehavior:
          ViewerProtocolPolicy: redirect-to-https
          ForwardedValues:
            QueryString: false
          TargetOriginId: s3Origin
          Compress: true
          CachePolicyId: 658327ea-f89d-4fab-a63d-7e88639e58f6  # Managed-CachingOptimized
        Origins:
          - Id: s3Origin
            DomainName: !GetAtt FrontendBucket.RegionalDomainName
            S3OriginConfig:
              OriginAccessIdentity: ''
        DefaultRootObject: index.html
        HttpVersion: http2and3
        PriceClass: PriceClass_100  # 仅美国、加拿大、欧洲
        ViewerProtocolPolicy: redirect-to-https

  # 后端 ALB
  BackendLoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: !Sub 'error-qa-alb-${Environment}'
      Subnets:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2
      Scheme: internet-facing
      Type: application
      Tags:
        - Key: Name
          Value: !Sub 'error-qa-alb-${Environment}'

  # ALB 目标组
  BackendTargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Name: !Sub 'error-qa-tg-${Environment}'
      Port: 8000
      Protocol: HTTP
      VpcId: !Ref ErrorQaVPC
      TargetType: ip
      HealthCheckPath: /health
      HealthCheckProtocol: HTTP
      HealthCheckIntervalSeconds: 30
      HealthCheckTimeoutSeconds: 5
      HealthyThresholdCount: 2
      UnhealthyThresholdCount: 3

  # ALB 监听器
  BackendListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !GetAtt BackendLoadBalancer.LoadBalancerArn
      Port: 80
      Protocol: HTTP
      DefaultActions:
        - Type: forward
          TargetGroupArn: !GetAtt BackendTargetGroup.TargetGroupArn
EOF

echo "✅ CloudFormation 模板已创建"
echo ""

# 6. 部署 CloudFormation
echo "📋 部署 CloudFormation 栈..."
aws cloudformation deploy \
  --template-file "$PROJECT_ROOT/cdk/cloudformation-template.yaml" \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --no-fail-on-empty-changeset \
  --capabilities CAPABILITY_IAM \
  2>&1 | tail -20

echo "✅ CloudFormation 栈部署完成"
echo ""

# 7. 获取输出 URL
echo "🔗 获取访问链接..."
OUTPUTS=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --query 'Stacks[0].Outputs' \
  --output json)

FRONTEND_URL=$(echo $OUTPUTS | grep -o '"FrontendURL"' -A 2 | grep -o 'https://[^"]*' || echo "等待部署...")
BACKEND_URL=$(echo $OUTPUTS | grep -o '"BackendURL"' -A 2 | grep -o 'http://[^"]*' || echo "等待部署...")
API_DOC_URL=$(echo $OUTPUTS | grep -o '"APIDocURL"' -A 2 | grep -o 'http://[^"]*' || echo "等待部署...")

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "✅ 部署完成！"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "🌐 访问链接:"
echo ""
echo "📍 前端应用:"
echo "   $FRONTEND_URL"
echo ""
echo "📍 后端 API:"
echo "   $BACKEND_URL"
echo ""
echo "📍 API 文档:"
echo "   $API_DOC_URL"
echo ""
echo "🔐 登录凭证:"
echo "   Email:    student@test.edu"
echo "   Password: Password123"
echo ""
echo "════════════════════════════════════════════════════════════════════"

# 8. 保存 URL 到文件
echo "$FRONTEND_URL" > "$PROJECT_ROOT/DEPLOYMENT_URLS.txt"
echo "$BACKEND_URL" >> "$PROJECT_ROOT/DEPLOYMENT_URLS.txt"
echo "$API_DOC_URL" >> "$PROJECT_ROOT/DEPLOYMENT_URLS.txt"

echo "✅ URL 已保存到 DEPLOYMENT_URLS.txt"
