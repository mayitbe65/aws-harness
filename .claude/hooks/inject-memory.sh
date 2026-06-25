#!/usr/bin/env bash
set -uo pipefail

MEMORY_DIR="/home/participant/.claude/projects/-workshop-aws-harness/memory"
PROJECT_DIR="/workshop/aws-harness"

# --- 全量注入 ---

if [ -f "${MEMORY_DIR}/MEMORY.md" ]; then
  echo "## 项目记忆索引"
  echo ""
  cat "${MEMORY_DIR}/MEMORY.md"
  echo ""
fi

if [ -f "${PROJECT_DIR}/rules/personal.md" ]; then
  echo "## 项目规则（personal.md）"
  echo ""
  cat "${PROJECT_DIR}/rules/personal.md"
  echo ""
fi

if [ -f "${MEMORY_DIR}/corrections.md" ] && [ -s "${MEMORY_DIR}/corrections.md" ]; then
  echo "## 近期纠正（待进化）"
  echo ""
  # 最近 5 条：跳过注释行和空行，取最后 5 条有效条目
  grep -E '^\- \[' "${MEMORY_DIR}/corrections.md" | tail -5
  echo ""
fi

# --- 蒸馏提醒 ---

REMINDERS=""

# 统计 daily/ 下无 <!--distilled 标记的文件数量
if [ -d "${MEMORY_DIR}/daily" ]; then
  UNDISTILLED=$(grep -rL '<!--distilled' "${MEMORY_DIR}/daily/" 2>/dev/null | grep '\.md$' | wc -l | tr -d ' ')
  if [ "${UNDISTILLED}" -ge 3 ]; then
    REMINDERS="${REMINDERS}📋 你有 ${UNDISTILLED} 个未蒸馏的日志。本次会话结束前，建议运行 /distill-memory 整理记忆。\n"
  fi
fi

# 统计 corrections.md 中有效纠正条目数量
if [ -f "${MEMORY_DIR}/corrections.md" ]; then
  CORRECTION_COUNT=$(grep -c '^\- \[' "${MEMORY_DIR}/corrections.md" 2>/dev/null || echo 0)
  if [ "${CORRECTION_COUNT}" -gt 10 ]; then
    REMINDERS="${REMINDERS}⚡ 有 ${CORRECTION_COUNT} 条积压纠正。建议运行 /evolve-memory 检查是否有复发模式可提案为规则。\n"
  fi
fi

if [ -n "${REMINDERS}" ]; then
  echo "## 💡 建议（非强制）"
  echo ""
  printf "%b" "${REMINDERS}"
  echo ""
fi
