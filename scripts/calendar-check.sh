#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 環境変数で上書き可能。未設定ならリポジトリ／スクリプト位置から解決する。
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CLAUDE_MODEL="${CLAUDE_MODEL:-claude-sonnet-5}"
PROMPT_FILE="${PROMPT_FILE:-$SCRIPT_DIR/calendar_check_prompt.md}"
CACHE_BUILDER="${CACHE_BUILDER:-$SCRIPT_DIR/build_calendar_cache.py}"

cd "$PROJECT_DIR"

"$CLAUDE_BIN" -p "$(cat "$PROMPT_FILE")" \
  --model "$CLAUDE_MODEL" \
  --allowedTools "mcp__claude_ai_Google_Calendar__list_events,mcp__claude_ai_Google_Calendar__search_events,mcp__claude_ai_Google_Calendar__list_calendars,Read,Write"

# build_calendar_cache.py はローカル環境専用。存在する場合のみ実行する。
if [ -f "$CACHE_BUILDER" ]; then
  python3 "$CACHE_BUILDER"
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') cache builder not found at $CACHE_BUILDER, skipping"
fi
