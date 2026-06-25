---
name: evolve-memory
description: 扫描 corrections，把复发纠正提案为规则；标记过期记忆为 dormant
tools: Read, Write, Grep
---

# 记忆进化（硬化 + 遗忘）

## 设计参照
参照 SwarmAI 的三层机制：
- distillation_hook._extract_corrections() → 提取纠正
- steeringify.group_and_propose() → 聚类+提案
- evolution_maintenance_hook → 衰减过期条目

## 硬化：纠正 → 规则提案

1. 读 memory/corrections.md，按相似主题归类
2. 同类纠正出现 ≥3 次 → 生成规则提案到 rules/proposed.md：
   - **规则文本**：一句话、可判定、格式参照 rules/personal.md 现有条目
   - **级别**：MUST（会造成 bug/安全问题）/ SHOULD（偏好/风格）
   - **证据**：引用触发的纠正记录（日期+原文摘要）
   - **建议硬化层级**：
     - L1 文字规则（首次）
     - L2 hook 门控（复发 5+ 次）
     - L3 结构性不可能（反复跨项目出现）
3. **绝不**直接写入 rules/personal.md 或 CLAUDE.md

## 遗忘：达尔文式衰减

4. 扫 memory/MEMORY.md：
   - 条目日期 >60 天 且 该条目的关键词在最近 5 个 daily 日志中没出现过
     → 在条目末尾追加 <!--dormant YYYY-MM-DD-->
   - 已 dormant 超过 30 天 → 移到 memory/archive.md（不删）

## 铁律
- 执行者不是立法者：只写 proposed.md，人审后手动转正
- 遗忘 ≠ 删除：dormant 降权不删，archive 留可查
- 被推翻的旧决策：标 superseded_by + 降权（SwarmAI COE03 教训）
