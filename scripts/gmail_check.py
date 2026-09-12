#!/usr/bin/env python3
"""Gmail 未読メールの要確認事項まとめを生成する（Google Gmail API 版）。

Claude CLI + Gmail MCP に依存していた mail-check.sh のバックエンド。
GitHub Actions のようなヘッドレス環境でも動くよう、Service Account 認証で
Gmail API を直接叩く。

使い方:
    python3 scripts/gmail_check.py \
        --google-creds "$GOOGLE_API_CREDS" \
        --project-dir "/path/to/noboruプロジェクト"

出力:
    {PROJECT_DIR}/メール/成果物/Gmail_要確認事項まとめ_{YYYYMMDD}.md
    {PROJECT_DIR}/開発/成果物/scripts/mail_cache.json

注意:
    - 読み取り専用（gmail.readonly）。既読化・削除・返信は一切行わない。
    - 取得したメール本文はローカルファイルにのみ保存する（外部送信なし）。
"""

import argparse
import base64
import html
import json
import os
import re
import sys
import traceback
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

DEFAULT_QUERY = "is:unread newer_than:3d"
DEFAULT_ACCOUNT = "n-hatayama@toyo.jp"
DEFAULT_MAX_RESULTS = 50

# JSON キャッシュに載せる要対応事項の上限（ダッシュボード表示用）。
CACHE_ITEM_LIMIT = 15

# ---------------------------------------------------------------------------
# 除外ルール（業者広告・セミナー勧誘）
# ---------------------------------------------------------------------------

# 送信元アドレス／ドメインに含まれていれば除外する文字列。
EXCLUDE_SENDER_PATTERNS = [
    "uber.com",
    "ubereats",
    "rakurakuseisan",
    "rakurakuseisan.jp",
    "rakuraku",
    "bizocean",
    "zoom.us",
    "zoom.com",
    "heygen",
    "make.com",
    "autoway.co.jp",
    "mingaku",
    "zeal-c.jp",
    "sansan.com",
    "freee.co.jp",
    "smbc-",
    "indeed.com",
    "mailchimp",
    "sendgrid.net",
    "benchmarkemail",
    "hubspot",
    "marketo",
    "salesforce.com",
    "amazon.co.jp",
    "rakuten.co.jp",
    "paypay",
    "no-reply@accounts.google.com",
]

# 送信者表示名に含まれていれば除外する文字列。
EXCLUDE_SENDER_NAME_PATTERNS = [
    "楽楽精算",
    "楽楽勤怠",
    "bizocean",
    "ビズオーシャン",
    "Uber",
    "Zoom",
    "HeyGen",
]

# 件名に含まれていれば除外する文字列。
EXCLUDE_SUBJECT_PATTERNS = [
    "ウェビナー",
    "webinar",
    "無料セミナー",
    "セミナーのご案内",
    "セミナー開催",
    "メルマガ",
    "メールマガジン",
    "キャンペーン",
    "クーポン",
    "割引",
    "【pr】",
    "[pr]",
    "＜pr＞",
    "広告",
    "モニター募集",
    "求人",
    "無料お試し",
    "無料トライアル",
    "期間限定",
    "お得な",
    "導入事例のご紹介",
    "資料ダウンロード",
    "サービスのご案内",
    "新機能のご紹介",
    "アップデート情報",
    "ご優待",
    "ポイント進呈",
    "今すぐチェック",
]

# 「信頼できる」ドメイン。ここからのメールは一括配信でも除外しない。
TRUSTED_SENDER_PATTERNS = [
    "toyo.jp",
    "toyo-ushiku.jp",
    ".go.jp",
    ".lg.jp",
    ".ac.jp",
    ".ed.jp",
    "jst.go.jp",
    "mext.go.jp",
]

# ---------------------------------------------------------------------------
# 部門判定
# ---------------------------------------------------------------------------

# (部門名, キーワード列) の順に評価し、最初に一致した部門を採用する。
DEPARTMENT_RULES = [
    ("SSH", ["ssh", "スーパーサイエンス", "科学技術振興機構", "jst", "ssh-sanka",
             "ssh-higashi", "課題研究", "サイエンス"]),
    ("経営会", ["経営会", "理事会", "評議員", "法人本部", "予算", "決算"]),
    ("入試広報", ["入試", "広報", "生徒募集", "募集要項", "オープンスクール",
                  "学校説明会", "適性検査", "エデュコン", "願書", "受験"]),
    ("通信制", ["通信制", "サポート校", "広域通信"]),
    ("教務", ["時間割", "教務", "成績", "定期考査", "カリキュラム", "履修"]),
    ("行事・予定", ["日程調整", "開催のご案内", "会議", "打合せ", "打ち合わせ",
                    "研修会", "サミット", "総会", "出張"]),
    ("総務・事務", ["事務連絡", "総務", "人事", "勤怠", "施設", "備品"]),
]

DEFAULT_DEPARTMENT = "その他"

# ---------------------------------------------------------------------------
# 優先度判定
# ---------------------------------------------------------------------------

URGENT_WORDS = ["至急", "緊急", "本日中", "明日まで", "早急", "リマインド", "督促",
                "未提出", "再送"]
DEADLINE_WORDS = ["締切", "〆切", "締め切り", "期限", "必着", "まで", "期日",
                  "提出", "回答", "申込", "申し込み", "依頼", "照会"]

HIGH_PRIORITY = "high"
MEDIUM_PRIORITY = "medium"
LOW_PRIORITY = "low"

PRIORITY_ORDER = [HIGH_PRIORITY, MEDIUM_PRIORITY, LOW_PRIORITY]
PRIORITY_LABEL = {
    HIGH_PRIORITY: "高",
    MEDIUM_PRIORITY: "中",
    LOW_PRIORITY: "低",
}
PRIORITY_EMOJI = {
    HIGH_PRIORITY: "🔴",
    MEDIUM_PRIORITY: "🟡",
    LOW_PRIORITY: "🟢",
}
# 本文が取得できなかったメールに付ける印（既存まとめの記法に合わせる）。
NEEDS_EYES_EMOJI = "🔶"


# ---------------------------------------------------------------------------
# 認証・API クライアント
# ---------------------------------------------------------------------------

def load_credentials_info(raw):
    """--google-creds の値から Service Account の dict を得る。

    受け付ける形式:
      1. JSON 文字列そのもの
      2. base64 エンコードされた JSON
      3. JSON ファイルへのパス
    """
    if raw is None:
        raise ValueError("Service Account の認証情報が空です")

    value = raw.strip()
    if not value:
        raise ValueError("Service Account の認証情報が空です")

    # 1. そのまま JSON
    if value.startswith("{"):
        return json.loads(value)

    # 3. ファイルパス
    if os.path.isfile(value):
        with open(value, "r", encoding="utf-8") as fh:
            return json.load(fh)

    # 2. base64
    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
    except Exception:
        raise ValueError(
            "Service Account の認証情報を解釈できません"
            "（JSON 文字列 / base64 / ファイルパスのいずれかを指定してください）"
        )
    return json.loads(decoded)


def build_credentials(creds_info, impersonate):
    """認証情報の dict から Credentials を組み立てる。

    2 種類の形式に対応する:
      - Service Account（"type": "service_account"）:
        Gmail のメールボックスを持たないため、ドメイン全体の委任
        （domain-wide delegation、Workspace 管理者の設定が必要）でなりすます。
      - OAuth ユーザー認証（"refresh_token" を含む）:
        本人が一度だけ同意して得たリフレッシュトークンを使う。
        管理者権限が不要な代わりに、事前に一度ローカルで認可フローを
        実行してリフレッシュトークンを発行しておく必要がある
        （scripts/oauth_authorize.py 参照）。
    """
    if "refresh_token" in creds_info:
        from google.oauth2.credentials import Credentials

        return Credentials(
            token=None,
            refresh_token=creds_info["refresh_token"],
            token_uri=creds_info.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=creds_info["client_id"],
            client_secret=creds_info["client_secret"],
            scopes=SCOPES,
        )

    from google.oauth2 import service_account

    credentials = service_account.Credentials.from_service_account_info(
        creds_info, scopes=SCOPES
    )
    if impersonate:
        credentials = credentials.with_subject(impersonate)
    return credentials


def build_gmail_service(creds_info, impersonate):
    """認証情報から Gmail API クライアントを組み立てる。"""
    # 依存ライブラリはここで import する（純粋関数のテストを依存なしで動かすため）。
    from googleapiclient.discovery import build

    credentials = build_credentials(creds_info, impersonate)
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def fetch_messages(service, user_id, query, max_results):
    """クエリに一致する未読メールを取得して、パース済み dict のリストで返す。"""
    listed = (
        service.users()
        .messages()
        .list(userId=user_id, q=query, maxResults=max_results)
        .execute()
    )
    refs = listed.get("messages", []) or []

    messages = []
    for ref in refs[:max_results]:
        detail = (
            service.users()
            .messages()
            .get(userId=user_id, id=ref["id"], format="full")
            .execute()
        )
        messages.append(detail)
    return messages


# ---------------------------------------------------------------------------
# メールのパース
# ---------------------------------------------------------------------------

def header_value(message, name):
    headers = (message.get("payload") or {}).get("headers") or []
    lowered = name.lower()
    for header in headers:
        if (header.get("name") or "").lower() == lowered:
            return header.get("value") or ""
    return ""


def decode_body_data(data):
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except Exception:
        return ""


def strip_html(text):
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"(?s)<br\s*/?>", "\n", text)
    text = re.sub(r"(?s)</p>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return html.unescape(text)


def extract_body(payload):
    """payload を再帰的に辿って本文テキストを取り出す。"""
    if not payload:
        return ""

    mime_type = payload.get("mimeType") or ""
    body = payload.get("body") or {}
    parts = payload.get("parts") or []

    if mime_type == "text/plain" and body.get("data"):
        return decode_body_data(body["data"])

    if parts:
        # text/plain を優先し、無ければ text/html を使う。
        plain = ""
        html_text = ""
        for part in parts:
            found = extract_body(part)
            if not found:
                continue
            part_mime = part.get("mimeType") or ""
            if part_mime.startswith("multipart/"):
                plain = plain or found
            elif part_mime == "text/plain":
                plain = plain or found
            elif part_mime == "text/html":
                html_text = html_text or found
        if plain:
            return plain
        if html_text:
            return strip_html(html_text)
        return ""

    if mime_type == "text/html" and body.get("data"):
        return strip_html(decode_body_data(body["data"]))

    return ""


def normalize_text(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t　]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def parse_sender(raw_from):
    """From ヘッダーを (表示名, メールアドレス) に分解する。"""
    match = re.search(r"<([^>]+)>", raw_from or "")
    if match:
        address = match.group(1).strip()
        name = (raw_from[: match.start()] or "").strip().strip('"').strip()
        return name, address
    value = (raw_from or "").strip()
    if "@" in value:
        return "", value
    return value, ""


def received_at(message):
    """internalDate（ミリ秒エポック）をローカル時刻の datetime に変換する。"""
    raw = message.get("internalDate")
    if not raw:
        return None
    try:
        return datetime.fromtimestamp(int(raw) / 1000.0)
    except (TypeError, ValueError, OSError):
        return None


def parse_message(message):
    """Gmail API の message を扱いやすい dict にする。"""
    body = normalize_text(extract_body(message.get("payload")))
    snippet = html.unescape(message.get("snippet") or "").strip()
    sender_name, sender_address = parse_sender(header_value(message, "From"))

    return {
        "id": message.get("id", ""),
        "thread_id": message.get("threadId", ""),
        "subject": (header_value(message, "Subject") or "(件名なし)").strip(),
        "sender_name": sender_name,
        "sender_address": sender_address,
        "sender": sender_address or sender_name or "(送信元不明)",
        "date": received_at(message),
        "snippet": snippet,
        "body": body,
        "list_unsubscribe": bool(header_value(message, "List-Unsubscribe")),
        "precedence": header_value(message, "Precedence").lower(),
        "body_available": bool(body or snippet),
    }


def dedupe_by_thread(items):
    """同一スレッドは最新の 1 通だけ残す。"""
    latest = {}
    for item in items:
        key = item.get("thread_id") or item.get("id")
        current = latest.get(key)
        if current is None:
            latest[key] = item
            continue
        if _sort_key(item) > _sort_key(current):
            latest[key] = item
    return sorted(latest.values(), key=_sort_key, reverse=True)


def _sort_key(item):
    date = item.get("date")
    return date or datetime.min


# ---------------------------------------------------------------------------
# 除外判定
# ---------------------------------------------------------------------------

def is_trusted_sender(item):
    sender = (item.get("sender_address") or "").lower()
    return any(pattern in sender for pattern in TRUSTED_SENDER_PATTERNS)


def exclusion_reason(item):
    """除外すべきメールなら理由（文字列）を返す。対応必要なら None。"""
    sender = (item.get("sender_address") or "").lower()
    sender_name = item.get("sender_name") or ""
    subject = item.get("subject") or ""
    subject_lower = subject.lower()

    for pattern in EXCLUDE_SENDER_PATTERNS:
        if pattern in sender:
            return "業者・広告配信元({})".format(pattern)

    for pattern in EXCLUDE_SENDER_NAME_PATTERNS:
        if pattern.lower() in sender_name.lower():
            return "業者・広告配信元({})".format(pattern)

    if is_trusted_sender(item):
        # 学内・官公庁ドメインは一括配信でも除外しない。
        return None

    for pattern in EXCLUDE_SUBJECT_PATTERNS:
        if pattern in subject_lower or pattern in subject:
            return "広告・セミナー勧誘の件名({})".format(pattern)

    if item.get("list_unsubscribe") or item.get("precedence") in ("bulk", "list"):
        return "一括配信メール(配信停止リンク付き)"

    return None


# ---------------------------------------------------------------------------
# 部門・優先度・要約
# ---------------------------------------------------------------------------

def detect_department(item):
    haystack = "{}\n{}\n{}".format(
        item.get("subject", ""), item.get("sender_address", ""),
        (item.get("body") or item.get("snippet") or "")[:600],
    ).lower()

    for department, keywords in DEPARTMENT_RULES:
        for keyword in keywords:
            if keyword.lower() in haystack:
                return department
    return DEFAULT_DEPARTMENT


_DEADLINE_DATE_RE = re.compile(
    r"(?:(\d{4})[年/\-])?(\d{1,2})[月/\-](\d{1,2})日?"
)


def find_deadline(text, today):
    """本文・件名から締切らしき日付を拾う。見つからなければ None。"""
    if not text:
        return None

    candidates = []
    for match in _DEADLINE_DATE_RE.finditer(text):
        # 日付の周辺に締切系の語があるものだけを候補にする。
        start = max(0, match.start() - 25)
        end = min(len(text), match.end() + 25)
        context = text[start:end]
        if not any(word in context for word in DEADLINE_WORDS):
            continue

        year, month, day = match.groups()
        try:
            month_i, day_i = int(month), int(day)
            if not (1 <= month_i <= 12 and 1 <= day_i <= 31):
                continue
            if year:
                date = datetime(int(year), month_i, day_i)
            else:
                date = datetime(today.year, month_i, day_i)
                # 年をまたぐ締切（例: 1月の締切を 12 月に受信）への対応。
                if (date.date() - today.date()).days < -60:
                    date = datetime(today.year + 1, month_i, day_i)
        except ValueError:
            continue
        candidates.append(date)

    if not candidates:
        return None

    future = [d for d in candidates if d.date() >= today.date()]
    return min(future) if future else max(candidates)


def detect_priority(item, department, today):
    """優先度（high / medium / low）と判定理由を返す。"""
    subject = item.get("subject", "")
    body = (item.get("body") or item.get("snippet") or "")[:2000]
    text = "{}\n{}".format(subject, body)

    reasons = []
    deadline = find_deadline(text, today)
    if deadline:
        days_left = (deadline.date() - today.date()).days
        reasons.append("締切 {}".format(deadline.strftime("%-m/%-d")))
    else:
        days_left = None

    has_urgent_word = any(word in text for word in URGENT_WORDS)
    if has_urgent_word:
        reasons.append("至急・督促の表現あり")

    priority = LOW_PRIORITY

    if department in ("SSH", "経営会"):
        priority = MEDIUM_PRIORITY
    elif department in ("入試広報", "通信制", "教務"):
        priority = MEDIUM_PRIORITY if deadline else LOW_PRIORITY

    if days_left is not None and days_left <= 7:
        priority = HIGH_PRIORITY
    elif days_left is not None and department in ("SSH", "経営会"):
        priority = HIGH_PRIORITY
    elif has_urgent_word:
        priority = HIGH_PRIORITY if department != DEFAULT_DEPARTMENT else MEDIUM_PRIORITY

    return priority, deadline, reasons


def summarize(item, limit=140):
    """本文の先頭から 1 行要約を作る。"""
    source = item.get("body") or item.get("snippet") or ""
    lines = []
    for line in source.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 引用・定型の区切り行は飛ばす。
        if re.match(r"^[-=_*─-╿]{3,}$", line):
            continue
        if line.startswith(">"):
            continue
        lines.append(line)
        if sum(len(x) for x in lines) >= limit:
            break

    text = " ".join(lines).strip()
    if not text:
        return "(本文を取得できませんでした)"
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


def classify(items, today):
    """メールを「要対応」と「除外」に振り分けて、必要な属性を付与する。"""
    actionable = []
    excluded = []

    for item in items:
        reason = exclusion_reason(item)
        if reason:
            item = dict(item)
            item["exclusion_reason"] = reason
            excluded.append(item)
            continue

        item = dict(item)
        department = detect_department(item)
        priority, deadline, reasons = detect_priority(item, department, today)
        item["department"] = department
        item["priority"] = priority
        item["deadline"] = deadline
        item["priority_reasons"] = reasons
        item["summary"] = summarize(item)
        actionable.append(item)

    # 優先度順 → 受信が新しい順。
    actionable.sort(key=lambda x: _sort_key(x), reverse=True)
    actionable.sort(key=lambda x: PRIORITY_ORDER.index(x["priority"]))
    return actionable, excluded


def item_emoji(item):
    if not item.get("body_available", True):
        return NEEDS_EYES_EMOJI
    return PRIORITY_EMOJI[item["priority"]]


def item_label(item):
    """JSON キャッシュ用のラベル（例: "🔴 SSH"）。"""
    if not item.get("body_available", True):
        return "{} {}(要目視確認)".format(NEEDS_EYES_EMOJI, item["department"])
    return "{} {}".format(PRIORITY_EMOJI[item["priority"]], item["department"])


def item_one_liner(item):
    """JSON キャッシュ用の 1 行要約。"""
    parts = [item.get("subject", "").strip()]
    deadline = item.get("deadline")
    if deadline:
        parts.append("締切{}".format(deadline.strftime("%-m/%-d")))
    summary = item.get("summary", "")
    if summary and summary != "(本文を取得できませんでした)":
        parts.append(summary)
    else:
        parts.append("本文取得不可のため Gmail で目視確認推奨")

    text = "、".join(p for p in parts if p)
    if len(text) > 160:
        text = text[:159] + "…"
    return text


# ---------------------------------------------------------------------------
# 出力
# ---------------------------------------------------------------------------

def format_datetime(value):
    return value.strftime("%Y-%m-%d %H:%M") if value else "(日時不明)"


def build_markdown(actionable, excluded, now, account, query, total_count):
    lines = []
    lines.append("# Gmail 要確認事項まとめ（{}時点）".format(now.strftime("%Y-%m-%d")))
    lines.append("")
    lines.append("更新日時：{}".format(now.strftime("%Y-%m-%d %H:%M:%S")))
    lines.append("")
    lines.append(
        "出典: Gmail（{}）検索結果（`{}`、{}件）より。".format(account, query, total_count)
    )
    lines.append("")

    for priority in PRIORITY_ORDER:
        bucket = [i for i in actionable if i["priority"] == priority]
        if not bucket:
            continue
        lines.append("## 緊急度：{}（{}件）".format(PRIORITY_LABEL[priority], len(bucket)))
        lines.append("")

        # 部門ごとにまとめる（出現順を維持）。
        departments = []
        for item in bucket:
            if item["department"] not in departments:
                departments.append(item["department"])

        for department in departments:
            members = [i for i in bucket if i["department"] == department]
            lines.append("### {} {}関連".format(PRIORITY_EMOJI[priority], department))
            lines.append("")
            for item in members:
                prefix = "{} ".format(NEEDS_EYES_EMOJI) if not item.get(
                    "body_available", True) else ""
                lines.append("- **件名：** {}{}".format(prefix, item["subject"]))
                lines.append("  - **差出人：** {}".format(item["sender"]))
                lines.append("  - **受信：** {}".format(format_datetime(item.get("date"))))
                if item.get("deadline"):
                    lines.append(
                        "  - **締切：** {}".format(item["deadline"].strftime("%Y-%m-%d"))
                    )
                lines.append("  - **内容：** {}".format(item["summary"]))
                if item.get("priority_reasons"):
                    lines.append(
                        "  - **判定理由：** {}".format("、".join(item["priority_reasons"]))
                    )
                lines.append("")
    if not actionable:
        lines.append("## 要対応事項")
        lines.append("")
        lines.append("- 要対応のメールはありません。")
        lines.append("")

    lines.append("## 除外（業者広告等）（{}件）".format(len(excluded)))
    lines.append("")
    if excluded:
        for item in excluded:
            lines.append(
                "- {}（{}）— {}".format(
                    item["subject"], item["sender"], item["exclusion_reason"]
                )
            )
    else:
        lines.append("- 除外対象はありません。")
    lines.append("")

    urgent = len([i for i in actionable if i["priority"] == HIGH_PRIORITY])
    unreadable = len([i for i in actionable if not i.get("body_available", True)])
    lines.append("## 確認状況")
    lines.append("")
    lines.append(
        "直近の未読メール{}件のうち{}件を業者広告・セミナー勧誘等として除外し、"
        "{}件を要対応として整理した（うち緊急度：高 {}件）。".format(
            total_count, len(excluded), len(actionable), urgent
        )
    )
    if unreadable:
        lines.append("")
        lines.append(
            "{}件は本文を取得できなかったため、{} を付けている。Gmail 上での目視確認を推奨する。".format(
                unreadable, NEEDS_EYES_EMOJI
            )
        )
    lines.append("")
    lines.append("---")
    lines.append("※ このまとめはGmail検索時点のスナップショットです。"
                 "最新化する場合は再度Gmailを確認してください。")
    lines.append("")
    return "\n".join(lines)


def build_cache(actionable, now, account, summary_file):
    items = []
    for item in actionable[:CACHE_ITEM_LIMIT]:
        items.append({"label": item_label(item), "summary": item_one_liner(item)})

    return {
        "updated": now.strftime("%Y-%m-%d %H:%M"),
        "account": account,
        # ダッシュボードの「要対応 N件」表示に使う値。
        "urgent_count": len(actionable),
        "items": items,
        "summary_file": summary_file,
    }


def write_text(path, text):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def write_json(path, payload):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
        fh.write("\n")


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Gmail の未読メールから要確認事項まとめを生成する"
    )
    parser.add_argument(
        "--google-creds",
        default=os.environ.get("GOOGLE_API_CREDS", ""),
        help="Service Account JSON（JSON 文字列 / base64 / ファイルパス）",
    )
    parser.add_argument(
        "--project-dir",
        default=os.environ.get("PROJECT_DIR", os.getcwd()),
        help="出力先のプロジェクトルート",
    )
    parser.add_argument(
        "--account",
        default=os.environ.get("GMAIL_ACCOUNT", DEFAULT_ACCOUNT),
        help="対象 Gmail アカウント（Service Account の委任先）",
    )
    parser.add_argument(
        "--query",
        default=os.environ.get("GMAIL_QUERY", DEFAULT_QUERY),
        help="Gmail 検索クエリ",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=int(os.environ.get("GMAIL_MAX_RESULTS", DEFAULT_MAX_RESULTS)),
        help="取得する最大メール数",
    )
    return parser.parse_args(argv)


def run(args):
    now = datetime.now()

    creds_info = load_credentials_info(args.google_creds)
    service = build_gmail_service(creds_info, args.account)
    raw_messages = fetch_messages(service, "me", args.query, args.max_results)

    parsed = [parse_message(m) for m in raw_messages]
    parsed = dedupe_by_thread(parsed)
    actionable, excluded = classify(parsed, now)

    summary_file = "Gmail_要確認事項まとめ_{}.md".format(now.strftime("%Y%m%d"))
    markdown_path = os.path.join(args.project_dir, "メール", "成果物", summary_file)
    cache_path = os.path.join(
        args.project_dir, "開発", "成果物", "scripts", "mail_cache.json"
    )

    markdown = build_markdown(
        actionable, excluded, now, args.account, args.query, len(parsed)
    )
    write_text(markdown_path, markdown)

    cache = build_cache(actionable, now, args.account, summary_file)
    write_json(cache_path, cache)

    print(
        "{} gmail_check: {}件取得 / 要対応{}件 / 除外{}件".format(
            now.strftime("%Y-%m-%d %H:%M:%S"), len(parsed), len(actionable), len(excluded)
        )
    )
    print("  markdown: {}".format(markdown_path))
    print("  cache   : {}".format(cache_path))
    return 0


def main(argv=None):
    args = parse_args(argv)
    if not args.google_creds:
        print(
            "Error: Service Account の認証情報が指定されていません"
            "（--google-creds もしくは環境変数 GOOGLE_API_CREDS）",
            file=sys.stderr,
        )
        return 1
    try:
        return run(args)
    except Exception as exc:  # noqa: BLE001 - CI ではスタックトレースを残して終了する
        traceback.print_exc()
        print_hint(exc, args)
        return 1


def print_hint(exc, args):
    """よくある失敗にだけ、次の一手が分かるヒントを添える。"""
    text = "{}".format(exc)
    if "unauthorized_client" in text or "Client is unauthorized" in text:
        print(
            "Hint: Service Account のドメイン全体の委任（domain-wide delegation）が未設定の可能性があります。"
            " Google Workspace 管理コンソールで、クライアント ID に対して"
            " '{}' のスコープを許可してください。".format(SCOPES[0]),
            file=sys.stderr,
        )
    elif "Precondition check failed" in text or "failedPrecondition" in text:
        print(
            "Hint: 委任先ユーザー（--account {}）が存在しないか、Gmail が有効化されていない可能性があります。"
            .format(args.account),
            file=sys.stderr,
        )
    elif "accessNotConfigured" in text or "has not been used in project" in text:
        print(
            "Hint: Google Cloud プロジェクトで Gmail API が有効化されていない可能性があります。",
            file=sys.stderr,
        )
    elif "invalid_grant" in text:
        print(
            "Hint: OAuth のリフレッシュトークンが失効している可能性があります。"
            " scripts/oauth_authorize.py を再実行して発行し直してください"
            "（OAuth 同意画面の公開ステータスが「テスト」のままだと 7 日で失効します）。",
            file=sys.stderr,
        )


if __name__ == "__main__":
    sys.exit(main())
