#!/usr/bin/env bash
set -uo pipefail

MEMORY_DIR="/home/participant/.claude/projects/-workshop-aws-harness/memory"
DAILY_DIR="${MEMORY_DIR}/daily"
mkdir -p "$DAILY_DIR"

DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)
OUT="${DAILY_DIR}/${DATE}.md"

# Changed files since last commit
FILES=$(git -C /workshop/aws-harness diff --name-only HEAD~1 2>/dev/null | tr '\n' ' ' | sed 's/ $//' || echo "(no git diff)")

# Recent commits
COMMITS=$(git -C /workshop/aws-harness log --oneline -3 --no-decorate 2>/dev/null || echo "(no commits)")

{
  echo ""
  echo "## ${TIME} | session"
  echo "**改动文件：** ${FILES:-（无）}"
  echo "**Git：**"
  echo "${COMMITS}" | sed 's/^/  /'
} >> "$OUT"

exit 0
