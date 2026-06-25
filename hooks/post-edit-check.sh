#!/usr/bin/env bash
set -uo pipefail

VIOLATIONS=""

# Extract edited file path from stdin JSON
FILE_PATH=$(jq -r '.tool_input.file_path // empty' 2>/dev/null)

# --- Lint check (frontend only) ---
if echo "$FILE_PATH" | grep -qE '\.(ts|tsx|js|jsx)$'; then
  LINT_TARGET="$FILE_PATH"
elif [ -z "$FILE_PATH" ]; then
  LINT_TARGET="src/"
else
  LINT_TARGET=""
fi

if [ -n "$LINT_TARGET" ] && [ -d "/workshop/aws-harness/frontend" ]; then
  LINT_OUT=$(cd /workshop/aws-harness/frontend && npx eslint --quiet "$LINT_TARGET" 2>&1) || {
    VIOLATIONS="${VIOLATIONS}[ESLint] Lint errors found:\n${LINT_OUT}\n"
  }
fi

# --- Architecture check: no direct DB/API calls in UI components ---
ARCH_OUT=$(grep -rn "fetch\|axios\|prisma\|db\." /workshop/aws-harness/frontend/src/components/ 2>/dev/null || true)
if [ -n "$ARCH_OUT" ]; then
  VIOLATIONS="${VIOLATIONS}[Architecture] Direct DB/API references found in UI components (should go through services/ or hooks/):\n${ARCH_OUT}\n"
fi

# --- Emit result ---
if [ -n "$VIOLATIONS" ]; then
  printf "%b" "$VIOLATIONS"
  exit 1
fi

exit 0
