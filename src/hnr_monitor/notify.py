from __future__ import annotations

from datetime import datetime
from email.message import EmailMessage
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import hashlib
import hmac
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
    if config.hermes.enabled:
        try:
            _send_hermes(config, alerts, now, timezone_name)
        except Exception as exc:
            errors.append(f"hermes: {exc}")
    if config.wechat.enabled:
        try:
            _send_wechat(config, alerts, now, timezone_name)
        except Exception as exc:
            errors.append(f"wechat: {exc}")
    if config.qq.enabled:
        try:
            _send_qq(config, alerts, now, timezone_name)
        except Exception as exc:
            errors.append(f"qq: {exc}")

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
        "alerts": _alert_payloads(alerts),
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


def _send_hermes(config: NotificationConfig, alerts: list[Alert], now: datetime, timezone_name: str) -> None:
    hermes_config = config.hermes
    message = _render_message(alerts, now, timezone_name)
    payload = {
        "source": "chdbits-hnr-monitor",
        "agent": hermes_config.agent_name,
        "type": "hnr_stalled",
        "severity": "warning",
        "title": f"H&R 监控提醒：{len(alerts)} 个种子完成时间未变化",
        "message": message,
        "text": message,
        "content": message,
        "sent_at": now.isoformat(),
        "timezone": timezone_name,
        "count": len(alerts),
        "alerts": _alert_payloads(alerts),
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    token = hermes_config.token_value
    if token:
        headers[hermes_config.token_header] = _token_header_value(hermes_config.token_prefix, token)
    hmac_secret = hermes_config.hmac_secret_value
    if hmac_secret:
        headers[hermes_config.signature_header] = _hmac_sha256_signature(data, hmac_secret)
    request = Request(
        hermes_config.url_value,
        data=data,
        method="POST",
        headers=headers,
    )
    with urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
        if response.status >= 400:
            raise NotifyError(f"hermes returned HTTP {response.status}: {body}")
        if body:
            try:
                result = json.loads(body)
            except json.JSONDecodeError:
                return
            status = str(result.get("status", "ok")).lower()
            ok = result.get("ok")
            success = result.get("success")
            if status in {"error", "failed", "fail"} or ok is False or success is False:
                message = result.get("message") or result.get("error") or body
                raise NotifyError(f"hermes returned failure: {message}")


def _send_wechat(config: NotificationConfig, alerts: list[Alert], now: datetime, timezone_name: str) -> None:
    wechat_config = config.wechat
    max_chars = 3500 if wechat_config.msgtype == "markdown" else 1800
    for content in _render_message_chunks(alerts, now, timezone_name, max_chars=max_chars):
        payload = _build_wecom_robot_payload(config, content)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            wechat_config.webhook_url_value,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            if response.status >= 400:
                raise NotifyError(f"wechat returned HTTP {response.status}: {body}")
            try:
                result = json.loads(body) if body else {}
            except json.JSONDecodeError as exc:
                raise NotifyError(f"wechat returned invalid JSON: {body}") from exc
            errcode = int(result.get("errcode", 0))
            if errcode != 0:
                errmsg = result.get("errmsg", "")
                raise NotifyError(f"wechat returned errcode {errcode}: {errmsg}")


def _token_header_value(prefix: str, token: str) -> str:
    if not prefix:
        return token
    if prefix.endswith((" ", "\t")):
        return f"{prefix}{token}"
    return f"{prefix} {token}"


def _hmac_sha256_signature(data: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), data, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _build_wecom_robot_payload(config: NotificationConfig, content: str) -> dict[str, object]:
    wechat_config = config.wechat
    if wechat_config.provider != "wecom_robot":
        raise NotifyError(f"Unsupported wechat provider: {wechat_config.provider}")

    if wechat_config.msgtype == "markdown":
        markdown: dict[str, object] = {"content": content}
        mentioned_mobile_list = _wechat_mentions(wechat_config.mention_mobiles, wechat_config.at_all)
        if mentioned_mobile_list:
            markdown["mentioned_mobile_list"] = mentioned_mobile_list
        return {"msgtype": "markdown", "markdown": markdown}

    text: dict[str, object] = {"content": content}
    mentioned_list = _wechat_mentions(wechat_config.mention_user_ids, wechat_config.at_all)
    mentioned_mobile_list = _wechat_mentions(wechat_config.mention_mobiles, wechat_config.at_all)
    if mentioned_list:
        text["mentioned_list"] = mentioned_list
    if mentioned_mobile_list:
        text["mentioned_mobile_list"] = mentioned_mobile_list
    return {"msgtype": "text", "text": text}


def _wechat_mentions(values: list[str], at_all: bool) -> list[str]:
    if at_all:
        return ["@all"]
    return [value for value in values if value]


def _send_qq(config: NotificationConfig, alerts: list[Alert], now: datetime, timezone_name: str) -> None:
    qq_config = config.qq
    max_chars = 1800
    for content in _render_message_chunks(alerts, now, timezone_name, max_chars=max_chars):
        payload = _build_onebot_payload(config, content)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        token = qq_config.access_token_value
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(
            _onebot_action_url(config),
            data=data,
            method="POST",
            headers=headers,
        )
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            if response.status >= 400:
                raise NotifyError(f"qq returned HTTP {response.status}: {body}")
            try:
                result = json.loads(body) if body else {}
            except json.JSONDecodeError as exc:
                raise NotifyError(f"qq returned invalid JSON: {body}") from exc
            retcode = int(result.get("retcode", 0))
            status = str(result.get("status", "ok"))
            if status != "ok" or retcode != 0:
                message = result.get("message") or result.get("wording") or body
                raise NotifyError(f"qq returned status={status} retcode={retcode}: {message}")


def _onebot_action_url(config: NotificationConfig) -> str:
    qq_config = config.qq
    if qq_config.provider != "onebot_v11":
        raise NotifyError(f"Unsupported qq provider: {qq_config.provider}")
    action = "send_private_msg" if qq_config.message_type == "private" else "send_group_msg"
    return f"{qq_config.api_base_url_value.rstrip('/')}/{action}"


def _build_onebot_payload(config: NotificationConfig, content: str) -> dict[str, object]:
    qq_config = config.qq
    payload: dict[str, object] = {
        "message": content,
        "auto_escape": qq_config.auto_escape,
    }
    if qq_config.message_type == "private":
        payload["user_id"] = _onebot_id(qq_config.user_id)
    elif qq_config.message_type == "group":
        payload["group_id"] = _onebot_id(qq_config.group_id)
    else:
        raise NotifyError(f"Unsupported qq message_type: {qq_config.message_type}")
    return payload


def _onebot_id(value: str) -> int | str:
    stripped = value.strip()
    return int(stripped) if stripped.isdecimal() else stripped


def _alert_payloads(alerts: list[Alert]) -> list[dict[str, object]]:
    return [
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
    ]


def _render_message(alerts: list[Alert], now: datetime, timezone_name: str) -> str:
    return _compose_message(_message_header(alerts, now, timezone_name), _alert_blocks(alerts))


def _render_message_chunks(
    alerts: list[Alert],
    now: datetime,
    timezone_name: str,
    max_chars: int,
) -> list[str]:
    header = _message_header(alerts, now, timezone_name)
    chunks: list[str] = []
    current_blocks: list[str] = []

    for block in _alert_blocks(alerts):
        candidate = _compose_message(header, current_blocks + [block])
        if len(candidate) > max_chars and current_blocks:
            chunks.append(_compose_message(header, current_blocks))
            current_blocks = [block]
        else:
            current_blocks.append(block)

    if current_blocks:
        chunks.append(_compose_message(header, current_blocks))

    if len(chunks) <= 1:
        return chunks

    first_line = header[0]
    return [
        chunk.replace(first_line, f"{first_line}（第 {index}/{len(chunks)} 段）", 1)
        for index, chunk in enumerate(chunks, start=1)
    ]


def _compose_message(header: list[str], blocks: list[str]) -> str:
    message = "\n".join(header)
    if blocks:
        message += "\n\n" + "\n\n".join(blocks)
    return message.rstrip()


def _message_header(alerts: list[Alert], now: datetime, timezone_name: str) -> list[str]:
    return [
        f"H&R 监控发现 {len(alerts)} 个种子的完成时间长时间没有变化。",
        f"检查时间：{now.isoformat()} ({timezone_name})",
    ]


def _alert_blocks(alerts: list[Alert]) -> list[str]:
    return [
        "\n".join(
            [
                f"{index}. 标题: {alert.name}",
                f"   Key: {alert.key}",
                f"   当前完成时间: {alert.progress_value}",
                f"   未变化时长: {alert.stalled_hours:.1f} 小时",
                f"   未变化起点: {alert.stalled_since.isoformat()}",
                f"   状态: {alert.status or '-'}",
                f"   链接: {alert.detail_url or '-'}",
            ]
        )
        for index, alert in enumerate(alerts, start=1)
    ]
