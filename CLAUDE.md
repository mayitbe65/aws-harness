# CLAUDE.md

本文件为在此仓库中使用 Claude Code（claude.ai/code）提供指导。

## 概述

**错题宝**：一个面向学生的智能学习系统。学生拍照上传错题 → AI 自动识别题目 → 数字化管理、智能复习推荐 → 可选排版成可打印文档。

核心流程：
```
📸 拍照上传 → 🤖 AI 识别 → 💾 数字化存储 → 📚 智能推荐 → 📄 文档导出
```

## 核心功能

| 功能 | 说明 |
|------|------|
| **题目识别** | OCR + Vision API 识别题目文本和图片、解析结构 |
| **数字化管理** | 按科目/知识点/难度分类管理题目，标记错误原因 |
| **智能推荐** | 基于错误频率、难度、遗忘曲线推荐复习计划 |
| **文档导出** | 生成排版精美的 PDF 或 Word 可打印文档 |
| **学习统计** | 错题趋势、掌握度、学习进度可视化 |

## 技术栈

### 后端（Python 3.11）
- **框架**：FastAPI 0.100+
- **ORM**：SQLAlchemy 2.0+
- **异步队列**：Celery + Redis
- **文档生成**：ReportLab

### 前端（React + TypeScript）
- **框架**：React 18.x + TypeScript 5.x
- **构建工具**：Vite 5.x
- **路由**：React Router 6.x
- **状态管理**：Context API（简单场景）或 Zustand（复杂场景）
- **样式**：CSS Modules / Tailwind CSS
- **UI 组件**：自定义或 Ant Design / Material-UI
- **HTTP 客户端**：Axios
- **测试**：Vitest + React Testing Library
- **类型检查**：TypeScript 5.x 严格模式
- **代码格式**：Prettier + ESLint

### 基础设施
- **数据库**：PostgreSQL 14+
- **缓存**：Redis 7+
- **AI/视觉**：Google Vision API 或 Claude Vision API
- **部署**：Docker + Docker Compose

## 项目结构

项目位置：`/workshop/aws-harness/`

```
aws-harness/
├── CLAUDE.md                        # 本文件
├── rules/
│   └── severity-guide.md           # 规则等级指南
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Upload.tsx          # 拍照/上传页面
│   │   │   ├── QuestionDetail.tsx  # 题目详情、标记错因
│   │   │   ├── Dashboard.tsx       # 学习统计、复习计划
│   │   │   ├── Export.tsx          # 文档导出页面
│   │   │   ├── Login.tsx           # 登录/注册页面
│   │   │   └── NotFound.tsx        # 404 页面
│   │   ├── components/
│   │   │   ├── Layout.tsx          # 主布局（Header、Sidebar）
│   │   │   ├── ImageUpload.tsx     # 图片上传组件
│   │   │   ├── QuestionCard.tsx    # 题目卡片
│   │   │   ├── RecommendList.tsx   # 推荐复习列表
│   │   │   ├── LoadingSpinner.tsx  # 加载指示器
│   │   │   └── ErrorBoundary.tsx   # 错误边界
│   │   ├── services/
│   │   │   ├── api.ts              # Axios API 客户端和 TypeScript 类型
│   │   │   └── storage.ts          # LocalStorage 封装
│   │   ├── context/
│   │   │   ├── AuthContext.tsx     # 用户认证状态
│   │   │   └── AppContext.tsx      # 全局应用状态
│   │   ├── hooks/
│   │   │   ├── useAuth.ts          # 认证 hook
│   │   │   ├── useQuestions.ts     # 题目管理 hook
│   │   │   └── useRecommendations.ts # 推荐管理 hook
│   │   ├── types/
│   │   │   ├── api.ts              # API 响应类型定义
│   │   │   ├── models.ts           # 数据模型类型定义
│   │   │   └── index.ts            # 类型导出
│   │   ├── utils/
│   │   │   ├── validators.ts       # 表单验证
│   │   │   ├── formatters.ts       # 数据格式化
│   │   │   └── constants.ts        # 常量定义
│   │   ├── styles/
│   │   │   ├── globals.css         # 全局样式
│   │   │   ├── Layout.module.css   # CSS Modules
│   │   │   └── variables.css       # CSS 变量
│   │   ├── App.tsx                 # 主组件和路由配置
│   │   ├── main.tsx                # React 入口点
│   │   └── vite-env.d.ts           # Vite 类型声明
│   ├── public/                     # 静态资源
│   │   └── favicon.ico
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── package.json
│   ├── tsconfig.json               # TypeScript 配置（严格模式）
│   ├── vite.config.ts              # Vite 配置
│   ├── vitest.config.ts            # Vitest 配置
│   ├── eslint.config.js            # ESLint 配置
│   └── .prettierrc                 # Prettier 配置
├── backend/
│   ├── src/
│   │   ├── routers/
│   │   │   ├── questions.py        # 题目管理端点
│   │   │   ├── users.py            # 用户端点
│   │   │   ├── recommendations.py  # 推荐引擎端点
│   │   │   └── export.py           # 文档导出端点
│   │   ├── services/
│   │   │   ├── ai_service.py       # AI 识别服务（调用 Vision API）
│   │   │   ├── question_service.py # 题目业务逻辑
│   │   │   ├── recommend_service.py# 复习推荐算法
│   │   │   └── export_service.py   # PDF/Word 生成
│   │   ├── models/
│   │   │   ├── question.py         # 题目数据模型
│   │   │   ├── user.py             # 用户模型
│   │   │   └── review_plan.py      # 复习计划模型
│   │   ├── middleware/
│   │   │   ├── auth.py             # JWT 认证
│   │   │   └── error_handler.py    # 错误处理
│   │   ├── database/
│   │   │   ├── migrations/         # 数据库迁移脚本
│   │   │   └── seeds/              # 初始数据
│   │   ├── main.py                 # FastAPI 应用入口
│   │   └── config.py               # 配置文件
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── requirements.txt            # Python 依赖（Python 3.11）
│   ├── .env.example
│   └── pyproject.toml              # Poetry 或 setuptools 配置
├── docs/
│   ├── API.md                      # API 文档
│   ├── ARCHITECTURE.md             # 架构设计
│   └── AI-RECOGNITION.md           # AI 识别流程
└── docker-compose.yml              # 本地开发环境
```

## 常见开发任务

| 任务 | 命令 |
|------|------|
| **本地开发启动** | `docker-compose up`（启动数据库+后端+前端） |
| **后端开发** | `cd backend && python3.11 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && uvicorn src.main:app --reload` |
| **前端开发** | `cd frontend && npm install && npm run dev` |
| **前端类型检查** | `cd frontend && npm run type-check` |
| **后端单元测试** | `cd backend && pytest tests/unit/` |
| **后端集成测试** | `cd backend && pytest tests/integration/` |
| **后端所有测试** | `cd backend && pytest tests/ --cov=src` |
| **后端代码检查** | `cd backend && black . && flake8 . && mypy src/` |
| **前端单元测试** | `cd frontend && npm run test` |
| **前端测试覆盖率** | `cd frontend && npm run test:coverage` |
| **前端代码检查** | `cd frontend && npm run lint && npm run format:check` |
| **前端代码格式化** | `cd frontend && npm run format` |
| **数据库迁移** | `cd backend && alembic upgrade head` |
| **构建生产** | `cd backend && pip install -r requirements.txt && cd ../frontend && npm install && npm run build` |
| **部署** | `docker build . && docker push ...` |

## 关键设计模式

### 1. AI 识别流程
- 用户上传图片 → 后端调用 Vision API（Google/Claude）→ 解析题目文本和结构 → 存储到数据库
- **MUST**：不要在前端暴露 API 密钥，所有 AI 调用必须通过后端代理
- 使用异步队列（Celery + Redis）处理耗时的 Vision API 调用，不阻塞 HTTP 响应

### 2. 推荐算法
- 基于**错误频率**：同一知识点错误次数越多，优先级越高
- 基于**遗忘曲线**：距离最后一次做错时间越长，优先级越高
- 基于**难度**：适配学生当前能力水平
- **SHOULD**：先用简单的加权算法，有数据后再优化为机器学习模型
- 实现在 `src/services/recommend_service.py`，需单元测试验证

### 3. 数据结构（SQLAlchemy ORM）
```
User (用户)
  ├─ user_id, email, password_hash, created_at
  └─ Questions (错题)
      ├─ question_id, image_url, recognized_text, subject, difficulty
      ├─ Errors (错误记录)
      │   ├─ error_id, timestamp, reason, correct_answer
      │   └─ ReviewPlan (复习计划)
      │       └─ plan_id, next_review_time, priority
      └─ ExportRecords (导出记录)
          └─ record_id, format (PDF/Word), created_at, file_url
```

### 4. 文档导出
- 使用 Jinja2 模板生成 HTML，ReportLab 转换为 PDF
- 按科目/知识点分节，包含错题、解析、复习建议
- **CAN** 支持多种格式（PDF、HTML 可打印版）
- 实现在 `src/services/export_service.py`

### 5. API 架构（FastAPI）
- 使用 FastAPI 框架，自动生成 OpenAPI 文档
- 所有路由按功能模块组织在 `src/routers/` 目录
- 使用依赖注入管理数据库连接、认证等
- 异常统一通过 `src/middleware/error_handler.py` 处理

### 6. 前端架构（React + TypeScript）
- **路由**：React Router 6 在 `App.tsx` 中定义，嵌套路由结构
- **状态管理**：使用 Context API 管理认证和全局状态
  - `AuthContext`：用户登录态、token 存储
  - `AppContext`：全局通知、加载状态、题目列表
- **Custom Hooks**：业务逻辑封装在 hooks 中（useAuth、useQuestions 等）
- **类型定义**：所有 API 响应和数据模型在 `types/` 中定义，启用 TypeScript 严格模式
- **API 调用**：通过 `services/api.ts` 的 Axios 实例统一管理
  - 自动添加 Authorization header（从 localStorage 读取 token）
  - 统一错误处理和请求拦截
- **样式**：使用 CSS Modules 或 Tailwind CSS，避免全局样式污染
- **错误处理**：`ErrorBoundary` 组件捕获 React 错误；useEffect 中的 API 错误通过 Context 显示

## 开发注意事项

### 后端（Python 3.11 + FastAPI）

1. **Python 版本（MUST）**
   - 所有代码必须兼容 **Python 3.11**
   - 使用 `python3.11 -m venv venv` 创建虚拟环境
   - `requirements.txt` 中声明 `python_requires=">=3.11"`

2. **API 密钥管理（MUST）**
   - 所有敏感密钥（Vision API、数据库连接字符串、JWT 密钥）存储在 `.env` 文件
   - **MUST NOT** 提交 `.env` 到 git，使用 `.env.example` 作为模板
   - 通过 `pydantic_settings` 加载环境变量到 `src/config.py`

3. **代码风格（SHOULD）**
   - 使用 `black` 格式化代码（`black src/ tests/`）
   - 使用 `flake8` 检查代码质量
   - 使用 `mypy` 进行类型检查
   - 遵循 PEP 8，使用 snake_case 命名

4. **异步处理（MUST）**
   - Vision API 调用使用 Celery + Redis 异步队列，不阻塞 HTTP 响应
   - 在 `src/services/ai_service.py` 中定义 Celery 任务
   - 前端轮询或 WebSocket 监听任务完成状态

5. **数据库（MUST）**
   - 使用 SQLAlchemy ORM + Alembic 管理迁移
   - 所有 write 操作需要事务保证（`async with db.begin()`）
   - 定义在 `src/models/` 中，使用 snake_case 表名

6. **测试覆盖（MUST）**
   - AI 识别服务需 mock 测试，不真实调用 Vision API
   - 推荐算法需单元测试验证逻辑正确性（目标覆盖率 > 80%）
   - 使用 `pytest` + `pytest-cov` 运行测试和覆盖率检查
   - 新功能需集成测试验证端到端流程

7. **图片处理（SHOULD）**
   - 上传图片应压缩到合理大小（< 5MB）
   - 存储到云存储（S3/阿里 OSS），后端存储 URL 和元数据
   - 使用 Pillow 库处理图片缩放和验证

8. **性能考虑**
   - 添加 Redis 缓存层减少数据库查询
   - 使用数据库索引优化 JOIN 和 WHERE 查询
   - 定期分析慢查询日志

### 前端（React + TypeScript）

1. **TypeScript 严格模式（MUST）**
   - `tsconfig.json` 中启用 `"strict": true`
   - 所有函数参数和返回值必须显式标注类型
   - 禁止使用 `any`，使用 `unknown` 或具体类型
   - **MUST NOT** 使用 `// @ts-ignore` 注释，除非有特殊理由

2. **类型定义（MUST）**
   - 所有 API 响应类型定义在 `src/types/api.ts`
   - 所有数据模型类型定义在 `src/types/models.ts`
   - React 组件的 props 必须定义接口（interface 或 type）
   - 示例：
     ```tsx
     interface QuestionCardProps {
       question: Question;
       onEdit: (id: string) => void;
       onDelete: (id: string) => Promise<void>;
     }
     ```

3. **代码风格（SHOULD）**
   - 使用 Prettier 格式化代码（`npm run format`）
   - 使用 ESLint 检查代码质量（`npm run lint`）
   - 使用 TypeScript 类型检查（`npm run type-check`）
   - 遵循 React 最佳实践：
     - 使用函数组件和 hooks，不用 class 组件
     - 自定义 hooks 提取业务逻辑
     - 使用 `useCallback` 和 `useMemo` 优化性能

4. **状态管理（SHOULD）**
   - 使用 Context API + custom hooks 管理全局状态
   - 不要过度使用状态，优先使用 props drilling
   - 复杂场景考虑 Zustand（比 Redux 轻量）
   - 避免在 Context 中存储过多数据，拆分为多个 Context

5. **API 调用（MUST）**
   - 所有 HTTP 请求通过 `services/api.ts` 的 Axios 实例
   - 自动添加 Authorization header（从 localStorage 读取 token）
   - 统一错误处理：失败时显示 toast 通知
   - 示例：
     ```tsx
     const { data } = await api.get<Question[]>('/api/questions');
     ```

6. **错误处理（SHOULD）**
   - 使用 ErrorBoundary 捕获 React 组件错误
   - useEffect 中的异步错误通过 try-catch 处理并更新状态
   - 显示有意义的错误信息给用户

7. **测试覆盖（SHOULD）**
   - 使用 Vitest + React Testing Library
   - 新功能需单元测试（目标覆盖率 > 70%）
   - 关键路径（上传、推荐、导出）需集成测试
   - Mock API 调用和 localStorage

8. **性能优化（CAN）**
   - 使用 React.lazy 和 Suspense 实现代码分割
   - 使用虚拟化列表（如 react-window）处理大列表
   - 避免不必要的重渲染（使用 useMemo、useCallback）
   - 图片加载使用懒加载和占位符

9. **国际化（SHOULD）**
   - 使用 i18next 支持中文/英文界面切换
   - 所有用户可见文本使用 i18n 翻译，不硬编码
   - 配置文件在 `src/i18n/locales/`

10. **浏览器兼容性（SHOULD）**
    - 目标兼容现代浏览器（Chrome 90+、Firefox 88+、Safari 14+）
    - 不支持 IE 11

## 规则与原则

参考 `rules/severity-guide.md` 理解规则等级和项目特定要求：
- **MUST**：硬约束，无条件遵守（Python 3.11、密钥管理、事务保证、async Vision API 调用等）
- **SHOULD**：强建议，默认遵守，有充分理由可偏离（代码风格、测试覆盖率、备份恢复等）
- **CAN**：灵活选择，用判断力（导出格式、缓存策略、部署平台等）

---

## 快速开始

### 方式 1：Docker Compose（推荐）
```bash
cd /workshop/aws-harness
docker-compose up
# 等待所有服务启动
# 前端：http://localhost:3000
# 后端 API：http://localhost:8000
# 文档：http://localhost:8000/docs
```

### 方式 2：本地开发

#### 后端（终端 1）
```bash
cd /workshop/aws-harness/backend

# 使用 Python 3.11
python3.11 -m venv venv
source venv/bin/activate  # 或 Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 Vision API 密钥、数据库连接等

# 运行数据库迁移
alembic upgrade head

# 启动 FastAPI 服务器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端（终端 2）
```bash
cd /workshop/aws-harness/frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 访问：http://localhost:5173
```

#### 数据库（Docker）
```bash
# 如果不使用 docker-compose，手动启动 PostgreSQL
docker run --name postgres-error-qa \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=error_qa \
  -p 5432:5432 \
  -d postgres:14-alpine
```

---

## 常见问题排查

| 问题 | 排查步骤 |
|------|--------|
| **后端：`ModuleNotFoundError`** | 确保激活虚拟环境，运行 `pip install -r requirements.txt` |
| **后端：Vision API 调用超时** | 检查 `.env` 中的 API 密钥和网络连接，确认配额未用尽 |
| **后端：数据库连接失败** | 运行 `alembic upgrade head`，检查 `.env` 中的数据库 URL |
| **前端：`npm install` 失败** | 删除 `node_modules` 和 `package-lock.json`，重新运行 `npm install` |
| **前端：TypeScript 错误** | 运行 `npm run type-check`，确保所有类型定义正确 |
| **前端：无法连接后端** | 检查后端是否运行在 `http://localhost:8000`，前端 `src/services/api.ts` 中的 baseURL |
| **前端：样式未加载** | 确认 CSS Modules 导入正确，检查浏览器开发工具的 Network 标签 |

---

## 前端项目初始化（如果从零开始）

```bash
# 使用 Vite 创建 React + TypeScript 项目
npm create vite@latest frontend -- --template react-ts

cd frontend

# 安装必需依赖
npm install axios react-router-dom

# 安装开发依赖
npm install -D \
  typescript \
  vitest \
  @vitest/ui \
  @testing-library/react \
  @testing-library/jest-dom \
  eslint \
  eslint-plugin-react \
  eslint-plugin-react-hooks \
  prettier

# 配置 TypeScript 严格模式
# 编辑 tsconfig.json，设置 "strict": true

# 配置 ESLint 和 Prettier
npx eslint --init
# 选择 React + TypeScript

# 生成初始化文件
npm run build
```

---

## 后端项目初始化（如果从零开始）

```bash
cd backend

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装 FastAPI 和基础依赖
pip install fastapi uvicorn sqlalchemy alembic psycopg[binary] pydantic-settings celery redis python-jose bcrypt

# 生成 requirements.txt
pip freeze > requirements.txt

# 初始化 Alembic
alembic init alembic

# 创建 .env.example
cp .env .env.example
```
