# 错题宝 — 需求说明文档

**版本**：1.0  
**日期**：2026-06-24  
**状态**：确认

---

## 目录

1. [项目背景](#项目背景)
2. [用户角色](#用户角色)
3. [核心功能需求](#核心功能需求)
4. [业务规则与约束](#业务规则与约束)
5. [数据需求](#数据需求)
6. [接口需求](#接口需求)
7. [非功能性需求](#非功能性需求)
8. [技术栈约束](#技术栈约束)

---

## 项目背景

**错题宝**是面向学校/班级的智能学习系统，帮助学生高效管理和复习错题。

核心流程：
```
📸 拍照上传 → 🤖 AI 识别 → 💾 数字化存储 → 📚 智能推荐 → 📄 文档导出
```

---

## 用户角色

| 角色 | 说明 | 注册方式 |
|------|------|----------|
| **student（学生）** | 上传错题、查看自己的题目和推荐、导出文档 | 管理员手动创建，确保真实性 |
| **admin（管理员）** | 查看全部学生数据汇总、班级管理（后期功能） | 系统初始化时创建 |

**权限矩阵**：

| 操作 | 学生 | 管理员 |
|------|------|--------|
| 登录 | ✅ | ✅ |
| 查看/编辑/删除自己的题目 | ✅ | ❌ |
| 查看全部题目 | ❌ | ✅ |
| 查看自己的推荐计划 | ✅ | ❌ |
| 查看全部学生数据 | ❌ | ✅（后期） |

---

## 核心功能需求

### FR-1 用户认证

- **FR-1.1** 邮箱 + 密码登录，返回 JWT token（有效期 1 小时）
- **FR-1.2** 登出时前端删除 token，后端无状态
- **FR-1.3** 敏感操作（删除题目、导出文档）前需再次验证密码
- **FR-1.4** 密码需满足：8+ 字符，包含大小写字母和数字
- **FR-1.5** 登录失败不区分"邮箱不存在"和"密码错误"，统一返回 401（防用户枚举）

---

### FR-2 拍照识别错题（三天主线，优先级最高）

- **FR-2.1** 学生上传图片 URL，后端调用 Google Vision API 识别题目文本
- **FR-2.2** 识别结果分三级质量：
  - confidence ≥ 0.7：高质量，直接存储
  - 0.5 ≤ confidence < 0.7：中等质量，标记需人工审核
  - confidence < 0.5：低质量，自动重试最多 3 次（间隔 1s / 2s / 4s）
- **FR-2.3** Vision API 返回格式校验：
  - 缺少 `confidence` 字段时按 0 处理
  - `confidence` 超出 [0,1] 范围时按 0 处理
  - 空文本、文本长度 < 5 或 > 10000、纯符号、"[无法识别]" 均标记为需人工审核
- **FR-2.4** 3 次重试仍失败时，仍创建题目记录（`recognized_text` = "[识别失败，请重新上传或手动输入]"），标记需人工审核
- **FR-2.5** 学生可手动编辑识别错误的题目文本；编辑后自动清除"需人工审核"标记
- **FR-2.6** 学生可对需审核的题目发起重新识别
- **FR-2.7** Vision API 调用必须通过后端代理，前端不得暴露 API 密钥

---

### FR-3 数字化题目管理（存储）

- **FR-3.1** 题目按科目、知识点、难度（1–5）分类管理
- **FR-3.2** 支持多维度查询：按科目、知识点、难度过滤，支持分页
- **FR-3.3** 每条题目记录包含：原始图片 URL、识别文本、科目、难度、知识点、标准答案、错误原因、置信度、审核状态
- **FR-3.4** 删除题目为敏感操作，需要密码验证
- **FR-3.5** 用户删除时，其所有题目及关联数据级联删除
- **FR-3.6** 提供题目统计接口：按科目、难度分类汇总，显示待审核数量

**数据隔离（强制）**：学生只能查看、编辑、删除自己的题目；所有查询必须加 `WHERE user_id = current_user_id`。

---

### FR-4 智能复习推荐（艾宾浩斯遗忘曲线）

- **FR-4.1** 基于以下三个因子计算复习优先级：
  ```
  priority = 0.4 × error_freq + 0.4 × spaced_repetition_score + 0.2 × difficulty_factor
  ```
- **FR-4.2** 遗忘曲线复习间隔规划（按复习次数）：

  | 复习次数 | 下次间隔 |
  |----------|---------|
  | 0（首次出错） | 1 天后 |
  | 1 | 3 天后 |
  | 2 | 7 天后 |
  | 3 | 15 天后 |
  | 4+ | 30 天后 |

- **FR-4.3** 学生可标记题目"已复习"或"再次出错"，系统据此更新下次复习时间和优先级
- **FR-4.4** 推荐计划结果缓存 1 小时（Redis），编辑题目或标记复习后立即清除对应用户的缓存
- **FR-4.5** 仅 `needs_review = false` 的题目进入推荐计划
- **FR-4.6** 推荐计算操作需事务保护，防止并发导致数据不一致

---

### FR-5 文档导出（打印）

- **FR-5.1** 导出前先创建快照，冻结题目当前状态；快照保留 30 天
- **FR-5.2** 快照生成后，即使原题目被编辑或删除，已冻结的数据不变
- **FR-5.3** 支持按"科目"或"知识点"分节组织题目
- **FR-5.4** 支持导出为 PDF 格式；可选支持 Word (.docx)
- **FR-5.5** 导出文档上传至云存储（S3/CDN），返回下载链接，有效期 60 天
- **FR-5.6** 用户可查看历史导出记录

---

## 业务规则与约束

### 强制规则（MUST — 违反即停止）

| 编号 | 规则 | 说明 |
|------|------|------|
| R1 | 用户数据隔离 | 所有查询加 `WHERE user_id=current`，学生只能访问自己的数据 |
| R2 | Vision API 返回格式校验 | 缺 `confidence` 按 0 处理，验证范围 [0,1] |
| R3 | API 密钥代理 | Vision API、数据库连接等所有敏感密钥只在后端，不暴露给前端 |
| R4 | 识别质量强制检查 | 低质量结果必须标记 `needs_review=true` 并说明原因 |
| R5 | 写操作事务保护 | 所有数据库写操作（创建题目、推荐计算、标记复习）在事务内执行 |
| R6 | 缓存 key 含 userId | Redis key 格式：`recommendation:user:{user_id}:plan`，防止用户数据混乱 |
| R7 | 推荐算法必须有单元测试 | 核心业务逻辑不能缺测试，覆盖率 > 80% |
| R8 | Vision API 失败自动重试 | confidence < 0.5 时重试 3 次，间隔 1s/2s/4s |
| R9 | 导出使用快照机制 | 导出时冻结题目状态，不直接查询题目表 |
| — | 敏感操作密码确认 | 删除题目、导出文档必须重新验证用户密码 |
| — | 不提交敏感信息到 Git | `.env` 文件、API 密钥、用户数据不得出现在 git 记录中 |

### 强烈建议规则（SHOULD）

- Vision API 识别准确率 > 95% 后才上线
- 提供用户手动纠正识别错误的界面
- 推荐算法变更需在灰度环境验证 24+ 小时
- 数据库迁移前备份，准备回滚方案
- AI 识别相关代码、推荐算法、数据模型变更需 code review

---

## 数据需求

### 核心实体

**User（用户）**
- `user_id`（UUID）、`email`（唯一）、`password_hash`（bcrypt）
- `role`（admin / student）、`name`、`created_at`、`updated_at`

**Question（错题）**
- `question_id`（UUID）、`user_id`（外键，级联删除）
- `image_url`、`recognized_text`、`subject`、`difficulty`（1–5）
- `knowledge_point`、`correct_answer`、`error_reason`
- `needs_review`（bool）、`confidence`（0–1）
- `created_at`、`updated_at`

**ReviewPlan（复习计划）**
- `plan_id`（UUID）、`question_id`（外键）、`user_id`（外键）
- `priority`（0–1）、`next_review_time`
- `error_count`、`last_error_time`、`reviewed_count`、`last_reviewed_time`
- 仅对 `needs_review=false` 的题目创建

**Snapshot（导出快照）**
- `snapshot_id`（UUID）、`user_id`（外键）
- `question_ids`（JSON 数组）、`snapshot_data`（JSON，冻结的题目内容）
- `format`（pdf / word）、`organize_by`（subject / knowledge_point）
- `created_at`、`expires_at`（30 天后过期）

**ExportDocument（导出文档）**
- `document_id`（UUID）、`user_id`（外键）、`snapshot_id`（外键）
- `format`、`file_url`（S3/CDN 链接）、`file_size_bytes`
- `generated_at`、`expires_at`（60 天后过期）

### 关系
- User → Question（一对多，级联删除）
- Question → ReviewPlan（一对一，级联删除）
- User → Snapshot（一对多，级联删除）
- Snapshot → ExportDocument（一对多，级联删除）

---

## 接口需求

### 认证模块 `/api/auth`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录，返回 JWT token |
| POST | `/api/auth/logout` | 登出（前端清除 token） |
| POST | `/api/auth/verify-password` | 验证密码（敏感操作前调用） |

### 题目管理 `/api/questions`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/questions` | 列表查询（支持科目、知识点、难度过滤，分页） |
| POST | `/api/questions` | 创建题目 |
| GET | `/api/questions/{id}` | 获取单题详情 |
| PUT | `/api/questions/{id}` | 编辑题目 |
| DELETE | `/api/questions/{id}` | 删除题目（需密码验证） |
| GET | `/api/questions/stats` | 题目统计 |

### 识别模块 `/api/recognition`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/recognition/recognize` | 上传并识别题目（同步，2–5 秒） |
| POST | `/api/recognition/retry/{id}` | 对已有题目重新识别 |

### 推荐模块 `/api/recommendations`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/recommendations/plan` | 获取推荐复习计划（按优先级排序） |
| POST | `/api/recommendations/mark-reviewed/{plan_id}` | 标记题目已复习或再次出错 |
| GET | `/api/recommendations/stats` | 推荐统计 |

### 导出模块 `/api/export`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/export/snapshot` | 创建导出快照（冻结题目状态） |
| POST | `/api/export/generate` | 基于快照生成 PDF/Word 文件 |
| GET | `/api/export/documents` | 获取历史导出记录 |
| GET | `/api/export/documents/{id}` | 获取单条导出记录 |
| DELETE | `/api/export/documents/{id}` | 删除导出记录 |

### 错误响应格式（统一）

```json
{
  "status": "error",
  "code": "ERROR_CODE",
  "message": "人类可读的错误信息",
  "details": {}
}
```

---

## 非功能性需求

### 性能
- Vision API 调用超时设置：5 秒
- 推荐计划接口响应时间（含缓存命中）：< 200ms
- 推荐计划缓存 TTL：1 小时

### 安全
- 密码使用 bcrypt 哈希存储，不存明文
- JWT 使用 HS256 签名，密钥 ≥ 32 字符
- 所有 API 密钥、数据库凭证通过环境变量注入，使用 `.env` 文件
- `.env` 不提交到 git，使用 `.env.example` 作为模板
- 传输层强制 HTTPS

### 可用性
- 识别失败时始终创建题目记录（标记需审核），不丢失用户上传
- Redis 缓存不可用时降级为直接查询数据库

### 测试覆盖
- 后端整体测试覆盖率 > 80%
- Vision API 调用必须使用 mock 测试，不真实调用（防止浪费配额）
- 推荐算法必须有单元测试验证正确性
- 关键路径（上传识别、推荐计划、导出）需要集成测试

---

## 技术栈约束

### 后端（MUST）
- Python **3.11**（使用 `python3.11 -m venv venv`）
- FastAPI 0.100+、SQLAlchemy 2.0+、Alembic（数据库迁移）
- PostgreSQL 14+（主数据库）、Redis 7+（缓存）
- bcrypt（密码哈希）、python-jose（JWT）
- Google Vision API（图片识别）
- pytest + pytest-asyncio（测试）

### 前端（MUST）
- React 18 + TypeScript 5（严格模式，`"strict": true`）
- Vite 5（构建工具）、React Router 6（路由）
- Axios（HTTP 客户端，统一通过 `services/api.ts` 调用）
- 禁止使用 `// @ts-ignore`，禁止使用 `any` 类型

### 基础设施
- Docker + Docker Compose（本地开发环境）
- 图片存储：S3 或兼容对象存储（云存储，后端存储 URL）
- 文档存储：S3/CDN（导出文档，60 天有效期）

---

## 实现优先级

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| Phase 1 | 用户认证（登录、JWT、密码验证） | 最高 |
| Phase 2 | 题目存储（CRUD、数据隔离、统计） | 最高 |
| Phase 3 | 拍照识别（Vision API、质量检查、重试）| 最高（三天主线） |
| Phase 4 | 复习推荐（遗忘曲线、优先级、缓存） | 高 |
| Phase 5 | 文档导出（快照、PDF 生成、CDN 上传） | 中 |
| 后续 | 异步队列改造、管理员端、全文搜索 | 低 |
