#!/usr/bin/env bash
# Inject last handoff note into session context if it exists
PROGRESS="/home/participant/.claude/projects/-workshop-aws-harness/memory/progress.md"

if [ -f "$PROGRESS" ] && [ -s "$PROGRESS" ]; then
  echo "## 上次交接"
  echo ""
  cat "$PROGRESS"
fi
