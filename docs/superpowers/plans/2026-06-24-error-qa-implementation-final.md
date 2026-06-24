# 错题宝实现计划（最终版 — PostgreSQL + Redis）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.
> **版本**：3.0（技术栈确定：PostgreSQL 14 + Redis 7）

**Goal:** 实现错题宝的五个核心模块（认证、存储、拍照识别、复习推荐、文档导出），从而构建一个完整的智能学习系统。

**Architecture:** 
- 后端：FastAPI 单体应用，分层架构（routers → services → models）
- 数据库：**PostgreSQL 14** + SQLAlchemy 2.0+ ORM，支持级联删除和事务保护
- 缓存：**Redis 7**，key 包含 userId 实现数据隔离（规则 R6）
- AI 识别：Google Vision API 同步调用，包含 3 次自动重试和质量检查

**Tech Stack:** 
- Python 3.11 + FastAPI 0.100+ + SQLAlchemy 2.0+ + asyncpg
- **PostgreSQL 14** + **Redis 7** + Google Vision API
- pytest + pytest-asyncio + python-jose + bcrypt
- Docker Compose (本地开发环境)

---

## Global Constraints

- **Python 版本**：3.11（MUST）
- **JWT 过期时间**：1 小时
- **Vision API 超时**：5 秒
- **Redis 缓存** TTL：推荐计划 1 小时，其他资源 24 小时
- **缓存 key 格式**：`{entity}:{user_id}:{resource}` 规则 R6（必须包含 user_id）
- **重试策略**：Vision API 失败时重试 3 次（间隔 1s/2s/4s）
- **测试覆盖率**：后端 > 80%，关键模块（认证、推荐、识别）100%
- **数据隔离**：所有查询必须加 `WHERE user_id=current_user_id`（规则 R1）
- **错误响应格式**：`{ "status": "error", "code": "ERROR_CODE", "message": "...", "details": {...} }`

---

## 进度清单

### ✅ 已完成任务

| 任务 | 提交 | 说明 |
|------|------|------|
| Task 0.1 | ddb2a91 | 项目初始化、依赖（已调整为 PostgreSQL + Redis） |
| Task 1.1 | efafa2d | User 数据模型 |
| Task 1.1-UPDATE | ef9bc6d | PostgreSQL UUID 兼容性修复 |
| Task 1.2 | c361801 | JWT + 密码工具函数 |
| Task 1.3 | 12d89de | 认证路由（login、verify-password） |
| Task 2.1 | b8a866c | Question 和 ReviewPlan 模型 |
| Task 0.1-REVERT | f9e6c92 | **恢复 PostgreSQL + Redis 技术栈** |

---

## Phase 2: 题目存储模块（继续实现）

### Task 2.2: 题目存储 API 端点

**Files:**
- Create: `backend/src/schemas/question.py` — 请求/响应模型
- Create: `backend/src/routers/questions.py` — CRUD 路由
- Create: `backend/tests/unit/test_question_endpoints.py` — 单元测试

**Endpoints:**
- `POST /api/questions/create` — 创建题目
- `GET /api/questions` — 列表（分页）
- `GET /api/questions/{question_id}` — 详情
- `PUT /api/questions/{question_id}` — 更新（人工纠正）
- `DELETE /api/questions/{question_id}` — 删除

**关键要求：**
- 规则 R1：所有查询过滤 user_id
- 规则 R4：confidence < 0.7 标记 needs_review=true
- 规则 R5：创建/更新在事务中完成

**预期测试数**：8+ 单元测试（包括数据隔离验证）

---

## Phase 3: 拍照识别模块（三天主线）

### Task 3.1: Vision API 集成和质量检查

**Files:**
- Create: `backend/src/services/recognition_service.py`
- Create: `backend/src/schemas/recognition.py`
- Create: `backend/src/routers/recognition.py`

**功能：**
- 调用 Google Vision API 识别题目文本、公式、图像
- 规则 R2（格式校验）：confidence 缺失按 0 处理
- 规则 R4（质量检查）：三级验证
  1. confidence ∈ [0, 1]
  2. 文本长度 ∈ [5, 10000]
  3. 非垃圾数据（"[无法识别]"、重复符号等）
- 规则 R8（重试）：失败时 3 次自动重试（1s/2s/4s 间隔）

**Endpoint:**
- `POST /api/recognition/upload` — 上传图片，返回识别结果

---

### Task 3.2: 异步识别任务和状态跟踪

**Files:**
- Create: `backend/src/tasks/recognition_tasks.py` — Celery 任务
- Modify: `backend/src/routers/recognition.py` — 添加状态查询端点

**功能：**
- Celery 队列处理长耗时识别任务（不阻塞 HTTP）
- 规则 R8：失败时回调通知、重试、人工审核队列
- 前端轮询或 WebSocket 监听任务完成

**Endpoint:**
- `GET /api/recognition/task/{task_id}` — 查询任务状态

---

## Phase 4: 复习推荐模块（艾宾浩斯遗忘曲线）

### Task 4.1: 遗忘曲线算法实现

**Files:**
- Create: `backend/src/services/recommend_service.py`
- Create: `backend/src/schemas/recommendation.py`

**算法：**
- 复习间隔规划：1 → 3 → 7 → 15 → 30 天
- 优先级计分（三维度）：
  - 错误频率：同一题目错误次数越多优先级越高
  - 遗忘曲线：距离最后复习时间越长优先级越高
  - 难度：适配学生当前能力（5 档难度）
- 加权公式：`0.4 * 错误率 + 0.4 * 遗忘度 + 0.2 * 难度`

**规则 R6：Redis 缓存**
- key 格式：`recommend:{user_id}:plan` TTL 1 小时
- 编辑题目后清除用户缓存

**预期覆盖率**：100% 单元测试

---

### Task 4.2: 推荐查询和编辑端点

**Files:**
- Create: `backend/src/routers/recommendations.py`
- Create: `backend/tests/unit/test_recommend_service.py`

**Endpoints:**
- `GET /api/recommendations/plan` — 获取推荐计划（Redis 缓存）
- `POST /api/recommendations/mark-reviewed/{plan_id}` — 标记已复习
- `GET /api/recommendations/stats` — 学习统计（通过率、掌握度）

**规则 R5：事务保护**
- 计算推荐时在事务中完成
- 避免中途数据修改导致结果不一致

---

## Phase 5: 文档导出模块（快照机制）

### Task 5.1: 快照和导出服务

**Files:**
- Create: `backend/src/models/snapshot.py` — Snapshot 模型
- Create: `backend/src/services/export_service.py` — PDF 生成
- Modify: `backend/src/models/__init__.py` — 导出 Snapshot

**功能：**
- 规则 R9：导出时使用快照（冻结题目内容）
- Snapshot 存储导出时刻的完整数据（JSON）
- 基于快照生成 PDF，防止导出中途数据修改

**模型：**
```python
class Snapshot(Base):
    snapshot_id: UUID
    user_id: UUID
    question_ids: List[str]  # 选中题目 ID
    snapshot_data: JSON  # 冻结的完整数据
    format: str  # "pdf", "html", "docx"
    file_url: str
    created_at: datetime
    expires_at: datetime  # 30 天后删除
```

---

### Task 5.2: 导出路由和测试

**Files:**
- Create: `backend/src/routers/export.py`
- Create: `backend/tests/unit/test_export_service.py`

**Endpoints:**
- `POST /api/export/pdf` — 请求导出 PDF
- `GET /api/export/{snapshot_id}` — 下载导出文件
- `GET /api/export/history` — 导出历史

---

## 执行检查清单

### 代码质量检查

- [ ] Python 3.11 兼容性验证
- [ ] 类型检查：mypy 无错误
- [ ] 代码风格：black + flake8 通过
- [ ] 测试覆盖率 > 80%
- [ ] 所有 SECRET 使用 .env 隔离
- [ ] 规则 R1-R9 都有单元测试覆盖

### 规则遵循检查

- [ ] **R1**：所有查询都有 `user_id` 过滤
- [ ] **R2**：Bedrock 返回做了格式校验（无 confidence 按 0）
- [ ] **R3**：前端代码无 API 密钥暴露
- [ ] **R4**：Vision API 结果质量三级检查
- [ ] **R5**：推荐计算在事务中
- [ ] **R6**：Redis key 包含 user_id
- [ ] **R7**：推荐算法有单元测试（> 80% 覆盖）
- [ ] **R8**：异步任务失败有重试和通知
- [ ] **R9**：导出使用快照机制

### 集成测试

- [ ] 完整 auth flow（注册 → 登录 → 获取 token）
- [ ] 完整题目 flow（上传 → 识别 → 存储 → 推荐）
- [ ] 完整导出 flow（选题 → 快照 → 生成 PDF）
- [ ] 数据隔离验证（用户 A 无法访问用户 B 的数据）

---

## 部署和测试

### 本地开发启动

```bash
# 终端 1: 启动数据库和缓存
docker-compose up -d

# 终端 2: 启动后端
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 终端 3: 启动前端
cd frontend
npm install
npm run dev

# 终端 4: 后端 Celery 工作进程（异步任务）
cd backend
celery -A src.tasks worker --loglevel=info
```

### 测试命令

```bash
# 后端单元测试
cd backend
pytest tests/unit/ -v --cov=src --cov-report=term-missing

# 后端集成测试
pytest tests/integration/ -v

# 前端测试
cd frontend
npm run test

# 类型检查
npm run type-check
cd ../backend
mypy src/
```

---

**下一步：** 继续执行 Task 2.2（题目 API 端点）
