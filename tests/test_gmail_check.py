#!/usr/bin/env python3
"""scripts/gmail_check.py のテスト。

実行方法:
    python3 -m unittest discover -s tests -v
    # あるいは
    python3 tests/test_gmail_check.py

標準ライブラリの unittest のみを使用（Google API ライブラリが無くても動く）。
"""

import base64
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(REPO_ROOT, "scripts", "gmail_check.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("gmail_check", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gmail_check = _load_module()


def b64(text):
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


def make_message(
    msg_id="m1",
    thread_id=None,
    subject="件名",
    sender="送信者 <someone@example.com>",
    body="本文です。",
    mime_type="text/plain",
    headers=None,
    internal_date=None,
    snippet="",
):
    all_headers = [
        {"name": "Subject", "value": subject},
        {"name": "From", "value": sender},
    ]
    all_headers.extend(headers or [])
    return {
        "id": msg_id,
        "threadId": thread_id or msg_id,
        "snippet": snippet,
        "internalDate": str(internal_date or 1757000000000),
        "payload": {
            "mimeType": mime_type,
            "headers": all_headers,
            "body": {"data": b64(body)} if body else {},
        },
    }


class CredentialLoadingTest(unittest.TestCase):
    def test_plain_json_string(self):
        info = gmail_check.load_credentials_info('{"type": "service_account"}')
        self.assertEqual(info["type"], "service_account")

    def test_base64_json(self):
        raw = base64.b64encode(b'{"type": "service_account"}').decode("ascii")
        info = gmail_check.load_credentials_info(raw)
        self.assertEqual(info["type"], "service_account")

    def test_file_path(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as fh:
            json.dump({"type": "service_account"}, fh)
            path = fh.name
        self.addCleanup(os.unlink, path)
        info = gmail_check.load_credentials_info(path)
        self.assertEqual(info["type"], "service_account")

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            gmail_check.load_credentials_info("   ")

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            gmail_check.load_credentials_info("これは JSON ではない")


class ParsingTest(unittest.TestCase):
    def test_plain_text_body(self):
        item = gmail_check.parse_message(make_message(body="こんにちは\n\n\n世界"))
        self.assertEqual(item["body"], "こんにちは\n世界")
        self.assertTrue(item["body_available"])

    def test_html_only_body_is_stripped(self):
        html_body = "<html><body><p>お知らせ</p><br><b>締切は10/1</b></body></html>"
        item = gmail_check.parse_message(
            make_message(body=html_body, mime_type="text/html")
        )
        self.assertIn("お知らせ", item["body"])
        self.assertIn("締切は10/1", item["body"])
        self.assertNotIn("<b>", item["body"])

    def test_multipart_prefers_plain(self):
        message = {
            "id": "m1",
            "threadId": "t1",
            "internalDate": "1757000000000",
            "payload": {
                "mimeType": "multipart/alternative",
                "headers": [
                    {"name": "Subject", "value": "件名"},
                    {"name": "From", "value": "a@example.com"},
                ],
                "parts": [
                    {"mimeType": "text/html", "body": {"data": b64("<p>HTML版</p>")}},
                    {"mimeType": "text/plain", "body": {"data": b64("テキスト版")}},
                ],
            },
        }
        item = gmail_check.parse_message(message)
        self.assertEqual(item["body"], "テキスト版")

    def test_sender_parsing(self):
        item = gmail_check.parse_message(
            make_message(sender='"茨城県総務" <somu6@pref.ibaraki.lg.jp>')
        )
        self.assertEqual(item["sender_name"], "茨城県総務")
        self.assertEqual(item["sender_address"], "somu6@pref.ibaraki.lg.jp")
        self.assertEqual(item["sender"], "somu6@pref.ibaraki.lg.jp")

    def test_missing_body_falls_back_to_snippet(self):
        message = make_message(body="", snippet="スニペットのみ")
        item = gmail_check.parse_message(message)
        self.assertEqual(item["body"], "")
        self.assertTrue(item["body_available"])

    def test_no_body_and_no_snippet_flags_needs_eyes(self):
        item = gmail_check.parse_message(make_message(body="", snippet=""))
        self.assertFalse(item["body_available"])

    def test_dedupe_keeps_latest_per_thread(self):
        old = gmail_check.parse_message(
            make_message(msg_id="a", thread_id="t1", internal_date=1_000_000_000_000)
        )
        new = gmail_check.parse_message(
            make_message(msg_id="b", thread_id="t1", internal_date=1_757_000_000_000)
        )
        other = gmail_check.parse_message(make_message(msg_id="c", thread_id="t2"))
        result = gmail_check.dedupe_by_thread([old, new, other])
        ids = {i["id"] for i in result}
        self.assertEqual(len(result), 2)
        self.assertIn("b", ids)
        self.assertNotIn("a", ids)


class ExclusionTest(unittest.TestCase):
    def _item(self, **kwargs):
        return gmail_check.parse_message(make_message(**kwargs))

    def test_excludes_known_vendor_domains(self):
        for sender in ["uber@uber.com", "loop@autoway.co.jp", "news@bizocean.jp",
                       "b.beentjes@make.com", "info@zeal-c.jp"]:
            with self.subTest(sender=sender):
                item = self._item(sender=sender, subject="お知らせ")
                self.assertIsNotNone(gmail_check.exclusion_reason(item))

    def test_excludes_vendor_display_name(self):
        item = self._item(sender="楽楽精算 <noreply@example.net>", subject="お知らせ")
        self.assertIsNotNone(gmail_check.exclusion_reason(item))

    def test_excludes_webinar_subject(self):
        item = self._item(sender="info@example.net", subject="【無料セミナー】生成AI活用ウェビナー")
        self.assertIsNotNone(gmail_check.exclusion_reason(item))

    def test_excludes_bulk_mail_with_unsubscribe(self):
        item = self._item(
            sender="news@example.net",
            subject="製品アップデートのお知らせ",
            headers=[{"name": "List-Unsubscribe", "value": "<https://example.net/u>"}],
        )
        self.assertIsNotNone(gmail_check.exclusion_reason(item))

    def test_keeps_trusted_domain_even_with_unsubscribe(self):
        item = self._item(
            sender="sender@fts.jst.go.jp",
            subject="[ssh-sanka] 令和8年度SSH情報交換会の参加申込みについて（依頼）",
            headers=[{"name": "List-Unsubscribe", "value": "<https://jst.go.jp/u>"}],
        )
        self.assertIsNone(gmail_check.exclusion_reason(item))

    def test_keeps_school_mail(self):
        item = self._item(sender="y-ueoka435@toyo-ushiku.jp", subject="適性検査の件")
        self.assertIsNone(gmail_check.exclusion_reason(item))


class DepartmentTest(unittest.TestCase):
    def _detect(self, subject, body="", sender="a@example.com"):
        item = gmail_check.parse_message(
            make_message(subject=subject, body=body or "本文", sender=sender)
        )
        return gmail_check.detect_department(item)

    def test_ssh(self):
        self.assertEqual(
            self._detect("[ssh-sanka] JST事務連絡：令和8年度SSH情報交換会"), "SSH"
        )

    def test_management(self):
        self.assertEqual(self._detect("第5回経営会議の資料送付"), "経営会")

    def test_admissions(self):
        self.assertEqual(self._detect("2027適性検査（中学校）の件"), "入試広報")

    def test_fallback(self):
        self.assertEqual(self._detect("暑中お見舞い"), gmail_check.DEFAULT_DEPARTMENT)


class DeadlineAndPriorityTest(unittest.TestCase):
    def setUp(self):
        self.today = datetime(2026, 9, 12, 9, 0, 0)

    def test_finds_deadline_with_keyword_context(self):
        found = gmail_check.find_deadline("申込締切は10/1（木）です", self.today)
        self.assertEqual(found.date(), datetime(2026, 10, 1).date())

    def test_ignores_date_without_deadline_keyword(self):
        self.assertIsNone(gmail_check.find_deadline("9/20に運動会を開催します", self.today))

    def test_rolls_over_to_next_year(self):
        found = gmail_check.find_deadline("提出期限は1/15です", datetime(2026, 12, 20))
        self.assertEqual(found.date(), datetime(2027, 1, 15).date())

    def test_near_deadline_is_high(self):
        item = gmail_check.parse_message(
            make_message(
                subject="【JST事務連絡】9/15まで：資料提出のお願い",
                sender="sender@fts.jst.go.jp",
                body="SSH情報交換会の資料を9/15までに提出期限としてご提出ください。",
            )
        )
        department = gmail_check.detect_department(item)
        priority, deadline, _ = gmail_check.detect_priority(item, department, self.today)
        self.assertEqual(department, "SSH")
        self.assertEqual(priority, gmail_check.HIGH_PRIORITY)
        self.assertIsNotNone(deadline)

    def test_ssh_without_deadline_is_medium(self):
        item = gmail_check.parse_message(
            make_message(subject="SSH通信の配信について", body="SSHの近況をお知らせします。")
        )
        priority, _, _ = gmail_check.detect_priority(item, "SSH", self.today)
        self.assertEqual(priority, gmail_check.MEDIUM_PRIORITY)

    def test_plain_mail_is_low(self):
        item = gmail_check.parse_message(
            make_message(subject="資料の共有", body="ご参考までに共有します。")
        )
        priority, _, _ = gmail_check.detect_priority(
            item, gmail_check.DEFAULT_DEPARTMENT, self.today
        )
        self.assertEqual(priority, gmail_check.LOW_PRIORITY)


class OutputFormatTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 12, 9, 0, 0)
        messages = [
            make_message(
                msg_id="a",
                thread_id="ta",
                subject="[ssh-sanka] 【JST事務連絡】9/15まで：参加申込みについて（依頼）",
                sender="sender@fts.jst.go.jp",
                body="令和8年度SSH情報交換会の参加申込み締切は9/15です。",
            ),
            make_message(
                msg_id="b",
                thread_id="tb",
                subject="第31回附属校サミット開催のご案内",
                sender="f-summit@st.ritsumei.ac.jp",
                body="次回附属校サミットを開催します。ご参加ください。",
            ),
            make_message(
                msg_id="c",
                thread_id="tc",
                subject="お得なクーポンのご案内",
                sender="uber@uber.com",
                body="今すぐご利用ください。",
            ),
        ]
        parsed = [gmail_check.parse_message(m) for m in messages]
        self.actionable, self.excluded = gmail_check.classify(parsed, self.now)

    def test_classification_counts(self):
        self.assertEqual(len(self.actionable), 2)
        self.assertEqual(len(self.excluded), 1)
        self.assertEqual(self.actionable[0]["priority"], gmail_check.HIGH_PRIORITY)

    def test_markdown_structure(self):
        markdown = gmail_check.build_markdown(
            self.actionable, self.excluded, self.now,
            gmail_check.DEFAULT_ACCOUNT, gmail_check.DEFAULT_QUERY, 3,
        )
        self.assertIn("# Gmail 要確認事項まとめ（2026-09-12時点）", markdown)
        self.assertIn("更新日時：2026-09-12 09:00:00", markdown)
        self.assertIn("## 緊急度：高", markdown)
        self.assertIn("### 🔴 SSH関連", markdown)
        self.assertIn("- **件名：**", markdown)
        self.assertIn("- **差出人：** sender@fts.jst.go.jp", markdown)
        self.assertIn("## 除外（業者広告等）（1件）", markdown)
        self.assertIn("uber@uber.com", markdown)
        self.assertIn("## 確認状況", markdown)

    def test_markdown_with_no_mail(self):
        markdown = gmail_check.build_markdown(
            [], [], self.now, gmail_check.DEFAULT_ACCOUNT, gmail_check.DEFAULT_QUERY, 0
        )
        self.assertIn("要対応のメールはありません", markdown)
        self.assertIn("除外対象はありません", markdown)

    def test_cache_shape_matches_dashboard(self):
        cache = gmail_check.build_cache(
            self.actionable, self.now, gmail_check.DEFAULT_ACCOUNT,
            "Gmail_要確認事項まとめ_20260912.md",
        )
        self.assertEqual(
            sorted(cache.keys()),
            sorted(["updated", "account", "urgent_count", "items", "summary_file"]),
        )
        self.assertEqual(cache["updated"], "2026-09-12 09:00")
        self.assertEqual(cache["account"], "n-hatayama@toyo.jp")
        self.assertEqual(cache["urgent_count"], 2)
        self.assertEqual(cache["summary_file"], "Gmail_要確認事項まとめ_20260912.md")
        self.assertTrue(cache["items"][0]["label"].startswith("🔴 SSH"))
        for entry in cache["items"]:
            self.assertEqual(sorted(entry.keys()), ["label", "summary"])
            self.assertNotIn("\n", entry["summary"])

    def test_cache_item_limit(self):
        many = self.actionable * 20
        cache = gmail_check.build_cache(many, self.now, "x@example.com", "f.md")
        self.assertEqual(len(cache["items"]), gmail_check.CACHE_ITEM_LIMIT)

    def test_needs_eyes_label_when_body_missing(self):
        item = dict(self.actionable[0])
        item["body_available"] = False
        self.assertIn("要目視確認", gmail_check.item_label(item))


class FakeExecutable(object):
    def __init__(self, value):
        self._value = value

    def execute(self):
        return self._value


class FakeMessages(object):
    def __init__(self, messages):
        self._messages = {m["id"]: m for m in messages}
        self.queries = []

    def list(self, userId, q, maxResults):  # noqa: N803 (Google API の引数名に合わせる)
        self.queries.append((userId, q, maxResults))
        return FakeExecutable(
            {"messages": [{"id": mid} for mid in self._messages]}
        )

    def get(self, userId, id, format):  # noqa: A002,N803
        return FakeExecutable(self._messages[id])


class FakeUsers(object):
    def __init__(self, messages):
        self._messages = FakeMessages(messages)

    def messages(self):
        return self._messages


class FakeService(object):
    def __init__(self, messages):
        self._users = FakeUsers(messages)

    def users(self):
        return self._users


class EndToEndTest(unittest.TestCase):
    """認証以降を差し替えて run() を通し、ファイル生成まで確認する。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)
        self.messages = [
            make_message(
                msg_id="a",
                subject="[ssh-sanka] 【JST事務連絡】9/15まで：参加申込みについて（依頼）",
                sender="sender@fts.jst.go.jp",
                body="申込締切は9/15です。",
            ),
            make_message(
                msg_id="b",
                subject="お得なクーポン",
                sender="uber@uber.com",
                body="広告本文",
            ),
        ]
        self._orig_build = gmail_check.build_gmail_service
        gmail_check.build_gmail_service = lambda info, account: FakeService(self.messages)
        self.addCleanup(self._restore)

    def _restore(self):
        gmail_check.build_gmail_service = self._orig_build

    def _cleanup(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_run_writes_both_outputs(self):
        exit_code = gmail_check.main(
            [
                "--google-creds", '{"type": "service_account"}',
                "--project-dir", self.tmpdir,
            ]
        )
        self.assertEqual(exit_code, 0)

        today = datetime.now().strftime("%Y%m%d")
        md_path = os.path.join(
            self.tmpdir, "メール", "成果物",
            "Gmail_要確認事項まとめ_{}.md".format(today),
        )
        cache_path = os.path.join(
            self.tmpdir, "開発", "成果物", "scripts", "mail_cache.json"
        )
        self.assertTrue(os.path.isfile(md_path), md_path)
        self.assertTrue(os.path.isfile(cache_path), cache_path)

        with open(md_path, encoding="utf-8") as fh:
            markdown = fh.read()
        self.assertIn("SSH", markdown)
        self.assertIn("uber@uber.com", markdown)

        with open(cache_path, encoding="utf-8") as fh:
            cache = json.load(fh)
        self.assertEqual(cache["urgent_count"], 1)
        self.assertEqual(len(cache["items"]), 1)
        self.assertIn("SSH", cache["items"][0]["label"])

    def test_missing_credentials_returns_1(self):
        self.assertEqual(gmail_check.main(["--google-creds", ""]), 1)

    def test_api_error_returns_1(self):
        def boom(info, account):
            raise RuntimeError("gmail api exploded")

        gmail_check.build_gmail_service = boom
        exit_code = gmail_check.main(
            [
                "--google-creds", '{"type": "service_account"}',
                "--project-dir", self.tmpdir,
            ]
        )
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
