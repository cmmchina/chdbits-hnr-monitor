from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sqlite3

from .models import Alert, CheckResult, TorrentRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS torrents (
  key TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  detail_url TEXT NOT NULL,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  last_progress_value TEXT NOT NULL,
  progress_changed_at TEXT NOT NULL,
  last_notified_at TEXT,
  missing_since_at TEXT,
  status TEXT NOT NULL DEFAULT '',
  raw_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_torrents_missing_since
ON torrents (missing_since_at);
"""


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def update_records(
        self,
        records: list[TorrentRecord],
        now: datetime,
        stalled_after_hours: int,
        notify_repeat_hours: int,
    ) -> CheckResult:
        now_iso = _to_iso(now)
        known_keys = set(self._all_keys())
        seen_keys = {record.key for record in records}
        new_records = 0
        changed_records = 0
        alerts: list[Alert] = []

        with self.conn:
            for record in records:
                existing = self._get(record.key)
                raw_json = json.dumps(record.raw_cells, ensure_ascii=False)
                if existing is None:
                    new_records += 1
                    self.conn.execute(
                        """
                        INSERT INTO torrents (
                          key, name, detail_url, first_seen_at, last_seen_at,
                          last_progress_value, progress_changed_at,
                          last_notified_at, missing_since_at, status, raw_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                        """,
                        (
                            record.key,
                            record.name,
                            record.detail_url,
                            now_iso,
                            now_iso,
                            record.progress_value,
                            now_iso,
                            record.status,
                            raw_json,
                        ),
                    )
                    continue

                progress_changed_at = _from_iso(existing["progress_changed_at"])
                last_notified_at = (
                    _from_iso(existing["last_notified_at"]) if existing["last_notified_at"] else None
                )
                if record.progress_value != existing["last_progress_value"]:
                    changed_records += 1
                    progress_changed_at = now
                    last_notified_at = None

                self.conn.execute(
                    """
                    UPDATE torrents
                    SET name = ?,
                        detail_url = ?,
                        last_seen_at = ?,
                        last_progress_value = ?,
                        progress_changed_at = ?,
                        last_notified_at = ?,
                        missing_since_at = NULL,
                        status = ?,
                        raw_json = ?
                    WHERE key = ?
                    """,
                    (
                        record.name,
                        record.detail_url,
                        now_iso,
                        record.progress_value,
                        _to_iso(progress_changed_at),
                        _to_iso(last_notified_at) if last_notified_at else None,
                        record.status,
                        raw_json,
                        record.key,
                    ),
                )

                stalled_hours = (now - progress_changed_at).total_seconds() / 3600
                should_alert = stalled_hours >= stalled_after_hours and _repeat_allowed(
                    now,
                    last_notified_at,
                    notify_repeat_hours,
                )
                if should_alert:
                    alerts.append(
                        Alert(
                            key=record.key,
                            name=record.name,
                            detail_url=record.detail_url,
                            progress_value=record.progress_value,
                            stalled_since=progress_changed_at,
                            stalled_hours=stalled_hours,
                            last_seen_at=now,
                            status=record.status,
                        )
                    )

            missing_keys = known_keys - seen_keys
            for key in missing_keys:
                existing = self._get(key)
                if existing and existing["missing_since_at"] is None:
                    self.conn.execute(
                        "UPDATE torrents SET missing_since_at = ?, last_seen_at = ? WHERE key = ?",
                        (now_iso, now_iso, key),
                    )

        missing_records = len(known_keys - seen_keys)
        return CheckResult(
            records_seen=len(records),
            new_records=new_records,
            changed_records=changed_records,
            stalled_records=len(alerts),
            missing_records=missing_records,
            alerts=alerts,
        )

    def mark_alerts_sent(self, alerts: list[Alert], sent_at: datetime) -> None:
        with self.conn:
            for alert in alerts:
                self.conn.execute(
                    "UPDATE torrents SET last_notified_at = ? WHERE key = ?",
                    (_to_iso(sent_at), alert.key),
                )

    def simulate_stall(
        self,
        now: datetime,
        stalled_hours: float,
        limit: int,
        include_all: bool = False,
    ) -> list[dict[str, str]]:
        if not include_all and limit <= 0:
            raise ValueError("limit must be positive unless include_all is true")

        query = """
            SELECT key, name, last_progress_value
            FROM torrents
            WHERE missing_since_at IS NULL
            ORDER BY key
        """
        params: tuple[object, ...] = ()
        if not include_all:
            query += " LIMIT ?"
            params = (limit,)

        rows = self.conn.execute(query, params).fetchall()
        stalled_at = now - timedelta(hours=stalled_hours)
        with self.conn:
            for row in rows:
                self.conn.execute(
                    """
                    UPDATE torrents
                    SET progress_changed_at = ?,
                        last_notified_at = NULL
                    WHERE key = ?
                    """,
                    (_to_iso(stalled_at), row["key"]),
                )

        return [
            {
                "key": row["key"],
                "title": row["name"],
                "completion_time": row["last_progress_value"],
            }
            for row in rows
        ]

    def build_simulated_alerts(
        self,
        now: datetime,
        stalled_hours: float,
        limit: int,
        include_all: bool = False,
    ) -> list[Alert]:
        if not include_all and limit <= 0:
            raise ValueError("limit must be positive unless include_all is true")

        query = """
            SELECT key, name, detail_url, last_progress_value, status
            FROM torrents
            WHERE missing_since_at IS NULL
            ORDER BY key
        """
        params: tuple[object, ...] = ()
        if not include_all:
            query += " LIMIT ?"
            params = (limit,)

        rows = self.conn.execute(query, params).fetchall()
        stalled_since = now - timedelta(hours=stalled_hours)
        return [
            Alert(
                key=row["key"],
                name=row["name"],
                detail_url=row["detail_url"],
                progress_value=row["last_progress_value"],
                stalled_since=stalled_since,
                stalled_hours=stalled_hours,
                last_seen_at=now,
                status=row["status"],
            )
            for row in rows
        ]

    def _get(self, key: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM torrents WHERE key = ?", (key,)).fetchone()

    def _all_keys(self) -> list[str]:
        rows = self.conn.execute("SELECT key FROM torrents WHERE missing_since_at IS NULL").fetchall()
        return [row["key"] for row in rows]


def _repeat_allowed(now: datetime, last_notified_at: datetime | None, repeat_hours: int) -> bool:
    if last_notified_at is None:
        return True
    return (now - last_notified_at).total_seconds() >= repeat_hours * 3600


def _to_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)
