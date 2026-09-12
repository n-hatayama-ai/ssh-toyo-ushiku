#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"

GOOGLE_API_CREDS="${GOOGLE_API_CREDS:-${GOOGLE_API_SERVICE_ACCOUNT_JSON:-${CALENDAR_API_CREDS:-}}}"

if [ -z "$GOOGLE_API_CREDS" ]; then
  echo "Error: GOOGLE_API_CREDS environment variable is not set" >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
CALENDAR_SCRIPT="${CALENDAR_SCRIPT:-$SCRIPT_DIR/calendar_check.py}"
CALENDAR_ACCOUNT="${CALENDAR_ACCOUNT:-n-hatayama@toyo.jp}"
CALENDAR_DAYS_AHEAD="${CALENDAR_DAYS_AHEAD:-21}"

"$PYTHON_BIN" "$CALENDAR_SCRIPT" \
  --google-creds "$GOOGLE_API_CREDS" \
  --project-dir "$PROJECT_DIR" \
  --account "$CALENDAR_ACCOUNT" \
  --days-ahead "$CALENDAR_DAYS_AHEAD"
