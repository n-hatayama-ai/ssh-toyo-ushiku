#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 環境変数で上書き可能。未設定ならリポジトリ／スクリプト位置から解決する。
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
GMAIL_SCRIPT="${GMAIL_SCRIPT:-$SCRIPT_DIR/gmail_check.py}"
LAST_RUN_FILE="${LAST_RUN_FILE:-$SCRIPT_DIR/last_run_date.txt}"
TODAY="$(date +%Y-%m-%d)"

# Service Account JSON。GOOGLE_API_CREDS を優先し、旧名の環境変数にもフォールバックする。
GOOGLE_API_CREDS="${GOOGLE_API_CREDS:-${GOOGLE_API_SERVICE_ACCOUNT_JSON:-${GMAIL_API_CREDS:-}}}"

if [ -z "$GOOGLE_API_CREDS" ]; then
  echo "Error: GOOGLE_API_CREDS environment variable is not set" >&2
  exit 1
fi

# FORCE_RUN=1 で当日実行済みチェックを飛ばせる。
if [ "${FORCE_RUN:-0}" != "1" ] && \
   [ "$(cat "$LAST_RUN_FILE" 2>/dev/null || true)" = "$TODAY" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') already checked today, skipping"
  exit 0
fi

cd "$PROJECT_DIR"

"$PYTHON_BIN" "$GMAIL_SCRIPT" \
  --google-creds "$GOOGLE_API_CREDS" \
  --project-dir "$PROJECT_DIR"

echo "$TODAY" > "$LAST_RUN_FILE"
