---
name: memory-health
description: 对记忆系统做健康度报告：覆盖率、新鲜度、进化率、体积、闭环完整性
tools: Read, Glob, Grep, Bash
---

# 记忆系统健康报告

## 设计参照
参照 SwarmAI DDD Layer 2 的五维健康度评分思想，简化为记忆 pipeline 的五维：

## 五维评估

### 1. 覆盖率 Coverage
- memory/ 下有多少记忆条目？
- daily/ 积累了多少天的日志？
- corrections 有多少条？
- 评分：>20 条记忆 + >7 天日志 + >5 条纠正 = 满分

### 2. 新鲜度 Freshness
- 最近一次 daily 日志是什么时候？
- 最近一次蒸馏（有 <!--distilled--> 标记）是什么时候？
- 有多少 daily 积压未蒸馏？
- 评分：<3 天无新日志 + <3 个积压 = 满分

### 3. 进化率 Evolution Rate
- corrections 中有多少条对应了 MEMORY 条目或 rules？（被消化的比例）
- proposed.md 有多少待审提案？有多少已批准转正的？
- 评分：消化率 >50% + 有已转正规则 = 满分

### 4. 体积 Size Budget
- MEMORY.md 当前估算 token 数（word_count * 1.3）
- rules/ 所有规则总 token 数
- 总注入体积 vs 50K 上限的余量百分比
- 评分：<30K 绿 / 30-50K 黄 / >50K 红（需要遗忘或检索）

### 5. 闭环完整性 Loop Integrity
- hooks 配置是否完整（Stop + UserPromptSubmit + SessionStart）？
- skills 是否存在（distill-memory + evolve-memory）？
- MEMORY.md 是否存在且非空？
- 评分：全有 = 满分；缺任何一环 = 闭环断裂

## 输出格式

| 维度 | 得分 | 状态 | 说明 |
|------|------|------|------|
| 覆盖率 | N/100 | 🟢/🟡/🔴 | ... |
| ... | ... | ... | ... |

**总评**：🟢 飞轮健康 / 🟡 需关注（某环节积压）/ 🔴 闭环断裂

**建议下一步**：基于最低分维度给出 1-2 条具体行动
