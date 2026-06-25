#!/usr/bin/env bash
set -uo pipefail

MEMORY_DIR="/home/participant/.claude/projects/-workshop-aws-harness/memory"
CORRECTIONS="${MEMORY_DIR}/corrections.md"

# Read JSON from stdin
INPUT=$(cat)

# Extract user message text
CONTENT=$(echo "$INPUT" | jq -r '.prompt // .input.content // ""' 2>/dev/null || echo "")

if [ -z "$CONTENT" ]; then
  exit 0
fi

# Match correction signal words (Chinese and English)
if echo "$CONTENT" | grep -qiE '不对|应该是|错了|别这么|搞反|不是这样|wrong|should be|don'\''t|stop|revert'; then
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
  SNIPPET=$(echo "$CONTENT" | head -c 120 | tr '\n' ' ')
  mkdir -p "$MEMORY_DIR"
  echo "- [${TIMESTAMP}] ${SNIPPET}" >> "$CORRECTIONS"
fi

exit 0
