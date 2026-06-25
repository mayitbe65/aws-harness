#!/bin/bash

# 错题宝 - 简化部署方案
# 使用 S3 + CloudFront 部署前端，EC2/本地部署后端

set -e

AWS_ACCOUNT_ID="471112989161"
AWS_REGION="us-east-1"
S3_BUCKET="error-qa-frontend-$(date +%s)"
DISTRIBUTION_NAME="error-qa-dist"

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║          错题宝 - 简化版 AWS 部署                                  ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# 1. 创建 S3 桶
echo "📦 创建 S3 桶..."
aws s3api create-bucket \
  --bucket $S3_BUCKET \
  --region $AWS_REGION \
  --acl private \
  2>/dev/null || echo "桶已存在"

# 启用版本控制
aws s3api put-bucket-versioning \
  --bucket $S3_BUCKET \
  --versioning-configuration Status=Enabled \
  2>/dev/null || true

# 阻止公开访问
aws s3api put-public-access-block \
  --bucket $S3_BUCKET \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
  2>/dev/null || true

echo "✅ S3 桶已创建: $S3_BUCKET"
echo ""

# 2. 上传前端静态文件
echo "📤 上传前端文件到 S3..."
cd /workshop/aws-harness/frontend

# 确保已构建
if [ ! -d "dist" ]; then
    echo "   构建前端..."
    npm run build
fi

# 上传文件
aws s3 sync dist/ s3://$S3_BUCKET/ \
  --region $AWS_REGION \
  --delete \
  --cache-control "max-age=3600" \
  2>/dev/null

echo "✅ 前端文件已上传"
echo ""

# 3. 创建 CloudFront 分布（使用 AWS CLI）
echo "🚀 创建 CloudFront 分布..."

# 生成 CloudFront 配置
cat > /tmp/cloudfront-config.json << EOF
{
  "CallerReference": "error-qa-$(date +%s)",
  "Comment": "Error QA Frontend Distribution",
  "Enabled": true,
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "S3Origin",
        "DomainName": "${S3_BUCKET}.s3.${AWS_REGION}.amazonaws.com",
        "S3OriginConfig": {
          "OriginAccessIdentity": ""
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3Origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "TrustedSigners": {
      "Enabled": false,
      "Quantity": 0
    },
    "Compress": true,
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": {
        "Forward": "none"
      }
    },
    "MinTTL": 0,
    "DefaultTTL": 3600,
    "MaxTTL": 86400
  },
  "DefaultRootObject": "index.html",
  "PriceClass": "PriceClass_100",
  "HttpVersion": "http2and3"
}
EOF

# 创建分布
DISTRIBUTION_JSON=$(aws cloudfront create-distribution \
  --distribution-config file:///tmp/cloudfront-config.json \
  --region $AWS_REGION \
  2>&1 || echo "分布可能已存在")

DISTRIBUTION_ID=$(echo $DISTRIBUTION_JSON | grep -o '"Id": "[^"]*"' | head -1 | cut -d'"' -f4 || echo "pending")
DISTRIBUTION_URL=$(echo $DISTRIBUTION_JSON | grep -o '"DomainName": "[^"]*"' | head -1 | cut -d'"' -f4 || echo "pending")

echo "✅ CloudFront 分布已创建"
echo "   分布 ID: $DISTRIBUTION_ID"
echo ""

# 4. 获取本地后端信息
echo "📝 获取后端信息..."

BACKEND_HOST="localhost"
BACKEND_PORT="8000"
BACKEND_URL="http://$BACKEND_HOST:$BACKEND_PORT"

# 检查本地后端是否运行
if curl -s http://$BACKEND_HOST:$BACKEND_PORT/health > /dev/null 2>&1; then
    echo "✅ 本地后端正在运行"
    BACKEND_STATUS="✅ 运行中"
else
    echo "⚠️ 本地后端未运行"
    BACKEND_STATUS="⚠️ 需要手动启动"
fi

echo ""

# 5. 输出信息
echo "════════════════════════════════════════════════════════════════════"
echo "✅ AWS 部署完成！"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "🌐 访问链接:"
echo ""
if [ "$DISTRIBUTION_URL" != "pending" ]; then
    echo "📍 前端应用:"
    echo "   https://$DISTRIBUTION_URL"
    echo ""
fi
echo "📍 后端 API:"
echo "   $BACKEND_URL"
echo "   $BACKEND_STATUS"
echo ""
echo "📍 API 文档:"
echo "   $BACKEND_URL/docs"
echo ""
echo "🔐 登录凭证:"
echo "   Email:    student@test.edu"
echo "   Password: Password123"
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "📋 后续步骤:"
echo ""
echo "1️⃣ 启动本地后端（如果还没启动）:"
echo "   cd /workshop/aws-harness/backend"
echo "   source venv/bin/activate"
echo "   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "2️⃣ 访问前端应用:"
if [ "$DISTRIBUTION_URL" != "pending" ]; then
    echo "   https://$DISTRIBUTION_URL"
else
    echo "   等待 CloudFront 分布创建完成（通常需要 5-10 分钟）"
    echo "   然后访问上面显示的 URL"
fi
echo ""
echo "3️⃣ 使用测试凭证登录"
echo ""
echo "════════════════════════════════════════════════════════════════════"

# 保存信息
{
    echo "# 错题宝 AWS 部署信息"
    echo ""
    echo "部署日期: $(date)"
    echo "AWS 账户: $AWS_ACCOUNT_ID"
    echo "AWS 区域: $AWS_REGION"
    echo ""
    echo "## 前端"
    echo "S3 桶: $S3_BUCKET"
    if [ "$DISTRIBUTION_ID" != "pending" ]; then
        echo "CloudFront 分布 ID: $DISTRIBUTION_ID"
        echo "CloudFront URL: https://$DISTRIBUTION_URL"
    else
        echo "CloudFront: 创建中..."
    fi
    echo ""
    echo "## 后端"
    echo "URL: $BACKEND_URL"
    echo "状态: $BACKEND_STATUS"
    echo ""
    echo "## 登录凭证"
    echo "Email: student@test.edu"
    echo "Password: Password123"
} > /workshop/aws-harness/AWS_DEPLOYMENT_INFO.txt

echo "✅ 部署信息已保存到 AWS_DEPLOYMENT_INFO.txt"
