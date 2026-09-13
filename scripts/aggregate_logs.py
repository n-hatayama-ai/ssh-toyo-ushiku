#!/usr/bin/env python3
"""daily check スクリプトの実行結果を execution-log.json に集約する。

GitHub Actions の各ステップが環境変数で結果を渡す想定:

    SCRIPT_MAIL_STATUS=ok|error
    SCRIPT_MAIL_MESSAGE="15件のメール確認"
    SCRIPT_MAIL_ERROR=""            # error のときのみ
    SCRIPT_MAIL_DURATION=12.3       # 任意（秒）

CALENDAR も同様のプレフィックスを使う。

標準ライブラリのみ（json / math / os / sys / datetime）で動作し、Python 3.9 以上を想定。

タイムゾーン方針:
  - ``timestamp`` / ``meta.last_updated`` は UTC（末尾 Z）。機械可読で曖昧さがない。
  - ``date`` は **実行環境のローカル日付**（JST 運用前提）。
    UTC 日付にすると JST 朝 8 時の定時実行が UTC では前日 23 時になり、
    同じ JST の日に再実行（JST 10 時 = UTC 当日 1 時）したときに date が
    ずれて重複排除が効かず、mail-check が 2 件並んでしまうため。
    GitHub Actions の runner は既定で UTC なので、ワークフロー側で
    ``env: TZ: Asia/Tokyo`` を設定すること。
"""

import json
import math
import os
import sys
from datetime import datetime, timezone

# (ログに記録する script 名, 環境変数のプレフィックス)
SCRIPTS = (
    ("mail-check", "SCRIPT_MAIL"),
    ("calendar-check", "SCRIPT_CALENDAR"),
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LOG_PATH = os.path.join(REPO_ROOT, "execution-log.json")

META_PROJECT = "noboru"
META_VERSION = 1


def log_path():
    """出力先。テスト用に EXECUTION_LOG_PATH で上書きできる。"""
    return os.environ.get("EXECUTION_LOG_PATH") or DEFAULT_LOG_PATH


def env_value(name):
    """環境変数を取得し、空文字・空白のみなら None を返す。"""
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def parse_duration(raw):
    """duration を float に変換する。数値でなければ None。

    nan / inf は JSON の仕様上表現できない（Python は NaN / Infinity という
    非標準のリテラルを書き出してしまい、JSON.parse などが失敗する）ため
    弾いて None にする。
    """
    if raw is None:
        return None
    try:
        result = float(raw)
    except ValueError:
        print(
            "warning: duration が数値ではないため無視します: {!r}".format(raw),
            file=sys.stderr,
        )
        return None
    if not math.isfinite(result):
        print(
            "warning: duration が有限の数値ではないため無視します: {!r}".format(raw),
            file=sys.stderr,
        )
        return None
    return result


def new_document():
    return {
        "meta": {
            "last_updated": None,
            "project": META_PROJECT,
            "version": META_VERSION,
        },
        "logs": [],
    }


def load_document(path):
    """既存の execution-log.json を読み込む。

    存在しない・壊れている場合は新規ドキュメントを返す（壊れていた場合は
    上書きで失われないよう .bak に退避する）。
    """
    if not os.path.exists(path):
        return new_document()

    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        print(
            "warning: {} を読み込めませんでした（{}）。新規作成します。".format(path, exc),
            file=sys.stderr,
        )
        backup_corrupt_file(path)
        return new_document()

    if not isinstance(data, dict) or not isinstance(data.get("logs"), list):
        print(
            "warning: {} の形式が不正です。新規作成します。".format(path),
            file=sys.stderr,
        )
        backup_corrupt_file(path)
        return new_document()

    meta = data.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    meta.setdefault("project", META_PROJECT)
    meta.setdefault("version", META_VERSION)
    data["meta"] = meta
    # logs の要素は dict のみ残す（想定外の値で後段が落ちないように）
    data["logs"] = [entry for entry in data["logs"] if isinstance(entry, dict)]
    return data


def backup_corrupt_file(path):
    backup = path + ".bak"
    try:
        os.replace(path, backup)
        print("既存ファイルを {} に退避しました。".format(backup), file=sys.stderr)
    except OSError as exc:
        print("warning: 退避に失敗しました（{}）。".format(exc), file=sys.stderr)


def local_date(now):
    """ログの ``date`` に使うローカル日付（既定は実行環境の TZ、運用上は JST）。

    ``timestamp`` は UTC のままにして、日付キーだけ人間の感覚（JST の 1 日）に
    合わせる。こうしないと JST 08:00（UTC 前日 23:00）の定時実行と
    JST 10:00（UTC 当日 01:00）の手動再実行で date が別日になり、
    「同一日付なら前回の結果を置き換える」という仕様が破れる。
    """
    return now.astimezone().strftime("%Y-%m-%d")


def build_entries(now):
    """環境変数から SCRIPTS 分のログエントリを作る。"""
    today = local_date(now)
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    entries = []
    for script_name, prefix in SCRIPTS:
        status = env_value(prefix + "_STATUS")
        status = status.lower() if status else "unknown"
        error_message = env_value(prefix + "_ERROR")
        if status != "error":
            # 成功時に error を残さない（誤解を招くため）
            error_message = None

        entries.append(
            {
                "date": today,
                "script": script_name,
                "status": status,
                "timestamp": timestamp,
                "duration_sec": parse_duration(env_value(prefix + "_DURATION")),
                "summary": env_value(prefix + "_MESSAGE"),
                "error_message": error_message,
            }
        )
    return entries


def merge_logs(existing, entries, today):
    """本日分の同名スクリプトのログを取り除いてから新しいエントリを追加する。"""
    replacing = {entry["script"] for entry in entries}
    kept = [
        entry
        for entry in existing
        if not (entry.get("date") == today and entry.get("script") in replacing)
    ]
    removed = len(existing) - len(kept)
    return kept + entries, removed


def write_document(path, document):
    """一時ファイル経由で書き込み、途中で失敗しても既存ファイルを壊さない。"""
    tmp_path = path + ".tmp"
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as handle:
            # allow_nan=False: NaN / Infinity は JSON として不正なので書き出さない
            json.dump(document, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
        os.replace(tmp_path, path)
    except (OSError, ValueError) as exc:
        print("error: {} の書き込みに失敗しました: {}".format(path, exc), file=sys.stderr)
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        return False
    return True


def main():
    path = log_path()
    now = datetime.now(timezone.utc)
    today = local_date(now)

    document = load_document(path)
    entries = build_entries(now)
    document["logs"], removed = merge_logs(document["logs"], entries, today)
    document["meta"]["last_updated"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    document["meta"].setdefault("project", META_PROJECT)
    document["meta"].setdefault("version", META_VERSION)

    if not write_document(path, document):
        return 1

    if removed:
        print("本日分の既存ログ {} 件を置き換えました。".format(removed))
    for entry in entries:
        line = "  {}: {}".format(entry["script"], entry["status"])
        if entry["summary"]:
            line += " - {}".format(entry["summary"])
        if entry["error_message"]:
            line += " (error: {})".format(entry["error_message"])
        print(line)
    print("execution-log.json を更新しました: {} (logs: {} 件)".format(path, len(document["logs"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
