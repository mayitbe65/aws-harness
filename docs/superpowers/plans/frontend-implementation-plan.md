# 前端实现计划（React + TypeScript）

> **For agentic workers:** Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.
> **版本**：1.0（前端五大 Phase，与后端并行）

**Goal:** 实现 React 18 + TypeScript 5 前端，与后端 API 对接，支持四个核心功能。

**Architecture:**
- 前端框架：React 18 + TypeScript 5 (strict mode)
- 构建工具：Vite 5
- 路由：React Router 6
- 状态管理：Context API + Custom Hooks
- HTTP 客户端：Axios (自动 JWT header)
- 样式：CSS Modules + Tailwind CSS
- 测试：Vitest + React Testing Library

**Tech Stack:**
```
React 18.x + TypeScript 5.x
Vite 5.x (dev server + build)
Axios (HTTP)
React Router 6.x
Context API (state)
CSS Modules (styles)
Vitest + RTL (testing)
```

---

## 前端五大 Phase

| Phase | 名称 | 页面 | 关键 Hook | 状态 |
|-------|------|------|----------|------|
| **F1** | 认证（E） | Login | useAuth, useAuthGuard | ⏳ 本次启动 |
| **F2** | 题目管理（C） | Dashboard, QuestionDetail | useQuestions, useQuestion | ⏳ 后续 |
| **F3** | 拍照识别（A） | PhotoUpload | usePhotoUpload, useRecognition | ⏳ 后续 |
| **F4** | 推荐复习（B） | ReviewPlan, StudyStats | useRecommendations, useMarkReviewed | ⏳ 后续 |
| **F5** | 文档导出（D） | Export | useExport | ⏳ 后续 |

---

## Phase F1: 认证系统（Login）

### Task F1.1: 项目初始化与依赖

**Files:**
- Create: `frontend/package.json` — 依赖清单
- Create: `frontend/tsconfig.json` — TypeScript strict mode
- Create: `frontend/vite.config.ts` — Vite 配置
- Create: `frontend/src/types/api.ts` — API 类型定义
- Create: `frontend/src/types/models.ts` — 数据模型类型

**关键依赖：**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.16.0",
    "axios": "^1.5.0"
  },
  "devDependencies": {
    "typescript": "^5.2.0",
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "vitest": "^0.34.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.1.0"
  }
}
```

**Commands:**
```bash
npm install
npm run dev        # Vite dev server
npm run build      # Production build
npm run test       # Run tests
npm run type-check # TypeScript check
```

---

### Task F1.2: API 类型定义与 Axios 配置

**Files:**
- Create: `frontend/src/types/api.ts` — API 请求/响应类型
- Create: `frontend/src/types/models.ts` — 数据模型（User, Question, ReviewPlan）
- Create: `frontend/src/services/api.ts` — Axios 实例 + 拦截器

**核心类型：**
```typescript
// api.ts
interface LoginRequest {
  email: string
  password: string
}

interface LoginResponse {
  access_token: string
  token_type: string
  user_id: string
  role: string
  expires_in: number
}

// models.ts
interface User {
  user_id: string
  email: string
  name: string
  role: "admin" | "student"
  created_at: string
}
```

**Axios 配置要点：**
- baseURL: `http://localhost:8000` (开发)
- 请求拦截器：添加 `Authorization: Bearer {token}` header
- 响应拦截器：401 时清除 token 并重定向到登录

---

### Task F1.3: AuthContext 与认证状态管理

**Files:**
- Create: `frontend/src/context/AuthContext.tsx` — 全局认证状态
- Create: `frontend/src/hooks/useAuth.ts` — 认证 hook
- Create: `frontend/src/utils/storage.ts` — localStorage 封装

**AuthContext 职责：**
```typescript
interface AuthContextType {
  currentUser: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  error: string | null
}
```

**工作流：**
1. 页面加载时，从 localStorage 恢复 token（如果存在）
2. login() 调用 API → 保存 token 到 localStorage + AuthContext
3. logout() 清除 token 和用户状态
4. 组件通过 useAuth() 获取当前用户

---

### Task F1.4: Login 页面实现

**Files:**
- Create: `frontend/src/pages/Login.tsx` — 登录页面组件
- Create: `frontend/src/components/Common/LoadingSpinner.tsx` — 加载指示
- Create: `frontend/src/components/Common/ErrorAlert.tsx` — 错误提示
- Create: `frontend/src/styles/Login.module.css` — 登录页样式

**Login 页面功能：**
- 邮箱 + 密码表单
- 表单验证（邮箱格式、密码长度）
- 登录按钮 → 调用 AuthContext.login()
- 成功后自动跳转到 Dashboard
- 失败时显示错误信息
- 加载中显示 spinner

**页面布局：**
```
┌─────────────────────────────┐
│      错题宝智能学习          │
├─────────────────────────────┤
│  邮箱: [_____________]      │
│  密码: [_____________]      │
│  [登录] [还没有账号？]       │
└─────────────────────────────┘
```

---

### Task F1.5: 路由保护与应用初始化

**Files:**
- Create: `frontend/src/App.tsx` — 主应用 + 路由定义
- Create: `frontend/src/main.tsx` — React 入口
- Create: `frontend/src/components/ProtectedRoute.tsx` — 路由保护组件
- Create: `frontend/src/pages/NotFound.tsx` — 404 页面

**路由结构：**
```typescript
<BrowserRouter>
  <Routes>
    <Route path="/login" element={<Login />} />
    <Route element={<ProtectedLayout />}>
      <Route path="/" element={<Dashboard />} />
      <Route path="/question/:id" element={<QuestionDetail />} />
      <Route path="/upload" element={<PhotoUpload />} />
      <Route path="/review" element={<ReviewPlan />} />
      <Route path="/export" element={<Export />} />
      <Route path="*" element={<NotFound />} />
    </Route>
  </Routes>
</BrowserRouter>
```

**ProtectedRoute 逻辑：**
- 检查 isAuthenticated
- 未认证时重定向到 /login
- 认证后显示受保护的布局

---

### Task F1.6: Login 单元测试

**Files:**
- Create: `frontend/src/__tests__/pages/Login.test.tsx` — Login 页面测试
- Create: `frontend/src/__tests__/hooks/useAuth.test.ts` — useAuth hook 测试
- Create: `frontend/src/__tests__/services/api.test.ts` — API 拦截器测试

**测试覆盖：**
- Login 表单渲染
- 表单验证（邮箱、密码）
- 成功登录流程
- 失败登录处理
- Token 持久化（localStorage）
- 路由保护（未认证时重定向）

---

## 总体进度清单

### Phase F1: 认证（本次）
- [ ] F1.1: 项目初始化
- [ ] F1.2: API 类型 + Axios
- [ ] F1.3: AuthContext + useAuth
- [ ] F1.4: Login 页面
- [ ] F1.5: 路由保护 + App
- [ ] F1.6: 单元测试

### Phase F2-F5: 后续
- [ ] F2: Dashboard + 题目列表
- [ ] F3: PhotoUpload + 识别预览
- [ ] F4: ReviewPlan + 推荐
- [ ] F5: Export + PDF 下载

---

## 开发检查清单（Phase F1）

- [ ] TypeScript strict mode 无错误
- [ ] ESLint 检查通过
- [ ] Prettier 格式化一致
- [ ] Login 页面可正常登录
- [ ] 成功登录后跳转到 Dashboard
- [ ] Token 正确存储到 localStorage
- [ ] 刷新页面后认证状态保持
- [ ] 登出后清除 token，重定向到登录
- [ ] 未认证用户无法访问受保护页面
- [ ] 所有单元测试通过（> 70% 覆盖率）

---

**下一步：** 执行 Task F1.1-F1.4（项目初始化到 Login 页面实现）
