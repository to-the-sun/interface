import io
import json
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

import delete_jules_sessions as djs


class TestDeleteJulesSessions(unittest.TestCase):

    def test_parse_timestamp(self):
        dt = djs.parse_timestamp("2024-01-15T10:30:00Z")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 15)

        invalid_dt = djs.parse_timestamp("invalid-date-string")
        self.assertIsNone(invalid_dt)

        none_dt = djs.parse_timestamp(None)
        self.assertIsNone(none_dt)

    def test_filter_sessions_by_age(self):
        now = datetime.now(timezone.utc)
        old_time = (now - timedelta(days=10)).isoformat()
        recent_time = (now - timedelta(days=2)).isoformat()

        sessions = [
            {"name": "sessions/old1", "createTime": old_time, "state": "COMPLETED"},
            {"name": "sessions/recent1", "createTime": recent_time, "state": "COMPLETED"},
        ]

        # Filter older than 5 days
        filtered = djs.filter_sessions(sessions, days_old=5)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["name"], "sessions/old1")

    def test_filter_sessions_by_state(self):
        sessions = [
            {"name": "sessions/1", "state": "COMPLETED"},
            {"name": "sessions/2", "state": "FAILED"},
            {"name": "sessions/3", "state": "QUEUED"},
        ]

        filtered = djs.filter_sessions(sessions, state="FAILED")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["name"], "sessions/2")

    def test_filter_sessions_delete_all(self):
        sessions = [
            {"name": "sessions/1", "state": "COMPLETED"},
            {"name": "sessions/2", "state": "FAILED"},
        ]

        filtered = djs.filter_sessions(sessions, delete_all=True)
        self.assertEqual(len(filtered), 2)

    @patch("urllib.request.urlopen")
    def test_fetch_all_sessions_pagination(self, mock_urlopen):
        # Setup paginated context manager responses
        cm1 = MagicMock()
        cm1.__enter__.return_value.status = 200
        cm1.__enter__.return_value.read.return_value = json.dumps({
            "sessions": [{"name": "sessions/1"}, {"name": "sessions/2"}],
            "nextPageToken": "token123"
        }).encode("utf-8")

        cm2 = MagicMock()
        cm2.__enter__.return_value.status = 200
        cm2.__enter__.return_value.read.return_value = json.dumps({
            "sessions": [{"name": "sessions/3"}]
        }).encode("utf-8")

        mock_urlopen.side_effect = [cm1, cm2]

        sessions = djs.fetch_all_sessions("test-api-key")
        self.assertEqual(len(sessions), 3)
        self.assertEqual([s["name"] for s in sessions], ["sessions/1", "sessions/2", "sessions/3"])
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("urllib.request.urlopen")
    def test_delete_session_success(self, mock_urlopen):
        cm = MagicMock()
        cm.__enter__.return_value.status = 200
        mock_urlopen.return_value = cm

        res = djs.delete_session("sessions/123", "test-api-key")
        self.assertTrue(res)

        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "DELETE")
        self.assertEqual(req.headers["X-goog-api-key"], "test-api-key")
        self.assertTrue(req.full_url.endswith("sessions/123"))

    @patch("delete_jules_sessions.fetch_all_sessions")
    @patch("delete_jules_sessions.delete_session")
    @patch("sys.argv", ["delete_jules_sessions.py", "--api-key", "key123", "--all", "--force"])
    def test_main_delete_all_force(self, mock_delete, mock_fetch):
        mock_fetch.return_value = [
            {"name": "sessions/1", "title": "Session 1", "state": "COMPLETED"},
            {"name": "sessions/2", "title": "Session 2", "state": "FAILED"},
        ]

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            djs.main()

        self.assertEqual(mock_delete.call_count, 2)
        self.assertIn("Successfully deleted: 2", mock_stdout.getvalue())

    @patch("delete_jules_sessions.fetch_all_sessions")
    @patch("delete_jules_sessions.delete_session")
    @patch("sys.argv", ["delete_jules_sessions.py", "--api-key", "key123", "--all", "--dry-run"])
    def test_main_dry_run(self, mock_delete, mock_fetch):
        mock_fetch.return_value = [
            {"name": "sessions/1", "title": "Session 1", "state": "COMPLETED"},
        ]

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            djs.main()

        self.assertEqual(mock_delete.call_count, 0)
        self.assertIn("[DRY RUN] No sessions were deleted.", mock_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
