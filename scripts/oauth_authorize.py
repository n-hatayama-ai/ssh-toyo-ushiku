#!/usr/bin/env python3
"""OAuth 2.0 のユーザー認可フローをローカルで一度だけ実行し、
gmail_check.py / calendar_check.py がそのまま読み込める形式の
認証情報 JSON（refresh_token を含む）を発行する。

Google Workspace の domain-wide delegation（管理者権限）が使えない場合の代替手段。
本人（--account で指定するアカウント）がブラウザで一度だけ同意するだけで済む。

使い方:
    python3 scripts/oauth_authorize.py \\
        --client-secret ~/Downloads/client_secret_xxxx.json \\
        --output oauth_credentials.json

--client-secret は Google Cloud Console で作成した
OAuth クライアント ID（アプリケーションの種類: デスクトップアプリ）の
JSON ファイル。
"""

import argparse
import json
import sys

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--client-secret",
        required=True,
        help="OAuth クライアント ID の JSON ファイルパス（デスクトップアプリ種別）",
    )
    parser.add_argument(
        "--output",
        default="oauth_credentials.json",
        help="発行した認証情報の書き出し先（既定: oauth_credentials.json）",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    # 依存ライブラリはここで import する（引数パースだけなら依存なしで動かせるようにするため）。
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(args.client_secret, SCOPES)
    # ローカルに一時的な HTTP サーバーを立てて、ブラウザでの認可完了を受け取る。
    credentials = flow.run_local_server(port=0)

    output = {
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
    }

    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2)

    print("認証情報を {} に書き出しました。".format(args.output))
    print(
        "この内容を GitHub Secret に登録してください:\n"
        "  gh secret set GOOGLE_API_SERVICE_ACCOUNT_JSON < {}".format(args.output)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
