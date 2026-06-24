# 错题本核心模块设计文档

**日期**：2026-06-24  
**版本**：1.0  
**状态**：设计阶段  
**作者**：Claude Code  

## 目录

1. [概述](#概述)
2. [架构设计](#架构设计)
3. [数据模型](#数据模型)
4. [API 契约](#api-契约)
5. [认证与授权](#认证与授权)
6. [业务逻辑流程](#业务逻辑流程)
7. [错误处理](#错误处理)
8. [数据验证](#数据验证)
9. [测试策略](#测试策略)
10. [配置与部署](#配置与部署)
11. [规则检查清单](#规则检查清单)

---

## 概述

### 项目背景

**错题宝**是面向学校/班级的智能学习系统。通过四个核心功能帮助学生高效学习：

1. **① 拍照识别错题**（三天主线，最难、最有意思）
   - 学生用手机拍照上传错题
   - AI（Google Vision API）自动识别题目文本和图片
   - 同时识别题目结构、公式、图表等
   - 质量检查和人工审核机制

2. **② 存储**
   - 题目数字化存储，按科目/知识点/难度分类
   - 用户数据严格隔离（规则 R1）
   - 支持多维度查询和全文搜索

3. **③ 复习推荐**（按艾宾浩斯遗忘曲线）
   - 根据错误频率、遗忘时间、难度计算优先级
   - 使用艾宾浩斯遗忘规律推荐复习时间
   - 学生标记"已复习"后动态更新复习计划

4. **④ 打印**
   - 快照机制：导出时冻结题目当前状态
   - 按科目/知识点分节排版
   - 生成精美的 PDF 或 Word 文档供印刷

### 本设计覆盖的模块

1. **E. 用户认证与权限** — JWT 无状态认证、两层角色、敏感操作密码验证
2. **C. 题目数字化管理（存储②）** — 题目 CRUD、多维度查询、用户隔离
3. **A. AI 识别流程（拍照①）** — Vision API、质量检查、重试、人工审核
4. **B. 推荐计划算法（复习推荐③）** — 遗忘曲线、优先级、缓存
5. **D. 文档导出（打印④）** — 快照机制、PDF 生成、排版

### 实现顺序

底向上构建：**认证 (E) → 存储 (C) → 拍照识别 (A) → 复习推荐 (B) → 打印 (D)**

### 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 后端框架 | FastAPI + SQLAlchemy | 高性能、异步支持、ORM 完善 |
| 认证方式 | JWT 无状态 | 可扩展、前端友好、无需 Redis session |
| 识别调用 | 同步阻塞（2-5秒） | 快速原型优先，后期改异步 |
| Vision API | Google Vision API | 准确度高、支持中文、支持公式识别 |
| 识别后重试 | 3 次自动重试 | confidence < 0.5 时，间隔 1s/2s/4s |
| 识别质量分级 | 三级：高/中/低 | confidence ≥0.7/0.5-0.7/< 0.5 分别处理 |
| 推荐算法 | 遗忘曲线 + 错误频率 + 难度 | 均衡权重：0.4/0.4/0.2 |
| 遗忘曲线实现 | 艾宾浩斯公式 | 30 天周期，复习次数递减系数 |
| 导出快照 | 导出时冻结数据 | 防止题目在导出中被修改 |
| 部署架构 | 单体应用 | 初期简洁，后期再拆微服务 |
| 用户模型 | 二层角色（admin/student） | 学校/班级场景适配 |
| 注册方式 | 管理员手动创建 | 确保用户身份真实性 |

---

## 架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端应用 (React + TypeScript)             │
│  - 登录页面  - 题目上传  - 推荐列表  - 题目编辑  - 导出导航       │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS / JSON
┌────────────────────────▼────────────────────────────────────────┐
│                    API Gateway / CORS 中间件                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                     FastAPI 应用层                              │
├─────────────────────────────────────────────────────────────────┤
│  中间件栈：                                                       │
│  - ErrorHandlerMiddleware（全局错误处理）                        │
│  - AuthMiddleware（JWT 验证）                                    │
│  - CORSMiddleware                                                │
├─────────────────────────────────────────────────────────────────┤
│  路由层（routers/）：                                            │
│  - /api/auth — 登录、登出、密码验证                             │
│  - /api/questions — 题目 CRUD、查询、过滤                       │
│  - /api/recognition — 识别、重试、质量检查                      │
│  - /api/recommendations — 推荐计划、标记复习                    │
├─────────────────────────────────────────────────────────────────┤
│  业务逻辑层（services/）：                                       │
│  - auth_service — 密码哈希、JWT 签名                           │
│  - question_service — 题目业务逻辑、权限检查                    │
│  - recognition_service — Vision API 调用、质量检查、重试         │
│  - recommend_service — 优先级计算、排序、缓存                    │
├─────────────────────────────────────────────────────────────────┤
│  数据访问层（models/）：                                         │
│  - SQLAlchemy ORM 模型（User, Question, ReviewPlan）            │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐  ┌──────▼──────┐  ┌─────▼──────┐
│ PostgreSQL   │  │   Redis     │  │ Vision API │
│  数据库      │  │  缓存层     │  │ (Google)   │
└──────────────┘  └─────────────┘  └────────────┘
```

### 1.2 后端目录结构

```
backend/
├── src/
│   ├── main.py                    # FastAPI 应用入口
│   ├── config.py                  # 配置管理（环境变量加载）
│   ├── middleware/
│   │   ├── auth.py                # JWT 认证中间件
│   │   └── error_handler.py       # 全局错误处理中间件
│   ├── routers/
│   │   ├── auth.py                # 登录、登出、密码验证
│   │   ├── questions.py           # 题目 CRUD、查询、统计
│   │   ├── recognition.py         # 识别、重试
│   │   └── recommendations.py     # 推荐计划、标记复习
│   ├── services/
│   │   ├── auth_service.py        # 密码哈希、JWT 操作
│   │   ├── question_service.py    # 题目业务逻辑、隔离检查
│   │   ├── recognition_service.py # Vision API 调用、质量检查、重试
│   │   └── recommend_service.py   # 优先级计算、推荐排序
│   ├── models/
│   │   ├── user.py                # User 模型
│   │   ├── question.py            # Question 模型
│   │   └── review_plan.py         # ReviewPlan 模型
│   ├── schemas/
│   │   ├── auth.py                # 认证请求/响应 schema
│   │   ├── question.py            # 题目 schema
│   │   ├── recognition.py         # 识别 schema
│   │   └── recommendation.py      # 推荐 schema
│   ├── database/
│   │   ├── db.py                  # 数据库连接和会话管理
│   │   └── migrations/            # Alembic 迁移脚本
│   ├── utils/
│   │   ├── validators.py          # 输入验证工具
│   │   ├── security.py            # 密码、JWT 工具函数
│   │   └── constants.py           # 常量定义
│   └── services/
│       └── cache.py               # Redis 缓存工具
├── tests/
│   ├── unit/
│   │   ├── test_auth_service.py
│   │   ├── test_question_service.py
│   │   ├── test_recognition_service.py
│   │   └── test_recommend_service.py
│   ├── integration/
│   │   └── test_e2e_flow.py       # 端到端测试
│   └── conftest.py                # pytest 配置和 fixtures
├── requirements.txt               # Python 依赖
├── .env.example                   # 环境变量模板
├── pyproject.toml                 # Poetry 或 setuptools 配置
└── docker-compose.yml             # 本地开发 compose 文件
```

### 1.3 核心依赖

- **FastAPI 0.100+** — Web 框架
- **SQLAlchemy 2.0+** — ORM
- **Pydantic 2.0+** — 数据验证
- **python-jose** — JWT 签名和验证
- **bcrypt** — 密码哈希
- **google-cloud-vision** — Vision API 客户端
- **redis** — Redis 客户端
- **pytest + pytest-asyncio** — 异步测试
- **httpx** — 异步 HTTP 客户端

---

## 数据模型

### 2.1 User 表

```sql
CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'student') NOT NULL DEFAULT 'student',
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_email (email),
    INDEX idx_role (role)
);
```

**字段说明**：
- `user_id`：UUID，唯一标识
- `email`：唯一约束，用于登录
- `password_hash`：bcrypt 哈希，永不存储明文
- `role`：枚举类型，admin 或 student
- `name`：用户显示名称
- `created_at`、`updated_at`：时间戳

### 2.2 Question 表

```sql
CREATE TABLE questions (
    question_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    image_url VARCHAR(512) NOT NULL,
    recognized_text TEXT NOT NULL,
    subject VARCHAR(50),
    difficulty INT DEFAULT 3,
    knowledge_point VARCHAR(255),
    correct_answer TEXT,
    error_reason VARCHAR(255),
    needs_review BOOLEAN DEFAULT FALSE,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_subject (subject),
    INDEX idx_knowledge_point (knowledge_point),
    INDEX idx_needs_review (needs_review),
    INDEX idx_created_at (created_at),
    CHECK (difficulty BETWEEN 1 AND 5),
    CHECK (confidence BETWEEN 0 AND 1)
);
```

**字段说明**：
- `question_id`：UUID，唯一标识
- `user_id`：外键，关联 users 表（数据隔离，规则 R1）
- `image_url`：原始照片 URL
- `recognized_text`：Vision API 识别的题目文本
- `subject`：科目（数学、英语、物理等）
- `difficulty`：难度 1-5
- `knowledge_point`：知识点（如"二次函数"）
- `correct_answer`：标准答案
- `error_reason`：错误原因（如"计算错误"、"理解偏差"、"粗心"）
- `needs_review`：是否需人工审核（低质量识别为 true）
- `confidence`：Vision API 识别置信度 [0, 1]
- **级联删除**：用户删除时，所有相关题目自动删除

### 2.3 Snapshot 表（导出快照）

```sql
CREATE TABLE snapshots (
    snapshot_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    question_ids JSON NOT NULL,                   -- 快照包含的题目 ID 列表
    format VARCHAR(10) NOT NULL,                  -- 导出格式：pdf 或 word
    organize_by VARCHAR(50),                      -- 组织方式：subject 或 knowledge_point
    snapshot_data JSON NOT NULL,                  -- 冻结的题目数据和元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                         -- 快照过期时间（30 天后）
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_expires_at (expires_at)
);
```

**字段说明**：
- `snapshot_id`：UUID，唯一标识
- `user_id`：外键
- `question_ids`：JSON 数组，快照中包含的题目 ID
- `snapshot_data`：JSON，包含题目内容、答案、元数据（冻结在此刻）
- `expires_at`：30 天后自动过期，可由定时任务删除

---

### 2.4 ExportDocument 表（导出文档）

```sql
CREATE TABLE export_documents (
    document_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    snapshot_id VARCHAR(36) NOT NULL,
    format VARCHAR(10) NOT NULL,                  -- pdf 或 word
    file_url VARCHAR(512) NOT NULL,               -- S3 或 CDN 链接
    file_size_bytes INT,                          -- 文件大小
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                         -- 文档过期时间（60 天后）
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_generated_at (generated_at)
);
```

**字段说明**：
- `document_id`：UUID，唯一标识
- `file_url`：指向 S3/CDN 的下载链接
- `expires_at`：60 天后自动删除，链接失效

---

### 2.5 ReviewPlan 表

```sql
CREATE TABLE review_plans (
    plan_id VARCHAR(36) PRIMARY KEY,
    question_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    priority FLOAT DEFAULT 0.5,
    next_review_time TIMESTAMP,
    error_count INT DEFAULT 0,
    last_error_time TIMESTAMP,
    reviewed_count INT DEFAULT 0,
    last_reviewed_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_next_review_time (next_review_time),
    INDEX idx_priority (priority),
    CHECK (priority BETWEEN 0 AND 1)
);
```

**字段说明**：
- `plan_id`：UUID，唯一标识
- `question_id`、`user_id`：外键
- `priority`：推荐优先级 [0, 1]，越高越紧迫
- `next_review_time`：下次推荐复习的时间
- `error_count`：该题目出错次数
- `last_error_time`：最后一次出错的时间
- `reviewed_count`：复习次数
- `last_reviewed_time`：最后复习的时间
- **注**：仅 `needs_review=false` 的题目才创建 ReviewPlan

### 2.4 Pydantic Schema（API 层）

#### Auth Schema
```python
# schemas/auth.py
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    expires_in: int

class PasswordVerifyRequest(BaseModel):
    password: str
```

#### Question Schema
```python
# schemas/question.py
class QuestionCreate(BaseModel):
    image_url: str
    recognized_text: str
    subject: Optional[str] = None
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    knowledge_point: Optional[str] = None

class QuestionUpdate(BaseModel):
    recognized_text: Optional[str] = None
    subject: Optional[str] = None
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    knowledge_point: Optional[str] = None
    correct_answer: Optional[str] = None
    error_reason: Optional[str] = None
    needs_review: Optional[bool] = None

class QuestionResponse(BaseModel):
    question_id: str
    user_id: str
    image_url: str
    recognized_text: str
    subject: Optional[str]
    difficulty: Optional[int]
    knowledge_point: Optional[str]
    correct_answer: Optional[str]
    error_reason: Optional[str]
    needs_review: bool
    confidence: float
    created_at: datetime
    updated_at: datetime
```

#### Recognition Schema
```python
# schemas/recognition.py
class RecognitionRequest(BaseModel):
    image_url: str
    subject: Optional[str] = None

class RecognitionResponse(BaseModel):
    question_id: str
    recognized_text: str
    confidence: float
    needs_review: bool
    reason: Optional[str]  # 如果 needs_review=true，说明原因
```

#### Recommendation Schema
```python
# schemas/recommendation.py
class ReviewPlanResponse(BaseModel):
    plan_id: str
    question: QuestionResponse
    priority: float
    next_review_time: datetime
    error_count: int
    reviewed_count: int

class MarkReviewedRequest(BaseModel):
    reviewed: bool
    notes: Optional[str] = None

class RecommendationStatsResponse(BaseModel):
    total_questions: int
    reviewed_count: int
    review_rate: float
    avg_priority: float
```

#### Export Schema
```python
# schemas/export.py
class SnapshotCreateRequest(BaseModel):
    question_ids: List[str]
    format: Literal["pdf", "word"]
    organize_by: Literal["subject", "knowledge_point"]

class SnapshotQuestionData(BaseModel):
    question_id: str
    image_url: str
    recognized_text: str
    subject: Optional[str]
    difficulty: Optional[int]
    knowledge_point: Optional[str]
    correct_answer: Optional[str]
    snapshot_at: datetime

class SnapshotMetadata(BaseModel):
    total_questions: int
    by_subject: Dict[str, int]
    by_difficulty: Dict[int, int]

class SnapshotResponse(BaseModel):
    snapshot_id: str
    user_id: str
    question_ids: List[str]
    format: str
    organize_by: str
    snapshot_data: Dict  # {questions: [...], metadata: {...}}
    created_at: datetime
    expires_at: datetime

class GenerateDocumentRequest(BaseModel):
    snapshot_id: str

class ExportDocumentResponse(BaseModel):
    document_id: str
    snapshot_id: str
    format: str
    file_url: str
    file_size_bytes: Optional[int]
    generated_at: datetime
    expires_at: datetime

class ExportDocumentListResponse(BaseModel):
    items: List[ExportDocumentResponse]
    total: int
```

---

## API 契约

### 3.1 认证模块（/api/auth）

#### POST /api/auth/login
登录获取 JWT token

**请求**：
```json
{
  "email": "student@school.edu",
  "password": "Password123"
}
```

**响应** (200 OK)：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "user-uuid-123",
  "role": "student",
  "expires_in": 3600
}
```

**错误**：
- 400：邮箱或密码格式错误
- 401：邮箱不存在或密码错误
- 429：尝试次数过多

---

#### POST /api/auth/logout
登出（前端删除 token，后端无需处理）

**请求**：Bearer token

**响应** (200 OK)：
```json
{
  "status": "success"
}
```

---

#### POST /api/auth/verify-password
验证密码（用于敏感操作确认）

**请求**：
```json
{
  "password": "Password123"
}
```

**响应** (200 OK)：
```json
{
  "valid": true
}
```

**错误**：
- 401：密码错误或 token 无效

---

### 3.2 题目管理模块（/api/questions）

#### POST /api/questions
创建题目

**请求**：
```json
{
  "image_url": "https://...",
  "recognized_text": "2x² + 3x - 5 = 0",
  "subject": "数学",
  "difficulty": 3,
  "knowledge_point": "二次方程"
}
```

**响应** (201 Created)：
```json
{
  "question_id": "question-uuid-123",
  "user_id": "user-uuid-123",
  "image_url": "https://...",
  "recognized_text": "2x² + 3x - 5 = 0",
  "subject": "数学",
  "difficulty": 3,
  "knowledge_point": "二次方程",
  "correct_answer": null,
  "error_reason": null,
  "needs_review": false,
  "confidence": 1.0,
  "created_at": "2026-06-24T10:00:00Z",
  "updated_at": "2026-06-24T10:00:00Z"
}
```

---

#### GET /api/questions
获取题目列表（多维度查询）

**查询参数**：
```
?subject=数学&knowledge_point=二次函数&difficulty=3&page=1&limit=20
```

**响应** (200 OK)：
```json
{
  "items": [
    { /* QuestionResponse */ },
    { /* QuestionResponse */ }
  ],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

**权限**：学生只能查看自己的题目（规则 R1）

---

#### GET /api/questions/{question_id}
获取单个题目详情

**响应** (200 OK)：
```json
{ /* QuestionResponse */ }
```

**错误**：
- 404：题目不存在或无权限

---

#### PUT /api/questions/{question_id}
编辑题目（如纠正低质量识别）

**请求**：
```json
{
  "recognized_text": "修正后的题目文本",
  "subject": "数学"
}
```

**响应** (200 OK)：
```json
{ /* 更新后的 QuestionResponse */ }
```

**特殊处理**：
- 若修改 `recognized_text`，自动设置 `needs_review=false`
- 清除该用户的推荐缓存（Redis）

---

#### DELETE /api/questions/{question_id}
删除题目（敏感操作，需密码验证）

**请求**：
```
Header: X-Confirm-Password: <已验证的密码标记>
```
或先调用 `/api/auth/verify-password` 获得确认

**响应** (204 No Content)：无

**权限**：需要密码验证

---

#### GET /api/questions/stats
获取题目统计（每位学生只看自己的）

**响应** (200 OK)：
```json
{
  "total": 42,
  "by_subject": {
    "数学": 15,
    "英语": 12,
    "物理": 10
  },
  "by_difficulty": {
    "1": 5,
    "2": 8,
    "3": 15,
    "4": 10,
    "5": 4
  },
  "needs_review_count": 3
}
```

---

### 3.3 识别模块（/api/recognition）

#### POST /api/recognition/recognize
上传并识别题目（同步调用，阻塞 2-5 秒）

**请求**：
```json
{
  "image_url": "https://...",
  "subject": "数学"
}
```

**响应** (200 OK)：
```json
{
  "question_id": "question-uuid-123",
  "recognized_text": "2x² + 3x - 5 = 0，求 x",
  "confidence": 0.85,
  "needs_review": false,
  "reason": null
}
```

**流程**：
1. 验证 image_url 有效性
2. 调用 Vision API 识别（同步）
3. 验证返回格式（规则 R2）：缺 confidence 按 0 处理
4. 质量检查（规则 R4）：
   - confidence ≥ 0.7：`needs_review=false`
   - 0.5 ≤ confidence < 0.7：`needs_review=true`，reason="低可信度"
   - confidence < 0.5：重试 3 次（间隔 1s、2s、4s）
5. 垃圾检查：空字符串、纯符号、"[无法识别]" → `needs_review=true`
6. 在事务中创建 Question 和 ReviewPlan（规则 R5）

**错误**：
- 400：image_url 无效
- 500：Vision API 超时或异常
- 429：超配额

**注**：即使识别失败，仍创建 Question 记录，标记 `needs_review=true`

---

#### POST /api/recognition/retry/{question_id}
重新识别（用户手动重新上传或重新识别）

**请求**：
```json
{
  "image_url": "https://... (新的或相同的)"
}
```

**响应** (200 OK)：
```json
{
  "question_id": "question-uuid-123",
  "recognized_text": "新的识别结果",
  "confidence": 0.92,
  "needs_review": false,
  "reason": null
}
```

---

### 3.4 推荐模块（/api/recommendations）

#### GET /api/recommendations/plan
获取推荐复习计划

**查询参数**：
```
?limit=10&include_low_confidence=false
```

**响应** (200 OK)：
```json
{
  "items": [
    {
      "plan_id": "plan-uuid-1",
      "question": { /* QuestionResponse */ },
      "priority": 0.92,
      "next_review_time": "2026-06-25T10:00:00Z",
      "error_count": 5,
      "reviewed_count": 2
    },
    { /* 更多项 */ }
  ],
  "generated_at": "2026-06-24T10:30:00Z"
}
```

**缓存**：结果缓存 1 小时，Redis key 格式 `recommendation:user:{user_id}:plan`（规则 R6）

**算法**：
```
priority = 0.4 × error_freq 
         + 0.4 × spaced_repetition_score 
         + 0.2 × difficulty_factor
```

---

#### POST /api/recommendations/mark-reviewed/{plan_id}
标记题目已复习

**请求**：
```json
{
  "reviewed": true,
  "notes": "已掌握"
}
```

**响应** (200 OK)：
```json
{
  "status": "success",
  "next_review_time": "2026-07-01T10:00:00Z"
}
```

**处理**：
- 更新 ReviewPlan 的 `reviewed_count`、`last_reviewed_time`
- 重新计算 `next_review_time`（基于遗忘曲线）
- 清除用户的推荐缓存

---

#### GET /api/recommendations/stats
获取推荐统计

**响应** (200 OK)：
```json
{
  "total_questions": 42,
  "reviewed_count": 18,
  "review_rate": 0.43,
  "avg_priority": 0.62
}
```

---

### 3.5 文档导出模块（/api/export）

#### POST /api/export/snapshot
创建导出快照（冻结当前题目状态）

**请求**：
```json
{
  "question_ids": ["q-uuid-1", "q-uuid-2", "q-uuid-3"],
  "format": "pdf",
  "organize_by": "subject"
}
```

**响应** (201 Created)：
```json
{
  "snapshot_id": "snapshot-uuid-123",
  "user_id": "user-uuid-123",
  "question_ids": ["q-uuid-1", "q-uuid-2", "q-uuid-3"],
  "format": "pdf",
  "organize_by": "subject",
  "snapshot_data": {
    "questions": [
      {
        "question_id": "q-uuid-1",
        "image_url": "https://...",
        "recognized_text": "2x² + 3x - 5 = 0",
        "subject": "数学",
        "difficulty": 3,
        "knowledge_point": "二次方程",
        "correct_answer": "x = 1 或 x = -2.5",
        "snapshot_at": "2026-06-24T10:30:00Z"
      }
    ],
    "metadata": {
      "total_questions": 3,
      "by_subject": {"数学": 3},
      "by_difficulty": {"3": 3}
    }
  },
  "created_at": "2026-06-24T10:30:00Z",
  "expires_at": "2026-07-24T10:30:00Z"
}
```

**说明**：
- 快照冻结题目当前状态（snapshot_data），保留 30 天
- format: "pdf" 或 "word"
- organize_by: "subject"（按科目分节）或 "knowledge_point"（按知识点分节）
- 即使之后题目被编辑/删除，快照数据不变

---

#### POST /api/export/generate
生成文档（基于快照）

**请求**：
```json
{
  "snapshot_id": "snapshot-uuid-123"
}
```

**响应** (200 OK)：
```json
{
  "document_id": "doc-uuid-456",
  "snapshot_id": "snapshot-uuid-123",
  "format": "pdf",
  "file_url": "https://cdn.example.com/exports/doc-uuid-456.pdf",
  "file_size_bytes": 1234567,
  "generated_at": "2026-06-24T10:35:00Z",
  "expires_at": "2026-08-24T10:35:00Z"
}
```

**处理流程**：
1. 查询快照数据
2. 生成排版（Jinja2 模板 → HTML）
3. 转换为 PDF（ReportLab）或 Word（python-docx）
4. 上传到 S3 或 CDN
5. 返回下载链接（有效期 60 天）

---

#### GET /api/export/documents
获取用户导出历史

**响应** (200 OK)：
```json
{
  "items": [
    {
      "document_id": "doc-uuid-456",
      "format": "pdf",
      "file_url": "https://cdn.example.com/...",
      "generated_at": "2026-06-24T10:35:00Z",
      "expires_at": "2026-08-24T10:35:00Z"
    }
  ],
  "total": 12
}
```

---

#### GET /api/export/documents/{document_id}
获取单个导出记录

**响应** (200 OK)：
```json
{
  "document_id": "doc-uuid-456",
  "snapshot_id": "snapshot-uuid-123",
  "format": "pdf",
  "file_url": "https://cdn.example.com/exports/doc-uuid-456.pdf",
  "generated_at": "2026-06-24T10:35:00Z"
}
```

---

#### DELETE /api/export/documents/{document_id}
删除导出文档（可选，若要清理存储空间）

**响应** (204 No Content)

---

## 认证与授权

### 4.1 JWT Token 结构

**Payload**：
```json
{
  "sub": "user-uuid-123",
  "email": "student@school.edu",
  "role": "student",
  "iat": 1719216000,
  "exp": 1719219600
}
```

- `sub`：用户 ID（subject）
- `email`：用户邮箱
- `role`：角色，admin 或 student
- `iat`：签发时间（Unix timestamp）
- `exp`：过期时间（1 小时后）

**签名**：HS256（HMAC with SHA-256），密钥存储在 `.env` 的 `JWT_SECRET_KEY`

---

### 4.2 认证流程

```
1. 用户输入邮箱和密码 → 调用 POST /api/auth/login
2. 后端验证：
   a. 检查邮箱是否存在
   b. 用 bcrypt 比对密码
   c. 如果正确，生成 JWT token
   d. 返回 token 和用户信息
3. 前端存储 token 到 localStorage
4. 后续请求在 Authorization header 中添加 "Bearer <token>"
5. 服务器验证 token：
   a. 解析签名
   b. 检查过期时间
   c. 提取 user_id 和 role
   d. 继续业务处理
6. 登出时，前端删除 localStorage 中的 token（后端无需处理，纯无状态）
```

---

### 4.3 权限检查矩阵

| 操作 | 学生 | 管理员 | 检查逻辑 |
|------|------|--------|--------|
| 登录 | ✅ | ✅ | 邮箱+密码 |
| 查看自己的题目 | ✅ | ❌ | user_id 匹配 |
| 编辑自己的题目 | ✅ | ❌ | user_id 匹配 + 密码验证 |
| 删除自己的题目 | ✅ | ❌ | user_id 匹配 + 密码验证 |
| 查看全部题目 | ❌ | ✅ | role == "admin" |
| 查看自己的推荐 | ✅ | ❌ | user_id 匹配 |
| 查看全部学生数据 | ❌ | ✅ | role == "admin"（后期功能） |

---

### 4.4 敏感操作验证流程

敏感操作包括：删除题目、导出文档、修改账户。

**流程**：
```
1. 前端检测敏感操作（如点击删除按钮）
2. 弹出对话框，要求用户输入密码
3. 前端调用 POST /api/auth/verify-password { password }
4. 后端验证：
   a. 从 JWT 获取 user_id
   b. 查询数据库中的 password_hash
   c. 用 bcrypt 比对输入密码 vs 哈希
   d. 返回 { valid: true } 或 { valid: false }
5. 如果验证成功，前端继续调用敏感操作的 API
6. 如果验证失败，提示用户"密码错误，请重试"
```

**注**：不要在请求中传递明文密码，使用 HTTPS 加密传输。后端也不存储明文，仅比对哈希。

---

## 业务逻辑流程

### 5.1 学生上传并识别题目

```
输入：image_url, subject (可选)
输出：Question 记录 + ReviewPlan

步骤：

1. 校验 JWT token
   ├─ 解析 token，获取 user_id
   └─ 如果 token 无效，返回 401

2. 校验 image_url
   ├─ 检查 URL 格式有效性
   ├─ 检查大小 < 5MB
   └─ 如果无效，返回 400

3. 调用 Vision API 识别（同步阻塞）
   ├─ 超时时间 5 秒
   ├─ 如果超时或异常，记录日志，返回 500
   └─ 获得 {recognized_text, confidence, ...}

4. 验证 Vision API 返回格式（规则 R2）
   ├─ 检查 recognized_text 存在
   ├─ 检查 confidence 存在，否则按 0 处理
   ├─ 验证 confidence ∈ [0, 1]
   └─ 如果格式错误，返回 500

5. 质量检查（规则 R4）
   ├─ IF confidence < 0.5:
   │   ├─ 重试 1 次（间隔 1s）
   │   ├─ 如果仍 < 0.5，重试 2 次（间隔 2s、4s）
   │   └─ 如果 3 次都失败，设置 needs_review=true
   ├─ ELSE IF 0.5 ≤ confidence < 0.7:
   │   └─ 设置 needs_review=true，reason="低可信度"
   └─ ELSE (confidence ≥ 0.7):
       └─ 设置 needs_review=false

6. 垃圾检查
   ├─ IF recognized_text 为空 OR 长度 < 5 OR > 10000:
   │   └─ 设置 needs_review=true
   ├─ ELSE IF 纯符号或"[无法识别]":
   │   └─ 设置 needs_review=true
   └─ 继续

7. 在事务中创建记录（规则 R5）
   ├─ async with db.begin():
   │   ├─ INSERT INTO questions(...)
   │   ├─ IF needs_review=false:
   │   │   └─ INSERT INTO review_plans(...)
   │   └─ COMMIT 事务
   └─ 如果事务失败，ROLLBACK

8. 返回 RecognitionResponse
   ├─ question_id, recognized_text, confidence
   ├─ needs_review, reason (如有)
   └─ HTTP 200 OK
```

---

### 5.2 计算和返回推荐计划

```
输入：user_id, limit=10
输出：ReviewPlanResponse[] 按 priority 倒序

步骤：

1. 校验 JWT token
   └─ 获取 user_id

2. 检查 Redis 缓存
   ├─ key = "recommendation:user:{user_id}:plan"
   ├─ IF 缓存存在且未过期:
   │   └─ 直接返回缓存数据，HTTP 200 OK
   └─ 继续

3. 计算推荐（需在事务中，规则 R5）
   ├─ async with db.begin():
   │   ├─ 查询所有 needs_review=false 的题目
   │   │   SELECT * FROM questions 
   │   │   WHERE user_id=? AND needs_review=false
   │   │
   │   ├─ 对每条题目计算优先级
   │   │   error_freq = error_count / (max_error_count + 1)
   │   │   forgetting = spaced_repetition_score(...)
   │   │   difficulty_factor = difficulty / 5.0
   │   │   priority = 0.4 × error_freq 
   │   │            + 0.4 × forgetting 
   │   │            + 0.2 × difficulty_factor
   │   │
   │   ├─ 按 priority 倒序排序
   │   │
   │   ├─ 取前 limit 条
   │   │
   │   ├─ 查询关联的 ReviewPlan 记录
   │   │   SELECT * FROM review_plans WHERE question_id IN (...)
   │   │
   │   ├─ 构建 ReviewPlanResponse[] 对象
   │   │
   │   └─ COMMIT 事务

4. 存入 Redis 缓存（规则 R6）
   ├─ key = "recommendation:user:{user_id}:plan"
   ├─ value = JSON serialize(ReviewPlanResponse[])
   ├─ TTL = 3600 秒（1 小时）
   └─ 推送到 Redis

5. 返回响应
   ├─ items: ReviewPlanResponse[]
   ├─ generated_at: 当前时间戳
   └─ HTTP 200 OK
```

**spaced_repetition_score 计算**：
```python
def calculate_spaced_repetition_score(
    last_error_time: datetime,
    last_reviewed_time: Optional[datetime],
    reviewed_count: int
) -> float:
    now = datetime.utcnow()
    
    # 若从未复习过，基于上次出错时间（遗忘曲线）
    if last_reviewed_time is None:
        days_since_error = (now - last_error_time).days
        # 天数越多，遗忘越严重，分数越高
        return min(1.0, days_since_error / 30.0)  # 30 天满分 1.0
    
    # 若复习过，基于复习时间和复习次数
    days_since_review = (now - last_reviewed_time).days
    forgetting_factor = min(1.0, days_since_review / 7.0)  # 7 天满分
    # 复习次数越多，遗忘的紧迫性越低
    repetition_factor = max(0.1, 1.0 - reviewed_count * 0.1)  # 最低 0.1
    
    return forgetting_factor * repetition_factor
```

---

### 5.3 学生编辑题目文本

```
输入：question_id, QuestionUpdate { recognized_text, ... }
输出：QuestionResponse

步骤：

1. 校验 JWT token，获取 user_id

2. 查询题目，验证权限
   ├─ SELECT * FROM questions WHERE question_id=?
   ├─ IF 题目不存在: 返回 404
   ├─ IF user_id 不匹配: 返回 403（无权限）
   └─ 继续

3. IF recognized_text 被修改:
   ├─ 校验长度 5-10000
   ├─ 更新 questions.recognized_text
   ├─ 自动设置 needs_review=false（用户已确认）
   └─ 更新其他字段（subject、difficulty 等）

4. 更新时间戳
   └─ updated_at = now()

5. 清除缓存
   └─ DELETE Redis key "recommendation:user:{user_id}:plan"

6. 返回更新后的 QuestionResponse

7. HTTP 200 OK
```

---

### 5.4 标记题目已复习

```
输入：plan_id, reviewed=true/false
输出：{ status: "success" }

步骤：

1. 校验 JWT token，获取 user_id

2. 查询 ReviewPlan，验证权限
   ├─ SELECT * FROM review_plans WHERE plan_id=?
   ├─ IF 不存在: 返回 404
   ├─ IF user_id 不匹配: 返回 403
   └─ 继续

3. 在事务中更新（规则 R5）
   ├─ async with db.begin():
   │   ├─ IF reviewed=true:
   │   │   ├─ reviewed_count += 1
   │   │   ├─ last_reviewed_time = now()
   │   │   ├─ 重新计算 next_review_time (遗忘曲线)
   │   │   │   next_review_time = now() + timedelta(
   │   │   │       days=calculate_next_review_days(...)
   │   │   │   )
   │   │   └─ 重新计算 priority
   │   │
   │   ├─ ELSE IF reviewed=false:
   │   │   ├─ error_count += 1
   │   │   ├─ last_error_time = now()
   │   │   └─ 提高 priority（用户再次出错）
   │   │
   │   └─ UPDATE review_plans SET ...

4. 清除缓存
   └─ DELETE Redis key "recommendation:user:{user_id}:plan"

5. 返回 { status: "success" }

6. HTTP 200 OK
```

---

### 5.5 创建导出快照（快照机制，规则 R9）

```
输入：question_ids[], format, organize_by
输出：Snapshot 记录

步骤：

1. 校验 JWT token，获取 user_id

2. 验证 question_ids
   ├─ IF 为空: 返回 400
   ├─ 查询所有题目
   │   SELECT * FROM questions 
   │   WHERE question_id IN (question_ids) AND user_id=?
   ├─ IF 任何题目不属于当前用户: 返回 403
   └─ 继续

3. 创建快照数据（冻结当前状态）
   ├─ 对每条题目创建 snapshot_data
   │   {
   │     "question_id": "...",
   │     "image_url": "...",
   │     "recognized_text": "...",
   │     "subject": "...",
   │     "difficulty": 3,
   │     "knowledge_point": "...",
   │     "correct_answer": "...",
   │     "snapshot_at": now()
   │   }
   ├─ 计算元数据
   │   {
   │     "total_questions": N,
   │     "by_subject": {科目: count, ...},
   │     "by_difficulty": {难度: count, ...}
   │   }
   └─ 合并为 snapshot_data JSON

4. 在数据库中创建快照（规则 R9：快照机制）
   ├─ INSERT INTO snapshots(
   │     snapshot_id, user_id, question_ids, format,
   │     organize_by, snapshot_data,
   │     created_at, expires_at
   │   )
   ├─ expires_at = now() + timedelta(days=30)
   └─ 返回快照信息

5. 返回 SnapshotResponse

6. HTTP 201 Created
```

**快照的关键作用**：
- 冻结题目当前内容，防止后续修改影响导出
- 即使用户删除了题目，快照数据仍保留
- 导出文档基于快照数据，而非实时查询题目表
- 30 天后自动过期，可由定时任务删除

---

### 5.6 生成导出文档（基于快照）

```
输入：snapshot_id
输出：PDF 或 Word 文件链接

步骤：

1. 校验 JWT token，获取 user_id

2. 查询快照（规则 R9）
   ├─ SELECT * FROM snapshots WHERE snapshot_id=?
   ├─ IF 不存在或过期: 返回 404
   ├─ IF user_id 不匹配: 返回 403
   └─ 获取 snapshot_data

3. 根据 organize_by 重新组织题目
   ├─ IF organize_by="subject":
   │   └─ 按科目分组排序
   ├─ ELSE IF organize_by="knowledge_point":
   │   └─ 按知识点分组排序
   └─ 其他默认按创建时间

4. 生成 HTML 排版（使用 Jinja2 模板）
   ├─ 标题、封面、目录
   ├─ 每组题目为一节
   │   ├─ 节标题（科目或知识点）
   │   ├─ 题目卡片：
   │   │   ├─ 题目图片（image_url）
   │   │   ├─ 识别文本
   │   │   ├─ 答案和解析
   │   │   ├─ 难度、知识点标签
   │   │   └─ 页码
   │   └─ 统计数据
   ├─ 页脚、水印（用户名、生成时间）
   └─ HTML 字符串

5. 转换为目标格式
   ├─ IF format="pdf":
   │   ├─ 使用 ReportLab 或 Weasyprint
   │   ├─ HTML → PDF
   │   └─ 设置纸张大小、页边距、字体
   ├─ ELSE IF format="word":
   │   ├─ 使用 python-docx
   │   ├─ HTML → Word (.docx)
   │   └─ 保持格式兼容性
   └─ 生成文件到临时目录

6. 上传文件到 S3/CDN
   ├─ 生成唯一文件名：{document_id}.{format}
   ├─ 上传到 S3，设置 Content-Type
   ├─ 获得公开 URL（有效期 60 天）
   └─ 记录文件大小

7. 在数据库中创建文档记录
   ├─ INSERT INTO export_documents(
   │     document_id, user_id, snapshot_id,
   │     format, file_url, file_size_bytes,
   │     generated_at, expires_at
   │   )
   ├─ expires_at = now() + timedelta(days=60)
   └─ COMMIT

8. 返回 ExportDocumentResponse

9. HTTP 200 OK
```

**文档生成的特点**：
- 基于快照数据，完全隔离（规则 R9）
- 即使快照被删除，已生成的文档不受影响
- 文件存储在 CDN，不占用数据库空间
- 支持离线下载和打印

---

### 5.7 艾宾浩斯遗忘曲线实现

**核心概念**：
根据遗忘规律，制定复习时间表。间隔越长，复习的紧迫性越高。

**复习间隔规划**（基于复习次数）：
```
第 1 次复习：1 天后
第 2 次复习：3 天后
第 3 次复习：7 天后
第 4 次复习：15 天后
第 5 次复习及以后：30 天后
```

**实现算法**：
```python
def calculate_next_review_days(reviewed_count: int) -> int:
    """根据复习次数返回下次复习的天数"""
    review_schedule = {
        0: 1,   # 首次出错后 1 天
        1: 3,   # 第 1 次复习后 3 天
        2: 7,   # 第 2 次复习后 7 天
        3: 15,  # 第 3 次复习后 15 天
        4: 30,  # 第 4 次复习后 30 天
    }
    return review_schedule.get(reviewed_count, 30)  # 超过 5 次都是 30 天

def calculate_spaced_repetition_score(
    last_error_time: datetime,
    last_reviewed_time: Optional[datetime],
    reviewed_count: int
) -> float:
    """计算复习的紧迫性分数 [0, 1]"""
    now = datetime.utcnow()
    
    # 若从未复习过，基于上次出错时间
    if last_reviewed_time is None:
        days_since_error = (now - last_error_time).days
        # 天数越多，遗忘越严重，分数越高
        # 30 天满分 1.0
        return min(1.0, days_since_error / 30.0)
    
    # 若复习过，基于复习时间和复习次数
    days_since_review = (now - last_reviewed_time).days
    next_review_days = calculate_next_review_days(reviewed_count)
    
    # 接近下次复习时间时，分数越高
    # 超过下次复习时间，分数最高 1.0
    forgetting_factor = min(1.0, days_since_review / next_review_days)
    
    # 复习次数越多，曲线越平缓
    # 每复习一次，基础分降 10%，最低 0.1（长期不忘）
    repetition_damping = max(0.1, 1.0 - reviewed_count * 0.1)
    
    return forgetting_factor * repetition_damping
```

**示例**：
```
题目 A：上周五出错，未复习过
  last_error_time = 上周五
  last_reviewed_time = None
  reviewed_count = 0
  days_since_error = 6
  spaced_repetition_score = min(1.0, 6/30) = 0.2

题目 B：上周一出错，复习过 2 次，最后复习在 3 天前
  last_error_time = 上周一
  last_reviewed_time = 3 天前
  reviewed_count = 2
  days_since_review = 3
  next_review_days = 7（第 2 次复习后应该 7 天）
  forgetting_factor = min(1.0, 3/7) = 0.43
  repetition_damping = max(0.1, 1.0 - 2*0.1) = 0.8
  spaced_repetition_score = 0.43 * 0.8 = 0.34

题目 C：两周前出错，今天正好是计划复习日（7 天后）
  last_reviewed_time = 7 天前
  reviewed_count = 1
  days_since_review = 7
  next_review_days = 7
  forgetting_factor = min(1.0, 7/7) = 1.0
  repetition_damping = max(0.1, 1.0 - 1*0.1) = 0.9
  spaced_repetition_score = 1.0 * 0.9 = 0.9 ← 最紧迫
```

---

## 推荐优先级总公式（完整）

```
priority = 0.4 × error_freq + 0.4 × spaced_repetition_score + 0.2 × difficulty_factor

其中：
  error_freq = error_count / (max_error_count + 1)
  spaced_repetition_score = calculate_spaced_repetition_score(...)
  difficulty_factor = difficulty / 5.0
  max_error_count = 该学生所有题目中的最大错误数
```

**优先级范围** [0, 1]，越接近 1.0 越需要立即复习。

---

## 错误处理

### 6.1 全局错误响应格式

所有错误均返回标准格式：

```json
{
  "status": "error",
  "code": "ERROR_CODE",
  "message": "人类可读的错误信息",
  "details": { /* 可选调试信息 */ }
}
```

### 6.2 错误码和 HTTP 状态码映射

| HTTP 状态 | 错误码 | 场景 | 处理 |
|----------|--------|------|------|
| 400 | INVALID_INPUT | 邮箱格式错、密码为空、image_url 无效 | 返回具体字段错误 |
| 401 | UNAUTHORIZED | JWT 无效、过期、缺失 | 前端清除 token，跳转登录 |
| 401 | AUTH_FAILED | 登录密码错误、验证密码失败 | 提示重试 |
| 403 | FORBIDDEN | 学生查看他人题目、无管理员权限 | 返回"无权限" |
| 404 | NOT_FOUND | 题目不存在、plan_id 不存在 | 返回具体资源类型 |
| 429 | TOO_MANY_REQUESTS | 登录超过 5 次/分钟、Vision API 超配额 | 提示稍后再试 |
| 500 | INTERNAL_ERROR | Vision API 超时、数据库异常 | 记录日志，提示用户"服务异常" |
| 503 | SERVICE_UNAVAILABLE | 依赖服务不可用 | 提示用户稍后再试 |

---

### 6.3 特定模块的错误处理

**认证模块**
- 登录失败：不区分邮箱不存在还是密码错误，统一返回 401，防用户枚举
- 密码验证失败：返回 401
- Token 过期：返回 401，前端自动清除并跳转登录

**识别模块**
- Vision API 超时：返回 500，记录日志
- Image URL 无效：返回 400
- 3 次重试仍失败：继续创建题目，标记 `needs_review=true`，返回 200（不算错误）

**题目管理模块**
- 无权限：返回 403
- 密码验证失败：返回 401

**推荐模块**
- 计算失败：返回 500，记录日志

---

## 数据验证

### 7.1 输入验证

```python
# utils/validators.py

class EmailValidator:
    """验证邮箱格式，长度 5-255"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
class PasswordValidator:
    """密码需 8+ 字符，包含大小写字母和数字"""
    min_length = 8
    require_uppercase = True
    require_lowercase = True
    require_digit = True

class ImageUrlValidator:
    """URL 格式有效，域名在允许列表"""
    allowed_domains = ["images.example.com", "cdn.example.com", ...]

class TextValidator:
    """题目文本长度 5-10000"""
    min_length = 5
    max_length = 10000

class ConfidenceValidator:
    """置信度浮点数，范围 [0, 1]"""
    min_value = 0.0
    max_value = 1.0

class DifficultyValidator:
    """难度整数，范围 [1, 5]"""
    min_value = 1
    max_value = 5
```

### 7.2 数据库约束

```sql
-- 唯一性
ALTER TABLE users ADD UNIQUE(email);

-- 非空约束
ALTER TABLE users MODIFY user_id NOT NULL;
ALTER TABLE questions MODIFY user_id NOT NULL;
ALTER TABLE questions MODIFY recognized_text NOT NULL;

-- 范围约束（CHECK）
ALTER TABLE questions ADD CHECK(difficulty BETWEEN 1 AND 5);
ALTER TABLE questions ADD CHECK(confidence BETWEEN 0 AND 1);
ALTER TABLE review_plans ADD CHECK(priority BETWEEN 0 AND 1);

-- 外键约束（级联删除）
ALTER TABLE questions 
  ADD FOREIGN KEY(user_id) 
  REFERENCES users(user_id) 
  ON DELETE CASCADE;

ALTER TABLE review_plans 
  ADD FOREIGN KEY(user_id) 
  REFERENCES users(user_id) 
  ON DELETE CASCADE;

ALTER TABLE review_plans 
  ADD FOREIGN KEY(question_id) 
  REFERENCES questions(question_id) 
  ON DELETE CASCADE;

-- 索引优化查询
CREATE INDEX idx_questions_user_id ON questions(user_id);
CREATE INDEX idx_questions_subject ON questions(subject);
CREATE INDEX idx_review_plans_user_id ON review_plans(user_id);
CREATE INDEX idx_review_plans_priority ON review_plans(priority);
```

---

## 测试策略

### 8.1 单元测试

**auth_service**
```
✅ test_password_hashing：bcrypt 哈希和验证
✅ test_jwt_generation：生成和解析 JWT
✅ test_jwt_expiry：过期 token 被拒绝
✅ test_role_extraction：从 JWT 提取 role
```

**question_service**
```
✅ test_create_question：创建题目记录
✅ test_list_questions_user_isolation：学生只看自己的题目（规则 R1）
✅ test_edit_question：编辑题目文本
✅ test_delete_question：删除权限检查
✅ test_query_by_multiple_filters：多维度查询（科目、知识点、难度）
✅ test_pagination：分页功能
```

**recognition_service**
```
✅ test_vision_api_success：成功识别（confidence ≥ 0.7）
✅ test_confidence_validation：缺 confidence 字段按 0 处理（规则 R2）
✅ test_confidence_range_0_5_to_0_7：标记 needs_review
✅ test_low_confidence_retry：< 0.5 时重试 3 次
✅ test_garbage_data_detection：检测垃圾数据
✅ test_vision_api_timeout：API 超时处理
✅ test_transaction_rollback：识别失败时事务回滚
```

**recommend_service**
```
✅ test_priority_calculation：优先级计算公式
✅ test_spaced_repetition_score：遗忘曲线计算
✅ test_recommend_plan_sorting：按优先级倒序排序
✅ test_mark_reviewed_updates_next_review_time：复习后重新计算时间
✅ test_recommend_caching：结果缓存（规则 R6）
✅ test_cache_invalidation：编辑题目后清除缓存
```

### 8.2 集成测试

```
✅ test_e2e_student_flow：
   1. 学生登录 → 2. 上传识别 → 3. 编辑题目 
   → 4. 查看推荐 → 5. 标记已复习

✅ test_e2e_admin_flow：
   1. 管理员登录 → 2. 查看学生数据汇总

✅ test_concurrent_recognition：
   并发上传多张图片，验证一致性

✅ test_user_isolation：
   学生 A 题目对学生 B 不可见（规则 R1）

✅ test_transaction_consistency：
   推荐计算中途删除题目，最终一致（规则 R5）

✅ test_password_verification_sensitive_ops：
   删除题目前必须验证密码
```

### 8.3 Mock 策略

**Vision API Mock**
```python
# 所有测试中 mock Vision API（不真实调用，浪费配额）
# 使用 unittest.mock 或 pytest-mock

mock_vision_response = {
    "recognized_text": "2x² + 3x - 5 = 0",
    "confidence": 0.85
}

@patch('services.recognition_service.vision_api.analyze_image')
def test_recognize_high_confidence(mock_api):
    mock_api.return_value = mock_vision_response
    # ... 测试逻辑
```

**Redis Mock**
```python
# 单元测试中 mock Redis，不使用真实 Redis
# 集成测试可使用真实 Redis 或 Docker

@patch('services.recommend_service.redis_client.get')
def test_cache_hit(mock_redis):
    mock_redis.return_value = json.dumps([...])
    # ... 测试逻辑
```

---

## 配置与部署

### 9.1 环境变量（.env.example）

```ini
# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/error_qa_db

# JWT
JWT_SECRET_KEY=your-secret-key-minimum-32-characters
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=1

# Vision API
VISION_API_KEY=your-google-vision-api-key
VISION_API_TIMEOUT_SECONDS=5

# Redis（缓存）
REDIS_URL=redis://localhost:6379/0

# 应用配置
APP_ENV=development
APP_DEBUG=true
APP_LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]

# 日志
LOG_FORMAT=json
LOG_FILE=/var/log/error-qa/app.log
```

### 9.2 本地开发启动

```bash
# 1. 启动依赖服务（数据库、Redis）
docker-compose up -d

# 2. 后端
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 Vision API 密钥

# 3. 数据库迁移
alembic upgrade head

# 4. 启动后端服务器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 5. 前端（新终端）
cd frontend
npm install
npm run dev
```

### 9.3 运行测试

```bash
# 单元测试
pytest tests/unit/ -v

# 集成测试
pytest tests/integration/ -v

# 所有测试 + 覆盖率
pytest tests/ --cov=src --cov-report=html

# 特定模块
pytest tests/unit/test_recommend_service.py -v
```

---

## 规则检查清单

基于 `rules/severity-guide.md` 和 `rules/personal.md`，本设计涵盖的规则：

- ✅ **R1**：userId 数据隔离 — API 层每个查询都加 `WHERE user_id=current`
- ✅ **R2**：Bedrock 返回格式校验 — 缺 confidence 按 0 处理，验证范围 [0, 1]
- ✅ **R3**：API 代理 — Vision API 调用通过后端，前端不暴露密钥
- ✅ **R4**：Vision 质量检查 — 低质量标记 needs_review，垃圾数据过滤
- ✅ **R5**：推荐计算事务保护 — `async with db.begin()` 保证一致性
- ✅ **R6**：缓存 key 隔离 — Redis key 格式 `recommendation:user:{user_id}:plan`
- ✅ **R7**：推荐算法测试 — 单元测试覆盖 > 80%
- ✅ **R8**：异步失败处理 — Vision API 失败重试 3 次 + 标记审核
- ✅ **R9**：导出快照机制 — 导出时冻结题目当前状态，30 天保留期

---

## 附录

### A.1 相关文件

- `CLAUDE.md` — 项目总体指导
- `rules/severity-guide.md` — 规则等级定义
- `rules/personal.md` — 10+ 条项目特定规则

### A.2 后续工作

**第一阶段**（三天主线 — 拍照识别错题）：
- ① 用户认证模块实现（E）
- ② 题目存储模块实现（C）
- ③ AI 拍照识别模块实现（A）— 最难、最有意思
  - Vision API 集成
  - 三级质量检查
  - 3 次自动重试机制
  - 人工审核流程
- 本阶段后端测试覆盖 > 80%

**第二阶段**（复习推荐系统）：
- ④ 推荐计划模块实现（B）
  - 艾宾浩斯遗忘曲线实现
  - 优先级计算和排序
  - Redis 缓存管理

**第三阶段**（文档导出系统）：
- ⑤ 导出模块实现（D）
  - 快照机制（规则 R9）
  - Jinja2 模板排版
  - PDF/Word 生成
  - S3/CDN 上传

**优化工作**：
- 异步队列改造 — 将同步 Vision API 改为 Celery + Redis 异步处理
- 管理员端功能 — 学生数据汇总、班级管理
- 全文搜索优化 — 集成 Elasticsearch 或数据库全文索引
- 前端 UI/UX 优化 — 响应式设计、离线支持

---

**文档版本控制**：
- 2026-06-24 v1.0 — 初版设计完成

**建议反馈**：提交到项目 PR，或在 `docs/` 目录下创建讨论文件。
