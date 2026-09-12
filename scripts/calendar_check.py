#!/usr/bin/env python3
import sys
import json
import argparse
import base64
import traceback
import os
from datetime import datetime, timedelta
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


def load_credentials(creds_input: str) -> dict:
    creds_dict = creds_input.strip()

    if creds_dict.startswith('{'):
        return json.loads(creds_dict)

    try:
        decoded = base64.b64decode(creds_dict)
        return json.loads(decoded)
    except Exception:
        pass

    try:
        with open(creds_dict, 'r') as f:
            return json.load(f)
    except Exception:
        pass

    raise ValueError(
        "Invalid Service Account credentials. Expected JSON string, base64, or file path."
    )


def build_calendar_client(creds_dict: dict, account: str):
    scopes = ['https://www.googleapis.com/auth/calendar.readonly']
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=scopes
    )
    credentials = credentials.with_subject(account)
    return build('calendar', 'v3', credentials=credentials)


def format_time_label(start_dt, end_dt) -> str:
    start_time = start_dt.strftime('%H:%M')
    end_time = end_dt.strftime('%H:%M')
    return f"{start_time}〜{end_time}"


def get_calendar_events(client, days_ahead: int = 21) -> list:
    today = datetime.utcnow()
    tomorrow = today + timedelta(days=1)
    end_date = today + timedelta(days=days_ahead)

    events_result = client.events().list(
        calendarId='primary',
        timeMin=today.isoformat() + 'Z',
        timeMax=end_date.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime',
        maxResults=100
    ).execute()

    events = events_result.get('items', [])
    formatted_events = []

    for event in events:
        start = event.get('start', {})
        end = event.get('end', {})

        start_str = start.get('dateTime') or start.get('date')
        end_str = end.get('dateTime') or end.get('date')

        if not start_str or not end_str:
            continue

        summary = event.get('summary', '')
        location = event.get('location', '')

        is_all_day = 'date' in start

        if is_all_day:
            start_date = datetime.strptime(start_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_str, '%Y-%m-%d')
            formatted_events.append({
                'start': start_date.strftime('%Y-%m-%d'),
                'end_exclusive': end_date.strftime('%Y-%m-%d'),
                'time_label': None,
                'summary': summary,
                'location': location
            })
        else:
            start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            formatted_events.append({
                'start': start_dt.strftime('%Y-%m-%d'),
                'end_exclusive': (start_dt + timedelta(days=1)).strftime('%Y-%m-%d'),
                'time_label': format_time_label(start_dt, end_dt),
                'summary': summary,
                'location': location
            })

    return formatted_events


def write_calendar_cache(events: list, output_path: str, account: str):
    cache = {
        'calendar': account,
        'events': events
    }

    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def run(
    google_creds: str,
    project_dir: str,
    account: str = 'n-hatayama@toyo.jp',
    days_ahead: int = 21
):
    try:
        creds_dict = load_credentials(google_creds)
        client = build_calendar_client(creds_dict, account)
        events = get_calendar_events(client, days_ahead)

        output_path = f"{project_dir}/開発/成果物/scripts/calendar_events_raw.json"
        write_calendar_cache(events, output_path, account)

        print(f"Calendar events saved to {output_path} ({len(events)} events)")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

        if 'unauthorized_client' in str(e):
            print(
                "Hint: Service Account domain-wide delegation not configured. "
                "Enable in Google Workspace Admin console: "
                "Security → API controls → Manage all → Add new → "
                "Client ID: [SA client ID], Scopes: https://www.googleapis.com/auth/calendar.readonly",
                file=sys.stderr
            )
        elif 'Precondition check failed' in str(e):
            print(
                "Hint: Google Workspace domain not configured for this Service Account. "
                "Verify domain settings in Google Cloud project.",
                file=sys.stderr
            )
        elif 'accessNotConfigured' in str(e):
            print(
                "Hint: Calendar API not enabled. "
                "Enable in Google Cloud Console: APIs & Services → Enable APIs and Services → Calendar API",
                file=sys.stderr
            )

        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch Google Calendar events and save to JSON cache')
    parser.add_argument('--google-creds', help='Service Account JSON (string/base64/path)')
    parser.add_argument('--project-dir', help='Project directory')
    parser.add_argument('--account', default='n-hatayama@toyo.jp', help='Gmail account to impersonate')
    parser.add_argument('--days-ahead', type=int, default=21, help='Days to look ahead')

    args = parser.parse_args()

    google_creds = args.google_creds or os.environ.get('GOOGLE_API_CREDS')
    project_dir = args.project_dir or os.environ.get('PROJECT_DIR', '.')

    if not google_creds:
        print("Error: GOOGLE_API_CREDS environment variable is not set", file=sys.stderr)
        sys.exit(1)

    run(google_creds, project_dir, args.account, args.days_ahead)
