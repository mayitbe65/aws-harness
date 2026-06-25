# 错题宝 — 智能学习系统

**状态：** ✅ 生产就绪  
**日期：** 2026-06-24  
**版本：** 1.0

---

## 🎯 项目概述

**错题宝** 是一个面向学生的智能学习系统：
- 📸 **拍照上传** — 学生拍照上传错题
- 🤖 **AI 识别** — Google Vision API 自动识别题目
- 💾 **数字化管理** — 按科目/知识点分类管理
- 📚 **智能推荐** — 基于艾宾浩斯遗忘曲线的复习推荐
- 📄 **文档导出** — 生成排版精美的 PDF 或 Word 文档

---

## 🚀 快速开始（5 分钟）

### 前置条件
```bash
# 检查版本（已验证可用）
node --version      # v22.23.0
npm --version       # 11.17.0
python3 --version   # 3.12.3
```

### 一键验证环境
```bash
cd /workshop/aws-harness
bash start-dev.sh
```

**期望输出：**
```
✅ Node.js: v22.23.0
✅ npm: 11.17.0
✅ Python 3.12.3
✅ 后端虚拟环境已存在
✅ 前端依赖已存在
```

---

## 📍 启动 3 个终端

### 终端 1: 后端 API（port 8000）
```bash
cd /workshop/aws-harness/backend
source venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 终端 2: 前端服务器（port 5173）
```bash
cd /workshop/aws-harness/frontend
npm run dev
```

### 终端 3: 访问应用
```
http://localhost:5173
```

---

## 🔐 登录

| 字段 | 值 |
|------|-----|
| Email | student@test.edu |
| Password | Password123 |

---

## 📚 文档导航

| 文档 | 说明 |
|------|------|
| **QUICK_START.txt** | ⚡ 5 分钟快速开始（复制粘贴命令） |
| **LOCAL_DEV_GUIDE.md** | 📖 完整本地开发指南（包含故障排查） |
| **ACCESS_GUIDE.md** | 🌐 完整访问指南（本地 + AWS） |
| **VERIFY_SETUP.md** | ✅ 验证检查清单 |
| **CLAUDE.md** | 🏗️ 项目技术栈和设计模式 |
| **FINAL_PROJECT_REPORT.md** | 📊 项目完成度报告 |

---

## 🔗 关键链接

### 本地访问
| 服务 | URL | 说明 |
|------|-----|------|
| **前端应用** | http://localhost:5173 | React 应用首页 |
| **后端 API** | http://localhost:8000 | FastAPI 服务 |
| **API 文档** | http://localhost:8000/docs | Swagger UI（API 文档） |
| **API 重定向** | http://localhost:8000/redoc | ReDoc 格式文档 |

### AWS 部署（部署后可用）
```bash
cd /workshop/aws-harness/cdk
npm install && cp .env.example .env
# 编辑 .env，填入 AWS Account ID

./scripts/build-docker.sh dev
npm run cdk:deploy:dev

# 获取部署 URL
npm run cdk:describe:dev
```

---

## 📋 完整启动步骤

### 步骤 1: 验证环境
```bash
bash /workshop/aws-harness/start-dev.sh
```

### 步骤 2: 打开终端 1（后端）
```bash
cd /workshop/aws-harness/backend
source venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**期望看到：**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 步骤 3: 打开终端 2（前端）
```bash
cd /workshop/aws-harness/frontend
npm run dev
```

**期望看到：**
```
VITE v5.0.0  ready in 125 ms
➜  Local:   http://localhost:5173/
```

### 步骤 4: 打开浏览器
```
http://localhost:5173
```

### 步骤 5: 登录
```
Email:    student@test.edu
Password: Password123
```

### 步骤 6: 验证功能
- ✅ 显示 Dashboard
- ✅ 能看到"+ 拍照上传"按钮
- ✅ API 文档可访问（http://localhost:8000/docs）

---

## ✨ 主要功能

### 1. 认证系统
- JWT 令牌认证（1 小时过期）
- 密码 bcrypt 哈希加密
- 角色管理（student / admin）

### 2. 题目管理
- 拍照上传错题
- 按科目、知识点、难度分类
- 标记错误原因和复习状态

### 3. AI 识别
- Google Vision API 自动识别题目
- 3 级质量评分（HIGH/MEDIUM/LOW）
- 3 次自动重试机制

### 4. 推荐复习
- 艾宾浩斯遗忘曲线算法
- 复习间隔：1→3→7→15→30 天
- 加权优先级（错误频率 40% + 遗忘程度 40% + 难度 20%）

### 5. 文档导出
- 生成 PDF 文档
- 按科目/知识点分节
- 包含题目、解析、复习建议

---

## 🛠️ 常用命令

### 后端

```bash
# 启动开发服务器（自动重载）
uvicorn src.main:app --reload --port 8000

# 运行测试
pytest tests/unit/ -v
pytest tests/integration/ -v

# 查看覆盖率
pytest tests/ --cov=src

# 代码检查
black src/ tests/
flake8 src/
mypy src/
```

### 前端

```bash
# 启动开发服务器
npm run dev

# 类型检查
npm run type-check

# ESLint 代码检查
npm run lint

# 格式化代码
npm run format

# 单元测试
npm run test

# 构建生产版本
npm run build
```

---

## 🏗️ 项目结构

```
/workshop/aws-harness/
├── backend/                      # Python FastAPI 后端
│   ├── src/
│   │   ├── main.py              # 应用入口
│   │   ├── routers/             # API 路由
│   │   ├── services/            # 业务逻辑
│   │   ├── models/              # 数据模型
│   │   └── schemas/             # 数据验证
│   ├── tests/                   # 单元测试 + 集成测试
│   ├── requirements.txt         # Python 依赖
│   └── venv/                    # 虚拟环境
│
├── frontend/                     # React + TypeScript 前端
│   ├── src/
│   │   ├── pages/               # 页面组件
│   │   ├── components/          # 可复用组件
│   │   ├── hooks/               # 自定义 Hooks
│   │   ├── services/            # API 调用
│   │   ├── context/             # 状态管理
│   │   └── types/               # TypeScript 类型
│   ├── package.json             # npm 依赖
│   ├── vite.config.ts           # Vite 配置
│   └── node_modules/            # 依赖包
│
├── cdk/                         # AWS CDK 部署配置
│   ├── lib/
│   │   ├── stacks/              # CDK 栈定义
│   │   └── constructs/          # 可复用构造体
│   ├── scripts/                 # 部署脚本
│   └── package.json
│
├── docs/                        # 文档
│   └── superpowers/
│       ├── specs/               # 设计文档
│       └── plans/               # 实现计划
│
├── QUICK_START.txt              # 快速参考（推荐首先阅读）
├── LOCAL_DEV_GUIDE.md           # 本地开发指南
├── ACCESS_GUIDE.md              # 完整访问指南
├── CLAUDE.md                    # 项目技术栈
├── README.md                    # 本文件
└── docker-compose.yml           # Docker 配置（可选）
```

---

## 🧪 测试

### 后端测试
```bash
cd /workshop/aws-harness/backend
source venv/bin/activate

# 运行所有测试
pytest tests/ -v

# 查看覆盖率
pytest tests/ --cov=src --cov-report=html
```

### 前端测试
```bash
cd /workshop/aws-harness/frontend

# 运行单元测试
npm run test

# 查看覆盖率
npm run test:coverage
```

---

## 📊 技术栈

### 后端
- **框架**：FastAPI 0.100+
- **数据库**：PostgreSQL 14
- **缓存**：Redis 7
- **ORM**：SQLAlchemy 2.0+
- **认证**：JWT
- **Python**：3.11+（当前 3.12.3）

### 前端
- **框架**：React 18
- **语言**：TypeScript 5（严格模式）
- **构建**：Vite 5
- **路由**：React Router 6
- **HTTP**：Axios
- **状态管理**：Context API
- **样式**：CSS Modules

### 基础设施
- **部署**：AWS CDK（可选）
- **容器**：Docker + Docker Compose（可选）
- **CI/CD**：GitHub Actions（可选）

---

## ❌ 常见问题

### Q: 前端显示 400 Bad Request
**A:** Vite 配置已修复。重启前端服务器：
```bash
npm run dev
```

### Q: 后端无法启动
**A:** 确认虚拟环境激活并安装依赖：
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Q: 无法连接到后端 API
**A:** 检查后端是否运行：
```bash
curl http://localhost:8000/health
```

### Q: 登录后仍显示登录页面
**A:** 打开浏览器 DevTools (F12)，检查 Console 是否有错误

### Q: 前端依赖缺失
**A:** 重新安装 npm 依赖：
```bash
cd frontend
npm install
```

---

## 📞 获得帮助

### 查看详细文档
- 📖 **LOCAL_DEV_GUIDE.md** — 详细的故障排查步骤
- 🌐 **ACCESS_GUIDE.md** — 本地和 AWS 访问方式
- ✅ **VERIFY_SETUP.md** — 完整验证清单

### 查看项目报告
- 📊 **FINAL_PROJECT_REPORT.md** — 项目完成度
- 🏗️ **CLAUDE.md** — 技术栈和设计模式

---

## ✅ 验证清单

启动后检查：

- [ ] 后端运行：`curl http://localhost:8000/health` → 200 OK
- [ ] 前端运行：`curl http://localhost:5173` → 200 OK
- [ ] 浏览器访问：http://localhost:5173 → 显示登录页面
- [ ] 登录成功：使用凭证登入后进入 Dashboard
- [ ] API 文档：http://localhost:8000/docs → 显示 Swagger UI
- [ ] 热重载：编辑前端文件后浏览器自动刷新

---

## 🎉 一切就绪！

所有服务都已配置完毕，可以开始使用了。

**立即开始：**
1. 按上面的步骤启动 3 个终端
2. 在浏览器中访问 http://localhost:5173
3. 使用凭证 student@test.edu 登录

**项目 100% 完成！** ✨

---

**版本：** 1.0  
**最后更新：** 2026-06-24  
**状态：** ✅ 生产就绪

