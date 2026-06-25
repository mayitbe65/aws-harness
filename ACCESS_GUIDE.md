# 错题宝 — 完整访问指南

**日期：** 2026-06-24  
**版本：** 1.0  
**状态：** 生产就绪  

---

## 📋 目录

1. [本地开发环境](#本地开发环境)
2. [AWS 部署环境](#aws-部署环境)
3. [登录凭证](#登录凭证)
4. [API 端点](#api-端点)
5. [常见问题](#常见问题)

---

## 🏠 本地开发环境

### 前置条件

```bash
# 检查版本
docker --version        # Docker 20.10+
docker-compose --version # Docker Compose 2.0+
node --version          # Node 18+
python3 --version       # Python 3.11+
npm --version           # npm 9+
```

### 快速启动（3 个终端）

#### 终端 1: 启动数据库和缓存
```bash
cd /workshop/aws-harness
docker-compose up -d

# 验证启动成功
docker-compose ps
# 输出：
# postgres  Up (5432)
# redis     Up (6379)
```

#### 终端 2: 启动后端 API
```bash
cd /workshop/aws-harness/backend

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动服务（开发模式，支持热重载）
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**期望输出：**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

#### 终端 3: 启动前端应用
```bash
cd /workshop/aws-harness/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

**期望输出：**
```
  VITE v5.0.0  ready in 125 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

### 本地访问地址

| 服务 | URL | 说明 |
|------|-----|------|
| **前端应用** | http://localhost:5173 | React 应用首页 |
| **后端 API** | http://localhost:8000 | FastAPI 服务 |
| **API 文档** | http://localhost:8000/docs | Swagger UI 文档 |
| **API 重定向** | http://localhost:8000/redoc | ReDoc 文档 |
| **PostgreSQL** | localhost:5432 | 数据库（pgAdmin 连接） |
| **Redis** | localhost:6379 | 缓存 Redis |

### 本地数据库访问

#### PostgreSQL
```bash
# 使用 psql 连接（需要安装 postgresql-client）
psql -h localhost -U postgres -d error_qa -p 5432

# 或使用 Docker 进入数据库
docker exec -it aws-harness-postgres-1 psql -U postgres -d error_qa
```

**PostgreSQL 凭证（开发）：**
```
Host: localhost
Port: 5432
Username: postgres
Password: password
Database: error_qa
```

#### Redis
```bash
# 使用 redis-cli 连接
redis-cli -h localhost -p 6379

# 或使用 Docker
docker exec -it aws-harness-redis-1 redis-cli

# 查看缓存键
KEYS recommend:*

# 清空缓存
FLUSHALL
```

**Redis 配置（开发）：**
```
Host: localhost
Port: 6379
Password: （无需密码）
Database: 0
```

---

## 💻 完整本地访问流程

### 第一次使用

1. **打开浏览器访问前端**
   ```
   http://localhost:5173
   ```

2. **自动重定向到登录页面**
   ```
   /login
   ```

3. **使用测试账号登录**
   ```
   Email: student@test.edu
   Password: Password123
   ```

4. **进入 Dashboard**
   - 显示题目列表（初始为空）
   - 看到"+ 拍照上传"按钮

### 测试用户

| 用户类型 | 邮箱 | 密码 | 角色 |
|---------|------|------|------|
| **学生** | student@test.edu | Password123 | student |
| **管理员** | admin@test.edu | AdminPass123 | admin |

**创建更多测试用户：**
```bash
# 使用后端 API
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@test.edu",
    "password": "Password123"
  }'
```

### 本地功能测试

#### 测试 1: 登录流程
```bash
# 1. 访问前端
http://localhost:5173

# 2. 输入凭证
# Email: student@test.edu
# Password: Password123

# 3. 期望：重定向到 Dashboard
# 4. 验证：URL 变为 http://localhost:5173/
```

#### 测试 2: 拍照上传和识别
```bash
# 1. 点击"+ 拍照上传"按钮
# 2. 选择或拍照一张包含数学题的图片
# 3. 点击"🤖 识别题目"
# 4. 期望：显示 Quality Indicator（高/中/低）
# 5. 验证：后端日志显示 Vision API 调用
```

**查看后端日志：**
```bash
# 在后端终端查看实时日志
# 应该看到：
# INFO:     POST /api/recognition/upload HTTP/1.1" 200
# INFO:     Vision API called for image recognition
```

#### 测试 3: 推荐复习
```bash
# 1. 保存几个题目
# 2. 点击"推荐"导航
# 3. 期望：显示推荐列表和学习统计
# 4. 点击题目卡片 → 打开 ReviewModal
# 5. 点击"做对"或"做错" → 更新复习计划
```

#### 测试 4: 文档导出
```bash
# 1. 点击"导出"导航
# 2. 选择题目（多选）
# 3. 选择格式（PDF/HTML）
# 4. 点击"生成导出"
# 5. 期望：显示进度条，完成后提供下载
```

---

## ☁️ AWS 部署环境

### 前提条件

```bash
# 安装 AWS CLI
aws --version  # AWS CLI 2.0+

# 配置 AWS 凭证
aws configure
# 输入：
# AWS Access Key ID: YOUR_KEY_ID
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region name: us-east-1 (或其他)
# Default output format: json
```

### 部署到 AWS

#### 步骤 1: 准备环境
```bash
cd /workshop/aws-harness/cdk

# 安装 CDK 依赖
npm install

# 配置环境变量
cp .env.example .env

# 编辑 .env 文件
nano .env
# 填入：
# AWS_ACCOUNT_ID=123456789012
# AWS_REGION=us-east-1
# ENVIRONMENT=dev
```

#### 步骤 2: 构建 Docker 镜像
```bash
# 构建并推送到 ECR
./scripts/build-docker.sh dev

# 期望输出：
# Successfully tagged 123456789012.dkr.ecr.us-east-1.amazonaws.com/error-qa-backend:latest
# Successfully tagged 123456789012.dkr.ecr.us-east-1.amazonaws.com/error-qa-frontend:latest
```

#### 步骤 3: 部署到 AWS
```bash
# 查看将要创建的资源（无需确认）
npm run cdk:diff:dev

# 部署到 AWS（需要确认）
npm run cdk:deploy:dev

# 期望输出：
# ✓ ErrorQaStackDev
# 
# Outputs:
# ErrorQaStackDev.BackendURL = http://api-dev-*.us-east-1.elb.amazonaws.com
# ErrorQaStackDev.FrontendURL = https://d-*.cloudfront.net
```

#### 步骤 4: 获取部署信息
```bash
# 查看输出（API 和前端 URL）
npm run cdk:describe:dev

# 或使用 AWS CLI
aws cloudformation describe-stacks \
  --stack-name ErrorQaStackDev \
  --region us-east-1 \
  --query 'Stacks[0].Outputs'
```

### AWS 部署地址

部署完成后，CDK 会输出以下 URL：

| 服务 | URL 格式 |
|------|----------|
| **前端应用** | https://d*.cloudfront.net |
| **后端 API** | http://api-dev-*.us-east-1.elb.amazonaws.com |
| **API 文档** | http://api-dev-*.us-east-1.elb.amazonaws.com/docs |

**实际 URL 示例：**
```
前端: https://d12345abcde.cloudfront.net
后端: http://api-dev-1234567890.us-east-1.elb.amazonaws.com
```

### AWS 环境访问

#### 访问前端
```bash
# 在浏览器中打开（可能需要几分钟部署完成）
https://d12345abcde.cloudfront.net

# 同样使用测试账号登录
Email: student@test.edu
Password: Password123
```

#### 访问后端 API
```bash
# API 文档
http://api-dev-1234567890.us-east-1.elb.amazonaws.com/docs

# API 调用示例
curl http://api-dev-1234567890.us-east-1.elb.amazonaws.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "student@test.edu", "password": "Password123"}'
```

#### 查看 AWS 资源

```bash
# 查看 RDS 数据库
aws rds describe-db-instances \
  --db-instance-identifier error-qa-db-dev \
  --region us-east-1

# 查看 ElastiCache Redis
aws elasticache describe-cache-clusters \
  --cache-cluster-id error-qa-cache-dev \
  --region us-east-1

# 查看 ECS 服务
aws ecs list-services \
  --cluster error-qa-cluster-dev \
  --region us-east-1

# 查看 S3 前端桶
aws s3 ls s3://error-qa-frontend-dev-bucket
```

---

## 🔐 登录凭证

### 本地开发

| 用户 | 邮箱 | 密码 | 说明 |
|------|------|------|------|
| 学生 | student@test.edu | Password123 | 普通用户 |
| 学生2 | student2@test.edu | Password123 | 测试用户隔离 |
| 管理员 | admin@test.edu | AdminPass123 | 管理权限 |

### AWS 环境

**初始凭证：** 与本地相同（由 CDK 创建）

**生产环境建议：**
```bash
# 使用 AWS Secrets Manager 管理凭证
aws secretsmanager create-secret \
  --name error-qa/admin-credentials \
  --secret-string '{
    "email": "admin@yourdomain.com",
    "password": "SecurePassword123!"
  }'
```

---

## 🔗 API 端点

### 认证
```
POST /api/auth/login
- 请求：{ email, password }
- 响应：{ access_token, user_id, role, expires_in }

POST /api/auth/verify-password
- 请求：{ password }
- 响应：{ valid: boolean }
```

### 题目管理
```
POST /api/questions/create
- 请求：{ photo_url, recognized_text, confidence, subject, difficulty, tags }
- 响应：Question 对象

GET /api/questions?page=1&page_size=20&subject=math
- 响应：{ items: Question[], total, page, page_size, has_more }

GET /api/questions/{question_id}
- 响应：Question 对象

PUT /api/questions/{question_id}
- 请求：{ recognized_text?, subject?, difficulty?, tags?, needs_review?, review_notes? }
- 响应：Question 对象

DELETE /api/questions/{question_id}
- 响应：{ status: "success", deleted_question_id }
```

### 拍照识别
```
POST /api/recognition/upload
- 请求：multipart/form-data (file)
- 响应：{ status, quality, result: { recognized_text, confidence }, message, needs_manual_review }
```

### 推荐复习
```
GET /api/recommendations/plan?limit=10
- 响应：{ items: ReviewItem[], total_questions, mastered_count, generated_at }

POST /api/recommendations/mark-reviewed/{plan_id}
- 请求：{ reviewed: boolean }
- 响应：{ plan_id, next_review_time, reviewed_count, message }

GET /api/recommendations/stats
- 响应：{ total_questions, mastered_count, mastery_rate, reviewed_today, average_errors_per_question }
```

### 文档导出
```
POST /api/export/pdf
- 请求：{ question_ids, format, group_by, include_answers }
- 响应：{ snapshot_id, status, message, estimated_time }

GET /api/export/{snapshot_id}
- 响应：{ snapshot_id, status, created_at, file_url, error_message }

GET /api/export/{snapshot_id}/download
- 响应：PDF/HTML 文件二进制

GET /api/export?page=1&page_size=10
- 响应：{ snapshots: SnapshotStatus[], total }
```

---

## 📊 前端路由

| 路由 | 说明 | 需要认证 |
|------|------|----------|
| `/login` | 登录页 | ❌ |
| `/` | Dashboard 题目列表 | ✅ |
| `/question/:id` | 题目详情编辑 | ✅ |
| `/upload` | 拍照上传 | ✅ |
| `/review` | 推荐复习 | ✅ |
| `/export` | 文档导出 | ✅ |

---

## 🔧 常见问题

### 本地开发常见问题

#### Q: 访问 http://localhost:5173 无响应
**A:** 检查前端服务是否运行
```bash
# 在前端终端查看输出
npm run dev

# 如果显示"Vite ... ready"，则服务正常运行
# 检查浏览器控制台和网络标签
```

#### Q: 后端 API 返回 404
**A:** 确认后端服务运行中
```bash
# 测试后端连接
curl http://localhost:8000/health

# 应该返回 200 OK
```

#### Q: 登录失败（401 Unauthorized）
**A:** 检查凭证和数据库
```bash
# 确认数据库迁移完成
alembic upgrade head

# 检查测试用户是否存在
docker exec aws-harness-postgres-1 \
  psql -U postgres -d error_qa -c "SELECT * FROM users;"
```

#### Q: Vision API 超时
**A:** 检查网络和 API 凭证
```bash
# 在 .env 中验证 GOOGLE_APPLICATION_CREDENTIALS
cat /path/to/credentials.json

# 测试 Vision API 连接
python3 -c "from google.cloud import vision; client = vision.ImageAnnotatorClient(); print('OK')"
```

### AWS 部署常见问题

#### Q: CDK 部署失败
**A:** 检查 AWS 凭证和权限
```bash
# 验证 AWS 凭证
aws sts get-caller-identity

# 应该输出：
# {
#   "UserId": "...",
#   "Account": "123456789012",
#   "Arn": "arn:aws:iam::..."
# }
```

#### Q: 部署后前端无法连接到后端
**A:** 检查安全组和 ALB
```bash
# 验证 ALB 状态
aws elbv2 describe-load-balancers \
  --names api-dev-* \
  --region us-east-1

# 检查目标组健康状态
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:... \
  --region us-east-1
```

#### Q: 高成本警告
**A:** 检查成本优化建议
```bash
# 查看部署配置
cat cdk/.env

# 根据 COST_ANALYSIS.md 调整 ENVIRONMENT 为 "dev"
```

---

## 📞 技术支持

### 获取帮助

1. **查看日志**
   ```bash
   # 前端开发模式日志
   # 在前端终端查看

   # 后端日志
   # 在后端终端查看或：
   tail -f /var/log/backend.log
   ```

2. **检查配置**
   - 本地：`/workshop/aws-harness/.env`
   - AWS：检查 SSM Parameter Store

3. **性能诊断**
   ```bash
   # PostgreSQL 性能
   psql -h localhost -d error_qa -c "EXPLAIN ANALYZE SELECT * FROM questions LIMIT 10;"

   # Redis 性能
   redis-cli INFO stats
   ```

---

## 🎯 快速参考

### 本地启动（一键）
```bash
cd /workshop/aws-harness

# 终端 1
docker-compose up -d

# 终端 2
cd backend && source venv/bin/activate && uvicorn src.main:app --reload --port 8000

# 终端 3
cd frontend && npm run dev

# 打开浏览器
# http://localhost:5173
```

### AWS 部署（一键）
```bash
cd /workshop/aws-harness/cdk

# 配置
npm install && cp .env.example .env
# 编辑 .env 文件

# 构建和部署
./scripts/build-docker.sh dev
npm run cdk:deploy:dev

# 获取 URL
npm run cdk:describe:dev
```

### 登录
```
Email: student@test.edu
Password: Password123
```

---

**版本：** 1.0  
**最后更新：** 2026-06-24  
**状态：** ✅ 生产就绪

🚀 **项目已完全就绪，可立即访问使用！**
