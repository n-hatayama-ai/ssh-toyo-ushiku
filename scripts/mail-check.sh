#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 環境変数で上書き可能。未設定ならリポジトリ／スクリプト位置から解決する。
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CLAUDE_MODEL="${CLAUDE_MODEL:-claude-sonnet-5}"
PROMPT_FILE="${PROMPT_FILE:-$SCRIPT_DIR/mail_check_prompt.md}"
LAST_RUN_FILE="${LAST_RUN_FILE:-$SCRIPT_DIR/last_run_date.txt}"
TODAY="$(date +%Y-%m-%d)"

if [ "$(cat "$LAST_RUN_FILE" 2>/dev/null || true)" = "$TODAY" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') already checked today, skipping"
  exit 0
fi

cd "$PROJECT_DIR"

"$CLAUDE_BIN" -p "$(cat "$PROMPT_FILE")" \
  --model "$CLAUDE_MODEL" \
  --allowedTools "mcp__claude_ai_Gmail__search_threads,mcp__claude_ai_Gmail__get_thread,mcp__claude_ai_Gmail__get_message,mcp__claude_ai_Gmail__list_labels,Read,Write,Glob"

echo "$TODAY" > "$LAST_RUN_FILE"
