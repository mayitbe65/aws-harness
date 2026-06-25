---
name: distill-memory
description: 将 memory/daily/ 的原始日志蒸馏为 memory/MEMORY.md 的持久条目
tools: Read, Write, Glob, Grep
---

# 记忆蒸馏

## 设计参照
参照 SwarmAI distillation_hook 的两阶段架构：
- 阶段1：从 daily 日志提取结构化信号（decisions, lessons, patterns）
- 阶段2：频率门控 + 去重后写入 MEMORY.md

## 触发条件
`memory/daily/` 下有 ≥3 个未标记 `<!--distilled-->` 的日志文件。

若不满足，输出"⏭️ 日志文件不足 3 个，跳过蒸馏"后退出。

## 执行流程

### 阶段1 — 提取信号

读取所有未含 `<!--distilled-->` 标记的 `memory/daily/*.md`，逐文件扫描，提取三类条目：

#### 1. 关键决策（Key Decisions）
识别模式（大小写不敏感）：
```
decided to / chose / will use / going with / switched to
```
格式：
```
- [YYYY-MM-DD] **决策标题** — 为什么这样选择（保留 why）
```

#### 2. 教训（Lessons Learned）
识别模式（大小写不敏感）：
```
lesson learned / fixed by / root cause was / should have / next time
```
格式：
```
- [YYYY-MM-DD] **教训标题** — 具体怎么避免
```

#### 3. 复发模式（Recurring Patterns）
条件：同类事件（关键词或主题）在不同日志文件中出现 ≥2 次（频率门控）。
格式：
```
- [YYYY-MM-DD] **模式名** — 出现N次，建议动作
```

### 阶段2 — 去重写入

1. 读取现有 `memory/MEMORY.md`
2. 对阶段1提取的每条候选：
   - 若 MEMORY.md 已有**相同标题**的条目 → 跳过
   - 否则 → prepend（插入到对应 section 的顶部）
3. Section 对应关系：
   - Key Decisions → `## Key Decisions` section
   - Lessons Learned → `## Lessons Learned` section
   - Recurring Patterns → `## Recurring Patterns` section
   - 若 section 不存在，先创建 section header 再插入
4. 写完后检查 MEMORY.md 总字数：
   - 超过 30K token 估算（约 120K 字符）时，将最旧的条目标记为 `<!--dormant-->`，并在文件顶部输出警告：`⚠️ MEMORY.md 接近上限，已将 N 条最旧条目标记为 dormant`

### 阶段3 — 标记已处理

在每个已处理的 daily 文件尾部追加一行：
```
<!--distilled YYYY-MM-DD-->
```
其中 YYYY-MM-DD 为今天的日期。

## 铁律

- **只提炼"学到了什么"，不照抄"发生了什么"**
- **不删 daily 文件**（留待 TTL 过期或手动归档）
- 每条写入 MEMORY.md 的条目必须对未来会话可直接用（能指导判断，不是流水账）
- 去重基于标题匹配，不基于日期
- 总 MEMORY.md 体积控制在 <30K token

## 输出格式

执行完成后，用以下格式汇报：

```
## 蒸馏报告

- 处理日志文件：N 个
- 新增 Key Decisions：N 条
- 新增 Lessons Learned：N 条
- 新增 Recurring Patterns：N 条
- 去重跳过：N 条
- MEMORY.md 当前体积：约 N 字符

已标记为 distilled 的文件：
- memory/daily/YYYY-MM-DD.md
```
