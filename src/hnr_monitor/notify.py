from __future__ import annotations

from datetime import datetime
from email.message import EmailMessage
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import json
import logging
import smtplib

from .config import NotificationConfig
from .models import Alert

logger = logging.getLogger(__name__)


class NotifyError(RuntimeError):
    pass


def send_alerts(config: NotificationConfig, alerts: list[Alert], now: datetime, timezone_name: str) -> None:
    if not alerts:
        return

    errors: list[str] = []
    if config.console.enabled:
        _send_console(alerts, now, timezone_name)
    if config.email.enabled:
        try:
            _send_email(config, alerts, now, timezone_name)
        except Exception as exc:
            errors.append(f"email: {exc}")
    if config.webhook.enabled:
        try:
            _send_webhook(config, alerts, now, timezone_name)
        except Exception as exc:
            errors.append(f"webhook: {exc}")

    if errors:
        raise NotifyError("; ".join(errors))


def test_notifications(config: NotificationConfig, timezone_name: str) -> None:
    now = datetime.now(ZoneInfo(timezone_name))
    fake = Alert(
        key="test",
        name="测试 H&R 种子",
        detail_url="https://example.invalid/details.php?id=test",
        progress_value="12:34:56",
        stalled_since=now,
        stalled_hours=24.0,
        last_seen_at=now,
        status="testing",
    )
    send_alerts(config, [fake], now, timezone_name)


def _send_console(alerts: list[Alert], now: datetime, timezone_name: str) -> None:
    logger.warning(_render_message(alerts, now, timezone_name))


def _send_email(config: NotificationConfig, alerts: list[Alert], now: datetime, timezone_name: str) -> None:
    email_config = config.email
    password = email_config.password_value
    message = EmailMessage()
    message["Subject"] = f"H&R 监控提醒：{len(alerts)} 个种子完成时间未变化"
    message["From"] = email_config.from_addr
    message["To"] = ", ".join(email_config.to)
    message.set_content(_render_message(alerts, now, timezone_name))

    if email_config.use_ssl:
        server: smtplib.SMTP = smtplib.SMTP_SSL(email_config.smtp_host, email_config.smtp_port, timeout=30)
    else:
        server = smtplib.SMTP(email_config.smtp_host, email_config.smtp_port, timeout=30)
    try:
        if email_config.starttls:
            server.starttls()
        if email_config.username:
            server.login(email_config.username, password)
        server.send_message(message)
    finally:
        server.quit()


def _send_webhook(config: NotificationConfig, alerts: list[Alert], now: datetime, timezone_name: str) -> None:
    payload = {
        "type": "hnr_stalled",
        "sent_at": now.isoformat(),
        "timezone": timezone_name,
        "count": len(alerts),
        "alerts": [
            {
                "key": alert.key,
                "name": alert.name,
                "title": alert.name,
                "detail_url": alert.detail_url,
                "progress_value": alert.progress_value,
                "completion_time": alert.progress_value,
                "stalled_since": alert.stalled_since.isoformat(),
                "stalled_hours": round(alert.stalled_hours, 2),
                "last_seen_at": alert.last_seen_at.isoformat(),
                "status": alert.status,
            }
            for alert in alerts
        ],
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        config.webhook.url_value,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urlopen(request, timeout=30) as response:
        if response.status >= 400:
            raise NotifyError(f"webhook returned HTTP {response.status}")


def _render_message(alerts: list[Alert], now: datetime, timezone_name: str) -> str:
    lines = [
        f"H&R 监控发现 {len(alerts)} 个种子的完成时间长时间没有变化。",
        f"检查时间：{now.isoformat()} ({timezone_name})",
        "",
    ]
    for index, alert in enumerate(alerts, start=1):
        lines.extend(
            [
                f"{index}. 标题: {alert.name}",
                f"   Key: {alert.key}",
                f"   当前完成时间: {alert.progress_value}",
                f"   未变化时长: {alert.stalled_hours:.1f} 小时",
                f"   未变化起点: {alert.stalled_since.isoformat()}",
                f"   状态: {alert.status or '-'}",
                f"   链接: {alert.detail_url or '-'}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()
