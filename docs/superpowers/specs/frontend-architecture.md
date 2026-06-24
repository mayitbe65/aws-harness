# 错题宝前端架构设计

**日期**：2026-06-24  
**状态**：架构设计  
**目标**：React 18 + TypeScript 5 前端，对应四个核心后端功能

---

## 目录

1. [概述](#概述)
2. [前端四大功能模块](#前端四大功能模块)
3. [应用架构](#应用架构)
4. [状态管理](#状态管理)
5. [页面和组件](#页面和组件)
6. [API 客户端设计](#api-客户端设计)
7. [工作流程](#工作流程)
8. [技术栈选择](#技术栈选择)

---

## 概述

前端分四个核心模块，与后端对应：

| 后端模块 | 前端页面 | 关键功能 |
|---------|---------|---------|
| **E 认证** | Login / Register | JWT token 管理、用户会话 |
| **C 题目存储** | Dashboard / QuestionList | 题目上传、列表、编辑、删除 |
| **A 拍照识别** | PhotoUpload | 拍照、图片上传、识别预览、质量检查 |
| **B 推荐计划** | ReviewPlan | 推荐列表、标记复习、学习统计 |
| **D 文档导出** | Export | 选题、导出设置、下载 PDF |

---

## 前端四大功能模块

### 模块 1：认证系统（E - Authentication）

**页面：** `Login.tsx`  
**职责：** JWT token 获取、用户会话管理、路由保护

**流程：**
```
用户输入邮箱/密码 → 调用 POST /api/auth/login → 获得 JWT token → 存储 localStorage → 重定向到 Dashboard
```

**实现细节：**
- JWT token 存储在 `localStorage` 中，键名 `auth_token`
- API 请求自动添加 `Authorization: Bearer {token}` header
- Token 过期时自动清除，重定向到登录页
- 支持自动刷新（如果后端实现 refresh token）

**相关 Hooks：**
- `useAuth()` — 获取当前用户和登出函数
- `useAuthGuard()` — 保护需要认证的路由

---

### 模块 2：题目管理（C - Question Storage）

**页面：** `Dashboard.tsx` (列表) + `QuestionDetail.tsx` (编辑)  
**职责：** 题目 CRUD、多维度查询、用户隔离验证

**功能清单：**

1. **题目列表页**
   - 分页显示（默认 20/页）
   - 筛选：全部 / 需审核 / 按科目
   - 排序：最新 / 最常错 / 难度
   - 快速操作：编辑、删除、导出单题

2. **题目详情页**
   - 显示原始照片 + OCR 结果
   - 编辑识别文本（手动纠正）
   - 修改科目、难度、标签
   - 标记是否需审核 + 审核备注
   - 删除题目（确认对话框）

3. **拍照上传**（内嵌模块）
   - 手机摄像头 / 文件选择
   - 图片预览 + 裁剪（可选）
   - 上传进度显示
   - 上传成功后自动跳转到识别页

**相关 Hooks：**
- `useQuestions()` — 列表查询、分页、筛选
- `useQuestion(id)` — 单个题目详情
- `useCreateQuestion()` — 上传并创建
- `useUpdateQuestion(id)` — 保存编辑
- `useDeleteQuestion(id)` — 删除

---

### 模块 3：拍照识别（A - Photo Recognition）

**页面：** `PhotoUpload.tsx`  
**职责：** 调用 Vision API、显示识别结果、质量检查提示

**流程：**
```
1. 用户拍照/选图 → 
2. 前端上传到后端 → 
3. 后端调用 Vision API 识别 → 
4. 返回识别结果（text + confidence） →
5. 前端判断质量
   - confidence ≥ 0.7：绿色√，自动提交
   - 0.5 ≤ confidence < 0.7：黄色⚠，提示"识别质量一般，需手动纠正"
   - confidence < 0.5：红色✗，提示"识别失败，建议重拍或手动输入"
6. 用户可手动编辑识别结果 → 确认保存
```

**识别质量指示：**
```tsx
// 类型
type RecognitionQuality = "high" | "medium" | "low"

// 显示规则
const quality = (confidence: number): RecognitionQuality => {
  if (confidence >= 0.7) return "high"   // ✓ 识别质量高
  if (confidence >= 0.5) return "medium" // ⚠ 需人工审核
  return "low"                           // ✗ 识别失败
}
```

**相关 Hooks：**
- `usePhotoUpload()` — 文件上传、进度追踪
- `useRecognition()` — 调用识别端点、轮询状态

---

### 模块 4：推荐计划（B - Recommendation）

**页面：** `ReviewPlan.tsx`  
**职责**： 显示推荐列表、标记复习、学习统计

**功能清单：**

1. **推荐列表**
   - 按优先级排序展示 10 题
   - 显示：题目预览、错误次数、上次复习时间、下次推荐时间
   - 操作：开始复习（模态框）、查看详情、标记已掌握

2. **复习模态框**
   - 显示题目内容 + 照片
   - 用户选择：✓ 做对 / ✗ 做错
   - 点击确认后，后端更新 ReviewPlan（下次复习时间）
   - 自动跳到下一题

3. **学习统计面板**
   - 今日复习数、周学习量
   - 掌握度曲线（按科目）
   - 常错题目 Top 5

**算法可视化：**
```
优先级 = 0.4 * (错误次数 / 总错次) + 0.4 * 遗忘度 + 0.2 * (难度 / 5)

遗忘度 = min(1.0, 天数 / 复习周期)
复习周期 = [1, 3, 7, 15, 30] 天（按复习次数递增）
```

**相关 Hooks：**
- `useRecommendations()` — 获取推荐列表（Redis 缓存）
- `useMarkReviewed()` — 标记复习状态
- `useStudyStats()` — 获取统计数据

---

### 模块 5：文档导出（D - Export）

**页面：** `Export.tsx`  
**职责**：选题、生成快照、下载 PDF

**流程：**
```
1. 用户选择题目（多选）或选择导出范围
2. 选择导出格式：PDF / HTML 可打印版
3. 选择排版方式：按科目 / 按难度
4. 点击"生成" → 后端生成快照 + PDF
5. 前端显示下载进度
6. 用户点击下载，浏览器下载 PDF 文件
```

**导出选项：**
```tsx
interface ExportOptions {
  questionIds: string[]        // 选中题目
  format: "pdf" | "html"      // 导出格式
  groupBy: "subject" | "difficulty" | "none" // 分组方式
  includeAnswers: boolean      // 是否包含答案
  pageSize: "A4" | "letter"   // 页面尺寸
}
```

**相关 Hooks：**
- `useExport()` — 发起导出请求
- `useExportHistory()` — 查看导出历史
- `useExportDownload(snapshotId)` — 下载文件

---

## 应用架构

### 目录结构

```
frontend/
├── src/
│   ├── pages/
│   │   ├── Login.tsx              # 登录页
│   │   ├── Dashboard.tsx          # 题目列表 + 操作
│   │   ├── QuestionDetail.tsx     # 题目编辑
│   │   ├── PhotoUpload.tsx        # 拍照识别
│   │   ├── ReviewPlan.tsx         # 推荐列表 + 复习
│   │   ├── StudyStats.tsx         # 学习统计
│   │   ├── Export.tsx             # 导出功能
│   │   ├── NotFound.tsx           # 404
│   │   └── Layout.tsx             # 主布局
│   │
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── Header.tsx         # 导航栏 + 用户菜单
│   │   │   ├── Sidebar.tsx        # 侧边栏导航
│   │   │   └── Footer.tsx         # 页脚
│   │   ├── Question/
│   │   │   ├── QuestionCard.tsx   # 题目卡片
│   │   │   ├── QuestionForm.tsx   # 题目编辑表单
│   │   │   ├── QuestionFilters.tsx# 筛选器
│   │   │   └── QuestionModal.tsx  # 查看详情模态框
│   │   ├── Photo/
│   │   │   ├── PhotoInput.tsx     # 相机 / 文件上传
│   │   │   ├── PhotoPreview.tsx   # 图片预览
│   │   │   ├── RecognitionResult.tsx # 识别结果展示
│   │   │   └── QualityIndicator.tsx  # 质量指示器
│   │   ├── Recommendation/
│   │   │   ├── RecommendList.tsx  # 推荐列表
│   │   │   ├── ReviewCard.tsx     # 单个复习卡片
│   │   │   ├── ReviewModal.tsx    # 复习模态框
│   │   │   └── StudyStatsPanel.tsx # 统计面板
│   │   ├── Export/
│   │   │   ├── ExportForm.tsx     # 导出选项表单
│   │   │   ├── ExportProgress.tsx # 导出进度
│   │   │   └── ExportHistory.tsx  # 历史下载
│   │   ├── Common/
│   │   │   ├── LoadingSpinner.tsx # 加载指示
│   │   │   ├── ErrorAlert.tsx     # 错误提示
│   │   │   ├── SuccessToast.tsx   # 成功通知
│   │   │   ├── ConfirmDialog.tsx  # 确认对话框
│   │   │   └── Pagination.tsx     # 分页器
│   │   └── ErrorBoundary.tsx      # 错误捕获
│   │
│   ├── hooks/
│   │   ├── useAuth.ts             # 认证状态 + 登出
│   │   ├── useAuthGuard.ts        # 路由保护
│   │   ├── useQuestions.ts        # 题目列表 + CRUD
│   │   ├── useQuestion.ts         # 单个题目
│   │   ├── usePhotoUpload.ts      # 上传 + 进度
│   │   ├── useRecognition.ts      # 识别状态轮询
│   │   ├── useRecommendations.ts  # 推荐列表
│   │   ├── useMarkReviewed.ts     # 标记复习
│   │   ├── useExport.ts           # 导出请求
│   │   ├── usePagination.ts       # 分页状态
│   │   ├── useDebounce.ts         # 防抖
│   │   └── useLocalStorage.ts     # localStorage 封装
│   │
│   ├── context/
│   │   ├── AuthContext.tsx        # 用户认证状态（JWT）
│   │   ├── AppContext.tsx         # 全局应用状态（通知、加载）
│   │   └── index.ts               # Provider 导出
│   │
│   ├── services/
│   │   ├── api.ts                 # Axios 客户端（自动 JWT header）
│   │   ├── storage.ts             # localStorage 操作
│   │   ├── question.ts            # 题目 API 调用
│   │   ├── recognition.ts         # 识别 API 调用
│   │   ├── recommendation.ts      # 推荐 API 调用
│   │   └── export.ts              # 导出 API 调用
│   │
│   ├── types/
│   │   ├── api.ts                 # API 请求 / 响应类型
│   │   ├── models.ts              # 数据模型类型
│   │   ├── components.ts          # 组件 props 类型
│   │   └── index.ts               # 类型导出
│   │
│   ├── utils/
│   │   ├── validators.ts          # 表单验证
│   │   ├── formatters.ts          # 数据格式化（日期、数字）
│   │   ├── constants.ts           # 常量定义
│   │   └── errors.ts              # 错误处理工具
│   │
│   ├── styles/
│   │   ├── globals.css            # 全局样式
│   │   ├── variables.css          # CSS 变量
│   │   ├── Layout.module.css      # CSS Modules
│   │   └── ...（按需）
│   │
│   ├── App.tsx                    # 主应用 + 路由定义
│   ├── main.tsx                   # React 入口
│   └── vite-env.d.ts              # Vite 类型声明
│
├── public/                        # 静态资源
│   ├── favicon.ico
│   └── logo.png
│
├── tests/
│   ├── unit/                      # 单元测试
│   └── integration/               # 集成测试
│
├── package.json
├── tsconfig.json                  # TypeScript 配置（strict: true）
├── vite.config.ts
├── vitest.config.ts
├── eslint.config.js
└── .prettierrc
```

---

## 状态管理

### 设计原则
- **Context API** 用于全局状态：认证、通知、应用设置
- **自定义 Hooks** 用于业务逻辑：CRUD、分页、过滤
- **局部状态** 用于 UI 状态：模态框开闭、表单值

### 全局状态

#### AuthContext
```tsx
interface AuthContextType {
  currentUser: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
}

// 使用
const { currentUser, isAuthenticated, logout } = useAuth()
```

#### AppContext
```tsx
interface AppContextType {
  notification: {
    type: "success" | "error" | "info" | "warning"
    message: string
    visible: boolean
  }
  showNotification: (type, message) => void
  hideNotification: () => void
  isLoading: boolean
  setIsLoading: (bool) => void
}

// 使用
const { notification, showNotification } = useApp()
showNotification("success", "题目已保存")
```

### 自定义 Hooks 示例

#### useQuestions (列表 + 分页 + 筛选)
```tsx
interface UseQuestionsOptions {
  page?: number
  pageSize?: number
  subject?: string
  needsReviewOnly?: boolean
}

function useQuestions(options: UseQuestionsOptions) {
  const [questions, setQuestions] = useState([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await api.get("/api/questions", { params: options })
      setQuestions(response.data.items)
      setTotal(response.data.total)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }, [options])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { questions, total, isLoading, error, refetch: fetch }
}
```

#### useRecognition (轮询识别状态)
```tsx
function useRecognition(taskId: string) {
  const [status, setStatus] = useState<"pending" | "completed" | "failed">("pending")
  const [result, setResult] = useState(null)

  useEffect(() => {
    if (!taskId) return

    const interval = setInterval(async () => {
      try {
        const response = await api.get(`/api/recognition/task/${taskId}`)
        setStatus(response.data.status)
        if (response.data.status === "completed") {
          setResult(response.data.result)
          clearInterval(interval)
        }
      } catch (err) {
        setStatus("failed")
        clearInterval(interval)
      }
    }, 1000) // 每秒轮询

    return () => clearInterval(interval)
  }, [taskId])

  return { status, result }
}
```

---

## 页面和组件

### 页面路由

```tsx
// App.tsx
<BrowserRouter>
  <Routes>
    <Route path="/login" element={<Login />} />
    <Route element={<ProtectedLayout />}>
      <Route path="/" element={<Dashboard />} />
      <Route path="/question/:id" element={<QuestionDetail />} />
      <Route path="/upload" element={<PhotoUpload />} />
      <Route path="/review" element={<ReviewPlan />} />
      <Route path="/stats" element={<StudyStats />} />
      <Route path="/export" element={<Export />} />
      <Route path="*" element={<NotFound />} />
    </Route>
  </Routes>
</BrowserRouter>
```

### 关键组件

#### QuestionCard（题目卡片）
```tsx
interface QuestionCardProps {
  question: Question
  onEdit: (id: string) => void
  onDelete: (id: string) => Promise<void>
  showPreview?: boolean
}

export function QuestionCard({ question, onEdit, onDelete, showPreview }: QuestionCardProps) {
  return (
    <div className={styles.card}>
      {showPreview && <img src={question.photoUrl} alt="preview" />}
      <h3>{question.recognizedText.substring(0, 50)}...</h3>
      <p>难度: {question.difficulty} | 科目: {question.subject}</p>
      {question.needsReview && <span className={styles.badge}>需审核</span>}
      <div className={styles.actions}>
        <button onClick={() => onEdit(question.questionId)}>编辑</button>
        <button onClick={() => onDelete(question.questionId)}>删除</button>
      </div>
    </div>
  )
}
```

#### RecognitionResult（识别结果展示）
```tsx
interface RecognitionResultProps {
  confidence: number
  recognizedText: string
  photoUrl: string
  onConfirm: (text: string) => void
  onEdit: (text: string) => void
}

export function RecognitionResult({ confidence, recognizedText, photoUrl, onConfirm, onEdit }: RecognitionResultProps) {
  const quality = confidence >= 0.7 ? "high" : confidence >= 0.5 ? "medium" : "low"

  return (
    <div>
      <img src={photoUrl} alt="uploaded" />
      <QualityIndicator quality={quality} confidence={confidence} />
      <textarea value={recognizedText} onChange={(e) => onEdit(e.target.value)} />
      <button onClick={() => onConfirm(recognizedText)}>确认保存</button>
    </div>
  )
}
```

#### ReviewModal（复习模态框）
```tsx
interface ReviewModalProps {
  question: Question
  onReviewComplete: (passed: boolean) => void
  onClose: () => void
}

export function ReviewModal({ question, onReviewComplete, onClose }: ReviewModalProps) {
  return (
    <Modal open onClose={onClose}>
      <div className={styles.reviewContent}>
        <img src={question.photoUrl} alt="question" />
        <p>{question.recognizedText}</p>
        <div className={styles.actions}>
          <button onClick={() => onReviewComplete(true)} className={styles.correct}>
            ✓ 做对了
          </button>
          <button onClick={() => onReviewComplete(false)} className={styles.wrong}>
            ✗ 做错了
          </button>
        </div>
      </div>
    </Modal>
  )
}
```

---

## API 客户端设计

### Axios 实例配置

```tsx
// services/api.ts
import axios from "axios"
import { useAuth } from "@/hooks/useAuth"

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
})

// 请求拦截：自动添加 JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：处理 401（token 过期）
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("auth_token")
      window.location.href = "/login"
    }
    return Promise.reject(error)
  }
)
```

### API 服务函数

```tsx
// services/question.ts
export const questionAPI = {
  list: (page: number, pageSize: number, filters?: any) =>
    api.get("/api/questions", { params: { page, page_size: pageSize, ...filters } }),

  get: (questionId: string) =>
    api.get(`/api/questions/${questionId}`),

  create: (data: CreateQuestionRequest) =>
    api.post("/api/questions/create", data),

  update: (questionId: string, data: UpdateQuestionRequest) =>
    api.put(`/api/questions/${questionId}`, data),

  delete: (questionId: string) =>
    api.delete(`/api/questions/${questionId}`),
}
```

---

## 工作流程

### 1. 用户登录 → 上传 → 识别 → 保存

```
LoginPage 
  ↓ (输入邮箱/密码) 
  ↓ (调用 POST /api/auth/login)
AuthContext.login() — 保存 JWT token
  ↓ 
Dashboard (自动跳转)
  ↓ (点击上传)
PhotoUpload
  ↓ (选择图片、点击上传)
  ↓ (调用 POST /api/recognition/upload)
RecognitionResult (显示识别结果 + 质量指示)
  ↓ (用户编辑文本、点击确认)
  ↓ (调用 POST /api/questions/create)
QuestionCard (显示在 Dashboard)
```

### 2. 推荐复习流程

```
Dashboard 
  ↓ (点击"开始复习")
ReviewPlan (显示推荐列表，按优先级排序)
  ↓ (点击题目，打开 ReviewModal)
ReviewModal (显示题目，用户选择做对/做错)
  ↓ (点击"做对了")
  ↓ (调用 POST /api/recommendations/mark-reviewed)
ReviewPlan (自动刷新，显示下一题)
```

### 3. 导出 PDF 流程

```
Dashboard
  ↓ (点击"导出")
Export (选择题目、格式、排版方式)
  ↓ (点击"生成")
  ↓ (调用 POST /api/export/pdf)
ExportProgress (显示进度，轮询状态)
  ↓ (完成后)
  ↓ (调用 GET /api/export/{snapshotId} 下载)
浏览器下载 PDF 文件
```

---

## 技术栈选择

| 技术 | 选项 | 理由 |
|------|------|------|
| 框架 | React 18 | 组件化、虚拟 DOM、大生态 |
| 语言 | TypeScript 5 | 类型安全、开发体验好 |
| 状态 | Context API + Hooks | 轻量、适配小-中型应用 |
| 路由 | React Router 6 | 标准路由库、支持嵌套 |
| HTTP | Axios | 简洁、支持拦截器 |
| 构建 | Vite 5 | 快速开发、极速构建 |
| 样式 | CSS Modules / Tailwind | 隔离 + 可维护（择一） |
| 组件库 | 自定义或 Ant Design | 灵活性 vs 快速上手 |
| 测试 | Vitest + React Testing Library | 单元测试覆盖 > 70% |
| 类型检查 | TypeScript strict mode | 零容忍类型错误 |

---

## 开发检查清单

### 认证模块
- [ ] Login 页面可正常登录
- [ ] JWT token 存储到 localStorage
- [ ] 未认证用户无法访问保护路由
- [ ] Token 过期时自动重定向到登录

### 题目管理
- [ ] 题目列表可正常显示和分页
- [ ] 题目编辑表单可保存修改
- [ ] 删除题目需要确认
- [ ] 用户 A 无法访问用户 B 的题目（R1 隔离验证）

### 拍照识别
- [ ] 图片上传成功
- [ ] 识别结果正确展示
- [ ] 质量指示器工作正常（高/中/低）
- [ ] 用户可编辑识别文本

### 推荐复习
- [ ] 推荐列表按优先级排序
- [ ] 标记复习后，NextReviewTime 更新
- [ ] 学习统计数据正确

### 导出功能
- [ ] 选题后可生成 PDF
- [ ] 下载 PDF 文件正常

### 代码质量
- [ ] TypeScript 严格模式无错误
- [ ] ESLint 检查通过
- [ ] Prettier 格式化一致
- [ ] 单元测试覆盖 > 70%

---

**下一步：** 根据此架构生成前端实现计划（前端分为 5 个 Phase，每 Phase 对应一个后端模块）
