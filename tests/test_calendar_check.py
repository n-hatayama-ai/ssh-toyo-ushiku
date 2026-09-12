import unittest
import json
import base64
import os
import sys
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import calendar_check


class TestLoadCredentials(unittest.TestCase):
    def test_load_json_string(self):
        creds_dict = {"type": "service_account", "project_id": "test"}
        creds_str = json.dumps(creds_dict)
        result = calendar_check.load_credentials(creds_str)
        self.assertEqual(result, creds_dict)

    def test_load_base64(self):
        creds_dict = {"type": "service_account", "project_id": "test"}
        creds_str = base64.b64encode(json.dumps(creds_dict).encode()).decode()
        result = calendar_check.load_credentials(creds_str)
        self.assertEqual(result, creds_dict)

    def test_load_file_path(self):
        creds_dict = {"type": "service_account", "project_id": "test"}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(creds_dict, f)
            f.flush()
            result = calendar_check.load_credentials(f.name)
            self.assertEqual(result, creds_dict)
        os.unlink(f.name)

    def test_invalid_credentials(self):
        with self.assertRaises(ValueError):
            calendar_check.load_credentials("invalid_creds")


class TestFormatTimeLabel(unittest.TestCase):
    def test_format_time_label(self):
        start = datetime(2026, 9, 12, 10, 30)
        end = datetime(2026, 9, 12, 15, 45)
        result = calendar_check.format_time_label(start, end)
        self.assertEqual(result, "10:30〜15:45")

    def test_format_time_label_midnight(self):
        start = datetime(2026, 9, 12, 0, 0)
        end = datetime(2026, 9, 12, 23, 59)
        result = calendar_check.format_time_label(start, end)
        self.assertEqual(result, "00:00〜23:59")


class TestGetCalendarEvents(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()

    def test_get_all_day_event(self):
        self.mock_client.events().list().execute.return_value = {
            'items': [
                {
                    'start': {'date': '2026-09-12'},
                    'end': {'date': '2026-09-13'},
                    'summary': '終日イベント',
                    'location': ''
                }
            ]
        }
        result = calendar_check.get_calendar_events(self.mock_client, days_ahead=21)
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]['time_label'])
        self.assertEqual(result[0]['summary'], '終日イベント')
        self.assertEqual(result[0]['start'], '2026-09-12')
        self.assertEqual(result[0]['end_exclusive'], '2026-09-13')

    def test_get_timed_event(self):
        self.mock_client.events().list().execute.return_value = {
            'items': [
                {
                    'start': {'dateTime': '2026-09-12T10:30:00Z'},
                    'end': {'dateTime': '2026-09-12T15:45:00Z'},
                    'summary': '時刻指定イベント',
                    'location': '会議室A'
                }
            ]
        }
        result = calendar_check.get_calendar_events(self.mock_client, days_ahead=21)
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0]['time_label'])
        self.assertEqual(result[0]['summary'], '時刻指定イベント')
        self.assertEqual(result[0]['location'], '会議室A')

    def test_get_multiple_events(self):
        self.mock_client.events().list().execute.return_value = {
            'items': [
                {
                    'start': {'date': '2026-09-12'},
                    'end': {'date': '2026-09-13'},
                    'summary': 'Event 1',
                    'location': ''
                },
                {
                    'start': {'dateTime': '2026-09-12T10:00:00Z'},
                    'end': {'dateTime': '2026-09-12T11:00:00Z'},
                    'summary': 'Event 2',
                    'location': ''
                }
            ]
        }
        result = calendar_check.get_calendar_events(self.mock_client, days_ahead=21)
        self.assertEqual(len(result), 2)

    def test_get_no_events(self):
        self.mock_client.events().list().execute.return_value = {'items': []}
        result = calendar_check.get_calendar_events(self.mock_client, days_ahead=21)
        self.assertEqual(len(result), 0)

    def test_event_missing_location(self):
        self.mock_client.events().list().execute.return_value = {
            'items': [
                {
                    'start': {'date': '2026-09-12'},
                    'end': {'date': '2026-09-13'},
                    'summary': 'No location event'
                }
            ]
        }
        result = calendar_check.get_calendar_events(self.mock_client, days_ahead=21)
        self.assertEqual(result[0]['location'], '')

    def test_event_missing_summary(self):
        self.mock_client.events().list().execute.return_value = {
            'items': [
                {
                    'start': {'date': '2026-09-12'},
                    'end': {'date': '2026-09-13'},
                    'location': 'somewhere'
                }
            ]
        }
        result = calendar_check.get_calendar_events(self.mock_client, days_ahead=21)
        self.assertEqual(result[0]['summary'], '')

    def test_skip_event_missing_dates(self):
        self.mock_client.events().list().execute.return_value = {
            'items': [
                {
                    'summary': 'No dates event',
                    'location': ''
                }
            ]
        }
        result = calendar_check.get_calendar_events(self.mock_client, days_ahead=21)
        self.assertEqual(len(result), 0)

    def test_api_call_with_correct_range(self):
        self.mock_client.events().list().execute.return_value = {'items': []}
        calendar_check.get_calendar_events(self.mock_client, days_ahead=21)

        call_args = self.mock_client.events().list.call_args
        self.assertEqual(call_args[1]['calendarId'], 'primary')
        self.assertIn('timeMin', call_args[1])
        self.assertIn('timeMax', call_args[1])


class TestWriteCalendarCache(unittest.TestCase):
    def test_write_cache_creates_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'subdir1', 'subdir2', 'cache.json')
            events = [
                {
                    'start': '2026-09-12',
                    'end_exclusive': '2026-09-13',
                    'time_label': None,
                    'summary': 'Test Event',
                    'location': ''
                }
            ]
            calendar_check.write_calendar_cache(events, output_path, 'test@example.com')

            self.assertTrue(os.path.exists(output_path))
            with open(output_path, 'r') as f:
                data = json.load(f)
                self.assertEqual(data['calendar'], 'test@example.com')
                self.assertEqual(len(data['events']), 1)

    def test_write_cache_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'cache.json')
            events = [
                {
                    'start': '2026-09-12',
                    'end_exclusive': '2026-09-13',
                    'time_label': '10:00〜15:00',
                    'summary': 'イベント',
                    'location': '会議室'
                }
            ]
            calendar_check.write_calendar_cache(events, output_path, 'test@example.com')

            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.assertEqual(data['calendar'], 'test@example.com')
                self.assertEqual(data['events'][0]['summary'], 'イベント')
                self.assertEqual(data['events'][0]['location'], '会議室')


class TestRunIntegration(unittest.TestCase):
    @patch('calendar_check.build_calendar_client')
    @patch('calendar_check.get_calendar_events')
    @patch('calendar_check.write_calendar_cache')
    def test_run_success(self, mock_write, mock_get_events, mock_build_client):
        mock_client = MagicMock()
        mock_build_client.return_value = mock_client
        mock_get_events.return_value = [
            {
                'start': '2026-09-12',
                'end_exclusive': '2026-09-13',
                'time_label': None,
                'summary': 'Test',
                'location': ''
            }
        ]

        creds_json = json.dumps({"type": "service_account"})
        calendar_check.run(creds_json, '/tmp/project', 'test@example.com', 21)

        mock_build_client.assert_called_once()
        mock_get_events.assert_called_once()
        mock_write.assert_called_once()

    @patch('calendar_check.build_calendar_client')
    def test_run_invalid_credentials(self, mock_build_client):
        mock_build_client.side_effect = ValueError("Invalid credentials")

        with self.assertRaises(SystemExit):
            calendar_check.run("invalid", "/tmp/project")

    @patch('calendar_check.build_calendar_client')
    @patch('calendar_check.get_calendar_events')
    def test_run_api_error(self, mock_get_events, mock_build_client):
        mock_get_events.side_effect = Exception("API error")
        mock_client = MagicMock()
        mock_build_client.return_value = mock_client

        creds_json = json.dumps({"type": "service_account"})
        with self.assertRaises(SystemExit):
            calendar_check.run(creds_json, "/tmp/project")


if __name__ == '__main__':
    unittest.main()
