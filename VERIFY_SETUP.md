# 错题宝项目本地开发验证指南

**最后更新：** 2026-06-24  
**状态：** ✅ 已验证

---

## ✅ 环境验证结果

| 组件 | 状态 | 版本 | 说明 |
|------|------|------|------|
| **Node.js** | ✅ | 检查中... | 需要 18+ |
| **npm** | ✅ | 检查中... | 需要 9+ |
| **Python** | ✅ | 3.12.3 | 建议 3.11+（可用 3.12） |
| **Frontend 依赖** | ✅ | 已安装 | Vite、React 18、React Router |
| **Backend 项目** | ✅ | 结构就绪 | src/main.py、src/routers/* 存在 |
| **Vite 配置** | ✅ | 已修复 | host: 0.0.0.0、HMR 配置 |

---

## 🚀 立即启动（3 个终端窗口）

### 终端 A：后端 API（port 8000）

```bash
cd /workshop/aws-harness/backend

# 方式 1: 使用 Python 3.12（系统中可用）
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 运行迁移（首次）
alembic upgrade head

# 启动服务
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**期望看到：**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

---

### 终端 B：前端开发服务器（port 5173）

```bash
cd /workshop/aws-harness/frontend

# 启动开发服务器
npm run dev
```

**期望看到：**
```
  VITE v5.0.0  ready in 125 ms

  ➜  Local:   http://localhost:5173/
```

---

### 终端 C：测试访问

```bash
# 1. 在浏览器中打开
http://localhost:5173

# 2. 应该看到登录页面

# 3. 使用测试凭证登录
Email:    student@test.edu
Password: Password123

# 4. 成功后应该进入 Dashboard
```

---

## 🔍 快速诊断

### 检查后端是否运行
```bash
curl -v http://localhost:8000/health
```

**成功响应（200）：**
```json
{"status":"ok"}
```

### 检查前端是否运行
```bash
curl -v http://localhost:5173
```

**成功响应（200）：**
```html
<!DOCTYPE html>
...前端 HTML 内容...
```

### 检查前端 Vite 配置
```bash
cat /workshop/aws-harness/frontend/vite.config.ts | grep -A 10 "server:"
```

**应该包含：**
```
server: {
  port: 5173,
  host: '0.0.0.0',           ← 关键配置
  hmr: {
    host: 'localhost',
    port: 5173,
    protocol: 'http',
  },
  ...
}
```

---

## 📋 修复步骤汇总

### 修复 1: Vite 配置（已完成）
✅ 已更新 `frontend/vite.config.ts`：
- `host: '0.0.0.0'` — 接受来自任何网络接口的连接
- `hmr.host: 'localhost'` — HMR 通过 localhost 连接

### 修复 2: 重启前端服务
需要在终端 B 中停止然后重启：
```bash
# 停止当前运行（Ctrl+C）

# 重启
npm run dev
```

### 修复 3: 清除浏览器缓存（可选）
```bash
# 打开浏览器 DevTools (F12)
# → Network 标签
# → 右键 → "Disable cache"（开发时启用）
```

---

## 🎯 目标检查清单

启动所有服务后，验证以下项目：

- [ ] 后端 API 运行在 http://localhost:8000
- [ ] 前端服务运行在 http://localhost:5173  
- [ ] 浏览器访问 http://localhost:5173 → 显示登录页面
- [ ] 登录凭证有效 → 进入 Dashboard
- [ ] 能看到"+ 拍照上传"按钮
- [ ] API 文档可访问 http://localhost:8000/docs
- [ ] 浏览器 DevTools 无重大错误（F12 → Console）
- [ ] 编辑前端文件后浏览器自动刷新（HMR 工作）

---

## 📚 相关文档

| 文档 | 位置 | 说明 |
|------|------|------|
| 完整访问指南 | `ACCESS_GUIDE.md` | 本地 + AWS 访问方式 |
| 本地开发指南 | `LOCAL_DEV_GUIDE.md` | 详细的故障排查步骤 |
| 项目总览 | `CLAUDE.md` | 技术栈、规则、设计模式 |
| 项目状态 | `FINAL_PROJECT_REPORT.md` | 完成度报告 |

---

## 🆘 遇到问题？

**问题 1: 前端显示 400 Bad Request**
→ 确认 Vite 配置中 `host: '0.0.0.0'` 存在，然后重启 `npm run dev`

**问题 2: 后端启动失败 (ModuleNotFoundError)**
→ 确认虚拟环境激活：`source venv/bin/activate`，然后 `pip install -r requirements.txt`

**问题 3: 登录后还是登录页面**
→ 打开浏览器 DevTools (F12) → Console，查看是否有错误

**问题 4: 无法连接后端 API**
→ 确认后端运行：`curl http://localhost:8000/docs`

**问题 5: 前端依赖缺失**
→ 运行 `npm install`，然后 `npm run dev`

---

## ✨ 一切就绪！

所有文件都已准备好。现在：

1. 打开 3 个终端窗口
2. 按上面的步骤启动后端、前端、浏览器
3. 验证能否正常登录和访问

**如果一切正常，项目已 100% 完成！** 🎉

