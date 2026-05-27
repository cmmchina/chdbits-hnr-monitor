from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from hnr_monitor.models import TorrentRecord
from hnr_monitor.storage import StateStore


class StorageTest(unittest.TestCase):
    def test_alert_after_progress_stalls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = StateStore(Path(tmp_dir) / "state.sqlite3")
            first = datetime(2026, 5, 25, 0, 0, tzinfo=timezone.utc)
            second = first + timedelta(hours=25)
            record = TorrentRecord(
                key="123",
                name="Ubuntu ISO",
                progress_value="12:30:00",
                status="进行中",
                detail_url="https://ptchdbits.co/details.php?id=123",
                raw_cells=["Ubuntu ISO", "12:30:00", "进行中"],
            )

            initial = store.update_records([record], first, stalled_after_hours=24, notify_repeat_hours=12)
            stalled = store.update_records([record], second, stalled_after_hours=24, notify_repeat_hours=12)

            self.assertEqual(initial.alerts, [])
            self.assertEqual(len(stalled.alerts), 1)
            self.assertEqual(stalled.alerts[0].key, "123")
            store.close()

    def test_collects_all_stalled_records_before_alerting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = StateStore(Path(tmp_dir) / "state.sqlite3")
            first = datetime(2026, 5, 25, 0, 0, tzinfo=timezone.utc)
            second = first + timedelta(hours=25)
            records = [
                TorrentRecord(
                    key="123",
                    name="Title A",
                    progress_value="0:44:17",
                    status="",
                    detail_url="https://ptchdbits.co/details.php?id=123",
                    raw_cells=["", "Title A", "0:44:17"],
                ),
                TorrentRecord(
                    key="456",
                    name="Title B",
                    progress_value="2:10:05",
                    status="",
                    detail_url="https://ptchdbits.co/details.php?id=456",
                    raw_cells=["", "Title B", "2:10:05"],
                ),
            ]

            store.update_records(records, first, stalled_after_hours=24, notify_repeat_hours=12)
            stalled = store.update_records(records, second, stalled_after_hours=24, notify_repeat_hours=12)

            self.assertEqual(len(stalled.alerts), 2)
            self.assertEqual([alert.name for alert in stalled.alerts], ["Title A", "Title B"])
            self.assertEqual([alert.progress_value for alert in stalled.alerts], ["0:44:17", "2:10:05"])
            store.close()

    def test_simulate_stall_marks_limited_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = StateStore(Path(tmp_dir) / "state.sqlite3")
            first = datetime(2026, 5, 25, 0, 0, tzinfo=timezone.utc)
            second = first + timedelta(hours=1)
            records = [
                TorrentRecord(
                    key="123",
                    name="Title A",
                    progress_value="0:44:17",
                    status="",
                    detail_url="https://ptchdbits.co/details.php?id=123",
                    raw_cells=["", "Title A", "0:44:17"],
                ),
                TorrentRecord(
                    key="456",
                    name="Title B",
                    progress_value="2:10:05",
                    status="",
                    detail_url="https://ptchdbits.co/details.php?id=456",
                    raw_cells=["", "Title B", "2:10:05"],
                ),
            ]

            store.update_records(records, first, stalled_after_hours=24, notify_repeat_hours=12)
            simulated = store.simulate_stall(second, stalled_hours=25, limit=1)
            stalled = store.update_records(records, second, stalled_after_hours=24, notify_repeat_hours=12)

            self.assertEqual(len(simulated), 1)
            self.assertEqual(simulated[0]["title"], "Title A")
            self.assertEqual(len(stalled.alerts), 1)
            self.assertEqual(stalled.alerts[0].name, "Title A")
            store.close()

    def test_build_simulated_alerts_from_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = StateStore(Path(tmp_dir) / "state.sqlite3")
            first = datetime(2026, 5, 25, 0, 0, tzinfo=timezone.utc)
            now = first + timedelta(hours=1)
            records = [
                TorrentRecord(
                    key="123",
                    name="Title A",
                    progress_value="0:44:17",
                    status="",
                    detail_url="https://ptchdbits.co/details.php?id=123",
                    raw_cells=["", "Title A", "0:44:17"],
                ),
                TorrentRecord(
                    key="456",
                    name="Title B",
                    progress_value="2:10:05",
                    status="",
                    detail_url="https://ptchdbits.co/details.php?id=456",
                    raw_cells=["", "Title B", "2:10:05"],
                ),
            ]

            store.update_records(records, first, stalled_after_hours=24, notify_repeat_hours=12)
            alerts = store.build_simulated_alerts(now, stalled_hours=25, limit=2)

            self.assertEqual(len(alerts), 2)
            self.assertEqual([alert.name for alert in alerts], ["Title A", "Title B"])
            self.assertEqual([alert.progress_value for alert in alerts], ["0:44:17", "2:10:05"])
            store.close()

if __name__ == "__main__":
    unittest.main()
