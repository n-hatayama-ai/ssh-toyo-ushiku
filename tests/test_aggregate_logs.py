#!/usr/bin/env python3
"""scripts/aggregate_logs.py のテスト。

実行方法:
    python3 -m unittest discover -s tests -v
    # あるいは
    python3 tests/test_aggregate_logs.py

標準ライブラリの unittest のみを使用（追加依存なし）。
"""

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(REPO_ROOT, "scripts", "aggregate_logs.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("aggregate_logs", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


aggregate_logs = _load_module()


class AggregateLogsTestBase(unittest.TestCase):
    """一時ディレクトリと環境変数を毎回リセットする共通基底クラス。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="aggregate-logs-test-")
        self.addCleanup(shutil.rmtree, self.tmpdir, True)
        self.log_path = os.path.join(self.tmpdir, "execution-log.json")

    def run_script(self, env_overrides=None, log_path=None, cwd=None):
        """スクリプトを別プロセスで実行し CompletedProcess を返す。"""
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "EXECUTION_LOG_PATH": log_path if log_path is not None else self.log_path,
            "TZ": "Asia/Tokyo",
        }
        if env_overrides:
            for key, value in env_overrides.items():
                if value is None:
                    env.pop(key, None)
                else:
                    env[key] = value
        return subprocess.run(
            [sys.executable, SCRIPT_PATH],
            env=env,
            cwd=cwd or self.tmpdir,
            capture_output=True,
            text=True,
        )

    def read_log(self, path=None):
        with open(path or self.log_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def entries_by_script(self, document):
        return {entry["script"]: entry for entry in document["logs"]}


class TestCase1NewFile(AggregateLogsTestBase):
    """ケース1: ファイルが無い状態からの新規作成。"""

    def test_creates_file_with_meta_and_two_entries(self):
        result = self.run_script(
            {
                "SCRIPT_MAIL_STATUS": "ok",
                "SCRIPT_MAIL_MESSAGE": "15件のメール確認",
                "SCRIPT_CALENDAR_STATUS": "error",
                "SCRIPT_CALENDAR_ERROR": "APIに接続できません",
            }
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        document = self.read_log()
        self.assertEqual(document["meta"]["project"], "noboru")
        self.assertEqual(document["meta"]["version"], 1)
        self.assertIsNotNone(document["meta"]["last_updated"])
        self.assertEqual(len(document["logs"]), 2)

        entries = self.entries_by_script(document)
        self.assertEqual(sorted(entries), ["calendar-check", "mail-check"])
        self.assertEqual(entries["mail-check"]["status"], "ok")
        self.assertEqual(entries["mail-check"]["summary"], "15件のメール確認")
        self.assertIsNone(entries["mail-check"]["error_message"])
        self.assertIsNone(entries["mail-check"]["duration_sec"])
        self.assertEqual(entries["calendar-check"]["status"], "error")
        self.assertEqual(entries["calendar-check"]["error_message"], "APIに接続できません")

    def test_formatting_is_indent2_utf8_and_trailing_newline(self):
        self.run_script({"SCRIPT_MAIL_STATUS": "ok", "SCRIPT_MAIL_MESSAGE": "日本語"})
        with open(self.log_path, "r", encoding="utf-8") as handle:
            raw = handle.read()
        self.assertTrue(raw.endswith("\n"))
        self.assertIn('\n  "meta"', raw)  # indent=2
        self.assertIn("日本語", raw)  # ensure_ascii=False
        self.assertNotIn("\\u", raw)


class TestCase2SameDayRerun(AggregateLogsTestBase):
    """ケース2: 同日再実行で本日分のみ置き換え、過去ログは保持。"""

    def setUp(self):
        super().setUp()
        today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
        self.today = today
        seed = {
            "meta": {"last_updated": "2026-01-01T00:00:00Z", "project": "noboru", "version": 1},
            "logs": [
                {
                    "date": "2026-01-01",
                    "script": "mail-check",
                    "status": "ok",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "duration_sec": 1.0,
                    "summary": "過去ログ",
                    "error_message": None,
                },
                {
                    "date": today,
                    "script": "mail-check",
                    "status": "error",
                    "timestamp": today + "T00:00:00Z",
                    "duration_sec": None,
                    "summary": "古い結果",
                    "error_message": "旧エラー",
                },
                {
                    "date": today,
                    "script": "other-check",
                    "status": "ok",
                    "timestamp": today + "T00:00:00Z",
                    "duration_sec": None,
                    "summary": "別スクリプト",
                    "error_message": None,
                },
            ],
        }
        with open(self.log_path, "w", encoding="utf-8") as handle:
            json.dump(seed, handle, ensure_ascii=False)

    def test_replaces_today_entries_and_keeps_others(self):
        result = self.run_script(
            {"SCRIPT_MAIL_STATUS": "ok", "SCRIPT_MAIL_MESSAGE": "新しい結果"}
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        document = self.read_log()
        # 過去ログ1 + 同日別スクリプト1 + 新規2 = 4
        self.assertEqual(len(document["logs"]), 4)

        mail_today = [
            e
            for e in document["logs"]
            if e["script"] == "mail-check" and e["date"] == self.today
        ]
        self.assertEqual(len(mail_today), 1)
        self.assertEqual(mail_today[0]["summary"], "新しい結果")
        self.assertIsNone(mail_today[0]["error_message"])

        past = [e for e in document["logs"] if e["date"] == "2026-01-01"]
        self.assertEqual(len(past), 1)
        self.assertEqual(past[0]["summary"], "過去ログ")

        other = [e for e in document["logs"] if e["script"] == "other-check"]
        self.assertEqual(len(other), 1)


class TestCase3CorruptJson(AggregateLogsTestBase):
    """ケース3: 壊れた JSON は .bak に退避して作り直す。"""

    def test_backs_up_and_recreates(self):
        with open(self.log_path, "w", encoding="utf-8") as handle:
            handle.write("{ this is not json")

        result = self.run_script({"SCRIPT_MAIL_STATUS": "ok"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("warning", result.stderr)

        backup = self.log_path + ".bak"
        self.assertTrue(os.path.exists(backup))
        with open(backup, "r", encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "{ this is not json")

        document = self.read_log()
        self.assertEqual(len(document["logs"]), 2)


class TestCase4MalformedStructure(AggregateLogsTestBase):
    """ケース4: JSON として妥当でも形式違い（トップレベルが配列）。"""

    def test_array_toplevel_is_recreated(self):
        with open(self.log_path, "w", encoding="utf-8") as handle:
            json.dump([1, 2, 3], handle)

        result = self.run_script({"SCRIPT_MAIL_STATUS": "ok"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("warning", result.stderr)
        self.assertTrue(os.path.exists(self.log_path + ".bak"))

        document = self.read_log()
        self.assertEqual(document["meta"]["project"], "noboru")
        self.assertEqual(len(document["logs"]), 2)

    def test_non_dict_entries_are_dropped(self):
        seed = {"meta": {}, "logs": ["ゴミ", 42, None]}
        with open(self.log_path, "w", encoding="utf-8") as handle:
            json.dump(seed, handle, ensure_ascii=False)

        result = self.run_script({"SCRIPT_MAIL_STATUS": "ok"})
        self.assertEqual(result.returncode, 0, result.stderr)
        document = self.read_log()
        self.assertEqual(len(document["logs"]), 2)
        self.assertTrue(all(isinstance(e, dict) for e in document["logs"]))


class TestCase5WriteFailure(AggregateLogsTestBase):
    """ケース5: 書き込み失敗時は exit 1 で .tmp を残さない。"""

    @unittest.skipIf(
        hasattr(os, "geteuid") and os.geteuid() == 0,
        "root ではパーミッションによる書き込み失敗を再現できない",
    )
    def test_readonly_directory_exits_1(self):
        readonly_dir = os.path.join(self.tmpdir, "readonly")
        os.makedirs(readonly_dir)
        target = os.path.join(readonly_dir, "execution-log.json")
        os.chmod(readonly_dir, stat.S_IRUSR | stat.S_IXUSR)
        self.addCleanup(os.chmod, readonly_dir, stat.S_IRWXU)

        result = self.run_script({"SCRIPT_MAIL_STATUS": "ok"}, log_path=target)
        self.assertEqual(result.returncode, 1)
        self.assertIn("error", result.stderr)

        os.chmod(readonly_dir, stat.S_IRWXU)
        self.assertEqual(os.listdir(readonly_dir), [])


class TestCase6DefaultPath(AggregateLogsTestBase):
    """ケース6: 既定の出力先はリポジトリルートの execution-log.json。"""

    def test_default_path_is_repo_root(self):
        self.assertEqual(
            aggregate_logs.DEFAULT_LOG_PATH,
            os.path.join(REPO_ROOT, "execution-log.json"),
        )

    def test_default_path_used_when_env_absent(self):
        # 実際のリポジトリルートを汚さないよう、環境変数なしでの解決だけ確認する
        original = os.environ.pop("EXECUTION_LOG_PATH", None)
        try:
            self.assertEqual(aggregate_logs.log_path(), aggregate_logs.DEFAULT_LOG_PATH)
        finally:
            if original is not None:
                os.environ["EXECUTION_LOG_PATH"] = original


class TestCase7CwdIndependence(AggregateLogsTestBase):
    """ケース7: 別 cwd からのシェバン直接実行と出力先ディレクトリの自動作成。"""

    def test_shebang_execution_from_other_cwd_creates_directories(self):
        self.assertTrue(os.access(SCRIPT_PATH, os.X_OK), "スクリプトに実行権限が無い")
        nested = os.path.join(self.tmpdir, "a", "b", "execution-log.json")
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "EXECUTION_LOG_PATH": nested,
            "TZ": "Asia/Tokyo",
            "SCRIPT_MAIL_STATUS": "ok",
        }
        result = subprocess.run(
            [SCRIPT_PATH], env=env, cwd="/", capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.exists(nested))
        self.assertEqual(len(self.read_log(nested)["logs"]), 2)


class TestNonFiniteDuration(AggregateLogsTestBase):
    """Fix 1: NaN / Infinity の duration は捨てて JSON を壊さない。"""

    def test_nan_duration_warns_and_writes_null(self):
        result = self.run_script(
            {"SCRIPT_MAIL_STATUS": "ok", "SCRIPT_MAIL_DURATION": "nan"}
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("warning", result.stderr)
        self.assertIn("duration", result.stderr)

        with open(self.log_path, "r", encoding="utf-8") as handle:
            raw = handle.read()
        self.assertNotIn("NaN", raw)
        self.assertNotIn("Infinity", raw)

        entries = self.entries_by_script(json.loads(raw))
        self.assertIsNone(entries["mail-check"]["duration_sec"])

    def test_infinity_variants_are_rejected(self):
        for raw_value in ("Infinity", "-inf", "INF", "nan", "-NaN"):
            with self.subTest(value=raw_value):
                self.assertIsNone(aggregate_logs.parse_duration(raw_value))

    def test_non_numeric_duration_is_rejected(self):
        self.assertIsNone(aggregate_logs.parse_duration("abc"))
        self.assertIsNone(aggregate_logs.parse_duration(None))

    def test_finite_duration_is_kept(self):
        self.assertEqual(aggregate_logs.parse_duration("12.5"), 12.5)
        self.assertEqual(aggregate_logs.parse_duration(" 0 "), 0.0)

    def test_write_document_rejects_non_finite_values(self):
        # allow_nan=False の保険が効いているか（parse_duration をすり抜けた場合）
        target = os.path.join(self.tmpdir, "guard.json")
        document = {"meta": {}, "logs": [{"duration_sec": float("nan")}]}
        self.assertFalse(aggregate_logs.write_document(target, document))
        self.assertFalse(os.path.exists(target))
        self.assertFalse(os.path.exists(target + ".tmp"))


class TestTimezoneDedup(AggregateLogsTestBase):
    """Fix 2: JST の同一日に UTC 日付をまたいで再実行しても重複しない。"""

    def setUp(self):
        super().setUp()
        original_tz = os.environ.get("TZ")
        os.environ["TZ"] = "Asia/Tokyo"
        time.tzset()

        def restore():
            if original_tz is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = original_tz
            time.tzset()

        self.addCleanup(restore)

    def test_date_uses_local_timezone(self):
        # JST 2026-09-12 08:00 = UTC 2026-09-11 23:00
        now = datetime(2026, 9, 11, 23, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(aggregate_logs.local_date(now), "2026-09-12")

    def test_timestamp_stays_utc(self):
        now = datetime(2026, 9, 11, 23, 0, 0, tzinfo=timezone.utc)
        entries = aggregate_logs.build_entries(now)
        self.assertEqual(entries[0]["timestamp"], "2026-09-11T23:00:00Z")
        self.assertEqual(entries[0]["date"], "2026-09-12")

    def test_runs_straddling_utc_midnight_dedup_to_one_entry(self):
        # 定時実行: JST 2026-09-12 08:00 (UTC 09-11 23:00)
        scheduled = datetime(2026, 9, 11, 23, 0, 0, tzinfo=timezone.utc)
        # 手動再実行: JST 2026-09-12 10:00 (UTC 09-12 01:00)
        manual = datetime(2026, 9, 12, 1, 0, 0, tzinfo=timezone.utc)

        first = aggregate_logs.build_entries(scheduled)
        logs, removed = aggregate_logs.merge_logs(
            [], first, aggregate_logs.local_date(scheduled)
        )
        self.assertEqual(removed, 0)
        self.assertEqual(len(logs), 2)

        second = aggregate_logs.build_entries(manual)
        logs, removed = aggregate_logs.merge_logs(
            logs, second, aggregate_logs.local_date(manual)
        )
        self.assertEqual(removed, 2, "JST 同日の再実行は前回分を置き換えるべき")
        self.assertEqual(len(logs), 2)

        mail = [e for e in logs if e["script"] == "mail-check"]
        self.assertEqual(len(mail), 1)
        self.assertEqual(mail[0]["date"], "2026-09-12")
        self.assertEqual(mail[0]["timestamp"], "2026-09-12T01:00:00Z")

    def test_different_jst_days_are_kept_separately(self):
        day1 = datetime(2026, 9, 11, 23, 0, 0, tzinfo=timezone.utc)  # JST 09-12
        day2 = datetime(2026, 9, 12, 23, 0, 0, tzinfo=timezone.utc)  # JST 09-13
        logs, _ = aggregate_logs.merge_logs(
            [], aggregate_logs.build_entries(day1), aggregate_logs.local_date(day1)
        )
        logs, removed = aggregate_logs.merge_logs(
            logs, aggregate_logs.build_entries(day2), aggregate_logs.local_date(day2)
        )
        self.assertEqual(removed, 0)
        self.assertEqual(len(logs), 4)


class TestEnvNormalization(AggregateLogsTestBase):
    """環境変数の正規化（status / message / error）。"""

    def test_status_is_lowercased_and_defaults_to_unknown(self):
        result = self.run_script({"SCRIPT_MAIL_STATUS": "OK"})
        self.assertEqual(result.returncode, 0, result.stderr)
        entries = self.entries_by_script(self.read_log())
        self.assertEqual(entries["mail-check"]["status"], "ok")
        self.assertEqual(entries["calendar-check"]["status"], "unknown")

    def test_blank_message_becomes_null(self):
        result = self.run_script(
            {"SCRIPT_MAIL_STATUS": "ok", "SCRIPT_MAIL_MESSAGE": "   "}
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        entries = self.entries_by_script(self.read_log())
        self.assertIsNone(entries["mail-check"]["summary"])

    def test_error_is_dropped_when_status_is_not_error(self):
        result = self.run_script(
            {"SCRIPT_MAIL_STATUS": "ok", "SCRIPT_MAIL_ERROR": "残骸のエラー"}
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        entries = self.entries_by_script(self.read_log())
        self.assertIsNone(entries["mail-check"]["error_message"])

    def test_entry_keys_match_spec(self):
        self.run_script({"SCRIPT_MAIL_STATUS": "ok"})
        entry = self.entries_by_script(self.read_log())["mail-check"]
        self.assertEqual(
            sorted(entry),
            [
                "date",
                "duration_sec",
                "error_message",
                "script",
                "status",
                "summary",
                "timestamp",
            ],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
