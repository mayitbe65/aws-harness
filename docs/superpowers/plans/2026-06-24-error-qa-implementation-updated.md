# 错题宝实现计划（更新版 — SQLite + 内存缓存）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.
> **版本**：2.0（技术栈调整：PostgreSQL → SQLite, Redis → 内存缓存）

**Goal:** 实现错题宝的五个核心模块（认证、存储、拍照识别、复习推荐、文档导出），从而构建一个完整的智能学习系统。

**Architecture:** 
- 后端：FastAPI 单体应用，分层架构（routers → services → models）
- 数据库：**SQLite** + SQLAlchemy ORM，支持级联删除和事务保护（改自 PostgreSQL）
- 缓存：**Python 内存字典 + functools.lru_cache**，key 包含 userId 实现隔离（改自 Redis）
- AI 识别：Google Vision API 同步调用，包含 3 次自动重试和质量检查

**Tech Stack:** 
- Python 3.11 + FastAPI 0.100+ + SQLAlchemy 2.0+
- **SQLite3**（无需额外依赖）+ **aiosqlite** + Google Vision API
- pytest + pytest-asyncio + python-jose + bcrypt

---

## Global Constraints

- **Python 版本**：3.11（MUST）
- **JWT 过期时间**：1 小时
- **Vision API 超时**：5 秒
- **缓存**：内存字典 + LRU Cache，推荐计划 TTL 1 小时（内存过期或重启清空）
- **重试策略**：Vision API 失败时重试 3 次（间隔 1s/2s/4s）
- **测试覆盖率**：后端 > 80%，关键模块（认证、推荐、识别）100%
- **数据隔离**：所有查询必须加 `WHERE user_id=current_user_id`（规则 R1）
- **错误响应格式**：`{ "status": "error", "code": "ERROR_CODE", "message": "...", "details": {...} }`

---

## Phase 0: 项目初始化与基础设施

### Task 0.1: 创建后端项目结构和依赖（已批准 ✅）

**Status:** APPROVED (commit ddb2a91)

**变更说明：** Task 0.1 已完成，但需要调整以下文件：

#### Task 0.1-UPDATE: 调整 requirements.txt 和 config（新技术栈）

**Files:**
- Modify: `backend/requirements.txt` — 移除 Redis 和 PostgreSQL，添加 aiosqlite
- Modify: `backend/src/config.py` — 移除 REDIS_URL，改为 SQLite

- [ ] **Step 1: 更新 requirements.txt**

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.13.0
aiosqlite==0.19.0
python-jose[cryptography]==3.3.0
bcrypt==4.1.1
pydantic-settings==2.1.0
google-cloud-vision==3.5.0
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2
python-multipart==0.0.6
```

- [ ] **Step 2: 更新 .env.example**

```ini
# SQLite 数据库（本地单文件）
DATABASE_URL=sqlite:///./error_qa.db

# JWT
JWT_SECRET_KEY=your-secret-key-minimum-32-characters-long-here
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=1

# Vision API
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
VISION_API_TIMEOUT_SECONDS=5

# 应用
APP_ENV=development
APP_DEBUG=true
APP_LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
```

- [ ] **Step 3: 更新 src/config.py**

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./error_qa.db"
    
    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 1
    
    # Vision API
    GOOGLE_CLOUD_PROJECT: str
    VISION_API_TIMEOUT_SECONDS: int = 5
    
    # App
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]
    
    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 4: 删除 docker-compose.yml（SQLite 无需容器）**

```bash
rm backend/docker-compose.yml
```

- [ ] **Step 5: 提交**

```bash
git add backend/requirements.txt backend/.env.example backend/src/config.py
git commit -m "chore: update tech stack to SQLite + memory cache (no Redis/PostgreSQL)"
```

---

## Phase 1: 认证模块（E）

### Task 1.1: 数据库设置 + User 模型（已批准 ✅）

**Status:** APPROVED (commit efafa2d)

**变更说明：** Task 1.1 的 db.py 需要调整为 SQLite 异步驱动

#### Task 1.1-UPDATE: 调整 db.py 使用 aiosqlite

**Files:**
- Modify: `backend/src/database/db.py` — 改为 SQLite 驱动

- [ ] **Step 1: 更新 db.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.config import settings
import logging
import os

logger = logging.getLogger(__name__)

# 确保数据库目录存在
os.makedirs(os.path.dirname(settings.DATABASE_URL.split("///")[1]) if "///" in settings.DATABASE_URL else ".", exist_ok=True)

# 创建异步引擎（SQLite + aiosqlite）
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    future=True,
    connect_args={"check_same_thread": False, "timeout": 30},  # SQLite 特定参数
)

# 创建异步会话工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncSession:
    """依赖注入：获取数据库会话"""
    async with async_session_maker() as session:
        yield session

async def init_db():
    """初始化数据库（创建所有表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized (SQLite)")

async def close_db():
    """关闭数据库连接"""
    await engine.dispose()

# Base 导出
from sqlalchemy.orm import declarative_base
Base = declarative_base()
```

- [ ] **Step 2: 提交**

```bash
git add backend/src/database/db.py
git commit -m "chore: update db.py to use SQLite with aiosqlite"
```

---

### Task 1.2: JWT 和密码工具函数（已批准 ✅）

**Status:** APPROVED (commit c361801)

**无需调整** — JWT 和密码工具与数据库无关，保持不变。

---

### Task 1.3: 认证 Schema 和路由

**Files:**
- Create: `backend/src/schemas/auth.py`
- Create: `backend/src/routers/auth.py`

**Interfaces:**
- Consumes: `User` 模型、`get_db`、JWT 工具函数
- Produces：
  - `POST /api/auth/login` → `LoginResponse`
  - `POST /api/auth/verify-password` → `{ valid: bool }`

- [ ] **Step 1: 创建 auth schema (src/schemas/auth.py)**

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    expires_in: int

class PasswordVerifyRequest(BaseModel):
    password: str = Field(..., min_length=1)

class ErrorResponse(BaseModel):
    status: str = "error"
    code: str
    message: str
    details: Optional[dict] = None
```

- [ ] **Step 2: 创建认证路由 (src/routers/auth.py)**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.db import get_db
from src.models.user import User
from src.schemas.auth import LoginRequest, LoginResponse, PasswordVerifyRequest
from src.utils.security import hash_password, verify_password, create_access_token
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse, status_code=200)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """登录获取 JWT token"""
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_access_token(user.user_id, user.role)
    
    return LoginResponse(
        access_token=token,
        user_id=user.user_id,
        role=user.role,
        expires_in=3600,
    )

@router.post("/verify-password", status_code=200)
async def verify_password_endpoint(
    request: PasswordVerifyRequest,
    current_user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """验证当前用户的密码（敏感操作确认）"""
    stmt = select(User).where(User.user_id == current_user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    valid = verify_password(request.password, user.password_hash)
    return {"valid": valid}

def get_current_user(authorization: str = Depends(get_bearer_token)) -> str:
    """依赖：从 JWT 获取当前用户 ID"""
    from src.utils.security import decode_access_token
    
    payload = decode_access_token(authorization)
    if payload is None:
        raise HTTPException(status_code=401, detail="无效的 token")
    
    return payload["user_id"]

def get_bearer_token(authorization: str = None):
    """从 Authorization header 提取 bearer token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少 Authorization header")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="无效的 Authorization header")
    
    return parts[1]
```

- [ ] **Step 3: 在 main.py 中注册路由**

```python
from src.routers import auth

app.include_router(auth.router)
```

- [ ] **Step 4: 创建认证测试 (tests/unit/test_auth_endpoints.py)**

```python
import pytest
from httpx import AsyncClient
from src.main import app
from src.utils.security import hash_password, create_access_token
from src.models.user import User

@pytest.mark.asyncio
async def test_login_success(test_db, test_user):
    """测试成功登录"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "student@test.edu",
                "password": "Password123",
            },
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["user_id"] == "test-user-123"
    assert data["role"] == "student"

@pytest.mark.asyncio
async def test_verify_password_success(test_user):
    """测试密码验证成功"""
    token = create_access_token("test-user-123", "student")
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/verify-password",
            json={"password": "Password123"},
            headers={"Authorization": f"Bearer {token}"},
        )
    
    assert response.status_code == 200
    assert response.json()["valid"] is True
```

- [ ] **Step 5: 运行测试**

```bash
cd backend
pytest tests/unit/test_auth_endpoints.py -v
```

- [ ] **Step 6: 提交**

```bash
git add backend/src/schemas/auth.py backend/src/routers/auth.py backend/tests/unit/test_auth_endpoints.py
git commit -m "feat: authentication endpoints (login, verify-password)"
```

---

## Phase 2: 题目存储模块（C）

### Task 2.1: Question 和 ReviewPlan 模型

**Files:**
- Create: `backend/src/models/question.py`
- Create: `backend/src/models/review_plan.py`
- Modify: `backend/src/models/__init__.py`

**Interfaces:**
- Consumes: User 模型、SQLAlchemy Base
- Produces：
  - `Question` 模型（包含 user_id 隔离）
  - `ReviewPlan` 模型
  - 关系定义和级联删除

[完整代码见原计划 Task 2.1，无需调整 — SQLite 与模型定义兼容]

---

## Phase 3: 拍照识别模块（A）— 最难、最有意思的三天主线

### Task 3.1: Vision API 集成和质量检查

**Files:**
- Create: `backend/src/services/recognition_service.py`
- Create: `backend/src/schemas/recognition.py`

**关键实现点：**
- 规则 R2：缺 confidence 按 0 处理
- 规则 R4：三级质量检查
- 规则 R8：3 次自动重试（间隔 1s/2s/4s）
- 垃圾数据检测

[完整代码见原计划 Task 3.1，无需调整 — Vision API 与存储无关]

---

## Phase 4: 复习推荐模块（B）— 艾宾浩斯遗忘曲线

### Task 4.1: 遗忘曲线算法实现

**Files:**
- Create: `backend/src/services/recommend_service.py`

**变更说明：** 缓存从 Redis 改为内存字典 + LRU Cache

#### Task 4.1-UPDATE: 遗忘曲线 + 内存缓存

- [ ] **Step 1: 创建 recommend_service.py（含内存缓存）**

```python
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.models.review_plan import ReviewPlan
from src.models.question import Question
import logging

logger = logging.getLogger(__name__)

# 内存缓存字典（用户ID → 推荐计划）
RECOMMENDATION_CACHE = {}  # {user_id: (timestamp, recommendations)}
CACHE_TTL = 3600  # 1 小时

class RecommendService:
    # 艾宾浩斯复习间隔规划（天数）
    REVIEW_SCHEDULE = {
        0: 1,   # 首次出错后 1 天
        1: 3,   # 第 1 次复习后 3 天
        2: 7,   # 第 2 次复习后 7 天
        3: 15,  # 第 3 次复习后 15 天
        4: 30,  # 第 4 次复习后 30 天
    }
    
    @staticmethod
    def calculate_next_review_days(reviewed_count: int) -> int:
        """根据复习次数返回下次复习的天数"""
        return RecommendService.REVIEW_SCHEDULE.get(reviewed_count, 30)
    
    @staticmethod
    def calculate_spaced_repetition_score(
        last_error_time: datetime,
        last_reviewed_time: datetime,
        reviewed_count: int,
    ) -> float:
        """计算复习的紧迫性分数 [0, 1]"""
        now = datetime.now(timezone.utc)
        
        if last_reviewed_time is None:
            days_since_error = (now - last_error_time).days
            return min(1.0, days_since_error / 30.0)
        
        days_since_review = (now - last_reviewed_time).days
        next_review_days = RecommendService.calculate_next_review_days(reviewed_count)
        
        forgetting_factor = min(1.0, days_since_review / next_review_days)
        repetition_damping = max(0.1, 1.0 - reviewed_count * 0.1)
        
        return forgetting_factor * repetition_damping
    
    @staticmethod
    async def get_recommendations(
        db: AsyncSession,
        user_id: str,
        limit: int = 10,
    ) -> list:
        """获取推荐复习计划（内存缓存）"""
        now = datetime.now(timezone.utc)
        
        # 检查内存缓存
        if user_id in RECOMMENDATION_CACHE:
            timestamp, cached = RECOMMENDATION_CACHE[user_id]
            if (now - timestamp).total_seconds() < CACHE_TTL:
                logger.info(f"Cache hit for user {user_id}")
                return cached[:limit]
        
        # 计算推荐（规则 R5：事务保护）
        async with db.begin():
            stmt = select(ReviewPlan, Question).join(Question).where(
                ReviewPlan.user_id == user_id,
                Question.needs_review == False,
            )
            
            result = await db.execute(stmt)
            items = result.all()
        
        # 重新计算优先级并排序
        recommendations = []
        for plan, question in items:
            error_count = plan.error_count or 0
            spaced_score = RecommendService.calculate_spaced_repetition_score(
                plan.last_error_time,
                plan.last_reviewed_time,
                plan.reviewed_count or 0,
            )
            difficulty_factor = (question.difficulty or 3) / 5.0
            
            priority = (
                0.4 * (error_count / max(error_count + 1, 1)) +
                0.4 * spaced_score +
                0.2 * difficulty_factor
            )
            
            recommendations.append({
                'plan': plan,
                'question': question,
                'priority': priority,
            })
        
        # 按优先级倒序排序
        recommendations.sort(key=lambda x: x['priority'], reverse=True)
        
        # 存入内存缓存
        RECOMMENDATION_CACHE[user_id] = (now, recommendations)
        
        return recommendations[:limit]
    
    @staticmethod
    def clear_cache(user_id: str = None):
        """清除缓存（编辑题目后调用）"""
        if user_id:
            RECOMMENDATION_CACHE.pop(user_id, None)
        else:
            RECOMMENDATION_CACHE.clear()
```

- [ ] **Step 2: 更新推荐路由使用内存缓存**

在 `src/routers/recommendations.py` 中，移除 Redis 逻辑，改为：

```python
from src.services.recommend_service import RecommendService

@router.get("/plan", response_model=RecommendationListResponse)
async def get_recommendations(
    current_user_id: str = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """获取推荐复习计划（内存缓存）"""
    try:
        recommendations = await RecommendService.get_recommendations(
            db,
            current_user_id,
            limit,
        )
        
        # 构建响应（同原计划）
        items = [...]
        
        return RecommendationListResponse(
            items=items,
            generated_at=datetime.now(timezone.utc),
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail="获取推荐失败")

@router.post("/mark-reviewed/{plan_id}", status_code=200)
async def mark_reviewed(
    plan_id: str,
    request: MarkReviewedRequest,
    current_user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记题目已复习（清除用户缓存）"""
    try:
        async with db.begin():
            plan = await RecommendService.mark_reviewed(
                db,
                current_user_id,
                plan_id,
                request.reviewed,
            )
            await db.flush()
        
        # 清除用户缓存
        RecommendService.clear_cache(current_user_id)
        
        return {
            'status': 'success',
            'next_review_time': plan.next_review_time,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

- [ ] **Step 3: 提交**

```bash
git add backend/src/services/recommend_service.py backend/src/routers/recommendations.py
git commit -m "feat: spaced repetition with memory cache (no Redis)"
```

---

## 总体进度清单

### 已完成（保留）✅

- Task 0.1: 项目初始化（commit ddb2a91）
- Task 1.1: 数据库 + User 模型（commit efafa2d）
- Task 1.2: JWT + 密码工具（commit c361801）

### 需要调整 🔄

- Task 0.1-UPDATE: 更新依赖配置（SQLite + 移除 Redis）
- Task 1.1-UPDATE: 调整 db.py 使用 aiosqlite

### 继续实现 ▶️

- Task 1.3: 认证路由
- Task 2.1: 题目存储模型
- Task 2.2-2.3: 题目 API
- Task 3.1-3.2: **拍照识别（核心三天主线）**
- Task 4.1-4.2: 复习推荐
- Task 5.1-5.2: 文档导出

---

**关键变更总结：**

| 组件 | 原方案 | 新方案 | 影响 |
|------|-------|-------|------|
| 数据库 | PostgreSQL | SQLite | 无需容器，本地文件存储 |
| ORM 驱动 | psycopg | aiosqlite | 异步兼容，无需改动模型定义 |
| 缓存 | Redis | 内存字典 + LRU | 简化部署，重启清空缓存 |
| docker-compose | 需要（PG + Redis） | 不需要 | 加快本地启动 |

**不需要调整的：**
- JWT 和密码工具（Task 1.2）✅
- Vision API 集成（Task 3.1）✅
- 模型定义（Task 2.1、1.1）✅
- 路由定义（只需移除 Redis 代码）✅

---

**下一步：**

1. 执行 Task 0.1-UPDATE（更新 requirements.txt 和 config）
2. 执行 Task 1.1-UPDATE（调整 db.py 为 aiosqlite）
3. 继续 Task 1.3-3.2（认证、存储、拍照识别 — 三天主线）

你想立即开始执行，还是先审核这份更新计划？
