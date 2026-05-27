from datetime import datetime, timezone
import unittest

from hnr_monitor.models import Alert
from hnr_monitor.notify import _render_message


class NotifyTest(unittest.TestCase):
    def test_message_contains_all_titles_and_completion_times(self) -> None:
        now = datetime(2026, 5, 26, 8, 0, tzinfo=timezone.utc)
        alerts = [
            Alert(
                key="123",
                name="Title A",
                detail_url="https://ptchdbits.co/details.php?id=123",
                progress_value="0:44:17",
                stalled_since=now,
                stalled_hours=24.5,
                last_seen_at=now,
                status="",
            ),
            Alert(
                key="456",
                name="Title B",
                detail_url="https://ptchdbits.co/details.php?id=456",
                progress_value="2:10:05",
                stalled_since=now,
                stalled_hours=25.0,
                last_seen_at=now,
                status="",
            ),
        ]

        message = _render_message(alerts, now, "Asia/Shanghai")

        self.assertIn("发现 2 个种子的完成时间长时间没有变化", message)
        self.assertIn("标题: Title A", message)
        self.assertIn("当前完成时间: 0:44:17", message)
        self.assertIn("标题: Title B", message)
        self.assertIn("当前完成时间: 2:10:05", message)


if __name__ == "__main__":
    unittest.main()
