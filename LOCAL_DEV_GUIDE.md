# 错题宝 - 本地开发完整指南

**日期：** 2026-06-24  
**状态：** ✅ 前端配置已修复（host: 0.0.0.0）

---

## 🚀 快速启动（3 个终端）

### 前置条件
```bash
# 检查 Python 版本
python3.11 --version      # 需要 3.11+

# 检查 Node.js 版本
node --version            # 需要 18+
npm --version             # 需要 9+
```

---

## 终端 1: 启动后端 API（port 8000）

```bash
cd /workshop/aws-harness/backend

# 创建虚拟环境（首次）
python3.11 -m venv venv

# 激活虚拟环境
source venv/bin/activate          # Linux/Mac
# 或 Windows:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移（首次）
alembic upgrade head

# 启动 FastAPI 服务器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**期望输出：**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**验证后端：**
```bash
curl http://localhost:8000/health
# 输出：{"status":"ok"}
```

---

## 终端 2: 启动前端开发服务器（port 5173）

```bash
cd /workshop/aws-harness/frontend

# 安装依赖（首次）
npm install

# 启动 Vite 开发服务器
npm run dev
```

**期望输出：**
```
  VITE v5.0.0  ready in 125 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

---

## 终端 3: 访问应用

### 本地直接访问
```
http://localhost:5173
```

### 登录
```
Email:    student@test.edu
Password: Password123
```

### API 文档
```
http://localhost:8000/docs       # Swagger UI
http://localhost:8000/redoc      # ReDoc
```

---

## 📊 服务状态检查

### 检查后端是否运行
```bash
curl -i http://localhost:8000/docs
# 应该返回 200 OK
```

### 检查前端是否运行
```bash
curl -i http://localhost:5173
# 应该返回 200 OK + HTML 内容
```

### 测试 API 调用
```bash
# 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"student@test.edu","password":"Password123"}'

# 返回 JWT token（类似）
# {"access_token":"eyJhbGc...","token_type":"bearer","expires_in":3600}
```

---

## ❌ 常见问题排查

### 问题 1: 前端显示 400 Bad Request

**原因：** Vite Host 验证失败

**解决：**
```bash
# 确认 vite.config.ts 有这些配置：
grep -A 5 "host: '0.0.0.0'" /workshop/aws-harness/frontend/vite.config.ts

# 应该包含：
# host: '0.0.0.0',
# hmr: { host: 'localhost', port: 5173, protocol: 'http' }

# 如果没有，重新运行修复脚本
```

---

### 问题 2: 后端返回 "Cannot import module"

**原因：** 虚拟环境未激活或依赖缺失

**解决：**
```bash
# 检查虚拟环境是否激活（prompt 应该显示 (venv)）
which python

# 如果不对，重新激活
cd /workshop/aws-harness/backend
source venv/bin/activate
pip install -r requirements.txt
```

---

### 问题 3: 前端无法连接到后端 API

**原因：** 后端未运行或 API 地址错误

**排查：**
```bash
# 1. 检查后端是否运行
curl http://localhost:8000/docs

# 2. 查看前端 API 配置
cat /workshop/aws-harness/frontend/src/services/api.ts | grep baseURL

# 3. 检查浏览器控制台（F12）
# 查看 Network 标签，看是否有 CORS 错误
```

---

### 问题 4: npm install 失败

**原因：** Node.js 版本过低或网络问题

**解决：**
```bash
# 清空缓存
rm -rf node_modules package-lock.json

# 重新安装
npm install --verbose

# 如果还是失败，检查 Node 版本
node --version    # 需要 18+
```

---

### 问题 5: 登录后仍然显示登录页面

**原因：** Token 存储或认证状态问题

**排查：**
```bash
# 1. 打开浏览器 DevTools (F12)
# 2. Console 标签检查是否有错误
# 3. Application/Storage 标签检查是否保存了 token
# 4. 查看 Network 标签的登录请求是否返回 token

# 后端测试登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"student@test.edu","password":"Password123"}' | jq .
```

---

## 📱 Vite 开发服务器 HMR 配置

**什么是 HMR？** Hot Module Replacement（热模块替换）— 代码改动后自动刷新浏览器

**当前配置（已修复）：**
```javascript
// vite.config.ts
server: {
  host: '0.0.0.0',           // 接受所有网络接口的连接
  hmr: {
    host: 'localhost',       // HMR 通过 localhost 连接
    port: 5173,
    protocol: 'http',
  },
}
```

**修改代码后的流程：**
1. 你编辑 `src/pages/Login.tsx`
2. 保存文件
3. Vite 检测到变化
4. 通过 HMR 通知浏览器
5. 浏览器自动刷新（**无需手动刷新**）

---

## 🔄 工作流程

### 典型的开发流程

```
1. 3 个终端同时运行：后端、前端、浏览器访问

2. 你编辑 frontend/src/pages/Login.tsx
   → 保存文件
   → Vite 自动检测
   → 浏览器自动刷新

3. 你编辑 backend/src/routers/auth.py
   → 保存文件
   → Uvicorn 自动重载（--reload）
   → API 立即生效

4. 在浏览器中测试
   → 在 DevTools 中调试
   → 提交 Git
```

---

## ✅ 验证清单

启动后检查以下项目：

- [ ] 后端运行：`curl http://localhost:8000/health` → 200 OK
- [ ] 前端运行：`curl http://localhost:5173` → 200 OK + HTML
- [ ] 浏览器访问：`http://localhost:5173` → 显示登录页面
- [ ] 登录成功：输入凭证后进入 Dashboard
- [ ] API 文档：`http://localhost:8000/docs` → 显示 Swagger UI
- [ ] 热重载工作：编辑前端文件后浏览器自动刷新

---

## 🛠️ 常用命令

### 后端

```bash
# 启动服务（开发模式，自动重载）
uvicorn src.main:app --reload --port 8000

# 运行测试
pytest tests/unit/ -v
pytest tests/integration/ -v

# 查看测试覆盖率
pytest tests/ --cov=src

# 代码格式化
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

# ESLint 检查
npm run lint

# 格式化代码
npm run format

# 运行单元测试
npm run test

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

---

## 📚 文档导航

| 文件 | 说明 |
|------|------|
| `ACCESS_GUIDE.md` | 完整的访问指南（本地 + AWS） |
| `CLAUDE.md` | 项目开发指导（技术栈、规则、设计模式） |
| `FINAL_PROJECT_REPORT.md` | 项目完成度报告 |
| `docs/superpowers/specs/` | 设计文档 |
| `docs/superpowers/plans/` | 实现计划 |

---

## 🚀 下一步

1. ✅ 后端运行正常
2. ✅ 前端运行正常
3. 📱 在浏览器中测试完整功能
4. 🧪 运行测试验证代码质量
5. 📤 （可选）部署到 AWS CDK

---

**版本：** 1.0  
**最后更新：** 2026-06-24  
**状态：** ✅ 生产就绪

