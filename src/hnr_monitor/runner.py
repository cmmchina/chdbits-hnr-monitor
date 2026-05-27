from __future__ import annotations

from datetime import datetime, timezone
import logging
import time

from .config import AppConfig
from .fetcher import fetch_hnr_page
from .models import CheckResult
from .notify import send_alerts
from .parser import parse_hnr_records
from .storage import StateStore

logger = logging.getLogger(__name__)


def run_once(config: AppConfig, notify: bool = True, html: str | None = None) -> CheckResult:
    now = datetime.now(timezone.utc)
    page_html = html if html is not None else fetch_hnr_page(config.site)
    records = parse_hnr_records(page_html, config.parser, config.site.base_url)

    store = StateStore(config.monitor.state_path)
    try:
        result = store.update_records(
            records=records,
            now=now,
            stalled_after_hours=config.monitor.stalled_after_hours,
            notify_repeat_hours=config.monitor.notify_repeat_hours,
        )
        if notify and result.alerts:
            local_now = now.astimezone(config.monitor.tzinfo)
            localized_alerts = [
                alert.__class__(
                    key=alert.key,
                    name=alert.name,
                    detail_url=alert.detail_url,
                    progress_value=alert.progress_value,
                    stalled_since=alert.stalled_since.astimezone(config.monitor.tzinfo),
                    stalled_hours=alert.stalled_hours,
                    last_seen_at=alert.last_seen_at.astimezone(config.monitor.tzinfo),
                    status=alert.status,
                )
                for alert in result.alerts
            ]
            send_alerts(
                config.notifications,
                localized_alerts,
                local_now,
                config.monitor.timezone,
            )
            store.mark_alerts_sent(result.alerts, now)
        return result
    finally:
        store.close()


def run_forever(config: AppConfig) -> None:
    interval_seconds = config.monitor.interval_seconds
    logger.info(
        "H&R 监控已启动。检查间隔：%s 分钟；页面：%s",
        config.monitor.check_interval_minutes,
        config.site.hnr_url,
    )
    while True:
        try:
            result = run_once(config, notify=True)
            logger.info(
                "检查完成。发现=%s 新增=%s 已变化=%s 停滞=%s 消失=%s 提醒=%s",
                result.records_seen,
                result.new_records,
                result.changed_records,
                result.stalled_records,
                result.missing_records,
                len(result.alerts),
            )
        except Exception as exc:
            logger.error("检查失败：%s", exc, exc_info=logger.isEnabledFor(logging.DEBUG))
        time.sleep(interval_seconds)
