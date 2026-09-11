#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 環境変数で上書き可能。未設定ならリポジトリ／スクリプト位置から解決する。
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CLAUDE_MODEL="${CLAUDE_MODEL:-claude-sonnet-5}"
PROMPT_FILE="${PROMPT_FILE:-$SCRIPT_DIR/deadline_check_prompt.md}"

cd "$PROJECT_DIR"

RETRY_COUNT="${RETRY_COUNT:-3}"
RETRY_DELAY_SEC="${RETRY_DELAY_SEC:-30}"
for attempt in $(seq 1 "$RETRY_COUNT"); do
  if "$CLAUDE_BIN" -p "$(cat "$PROMPT_FILE")" \
    --model "$CLAUDE_MODEL" \
    --allowedTools "Read,Write,Glob"; then
    break
  fi
  if [ "$attempt" -eq "$RETRY_COUNT" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') claude -p failed after $RETRY_COUNT attempts, giving up"
    exit 1
  fi
  echo "$(date '+%Y-%m-%d %H:%M:%S') claude -p failed (attempt $attempt/$RETRY_COUNT), retrying in ${RETRY_DELAY_SEC}s"
  sleep "$RETRY_DELAY_SEC"
done
