from datetime import datetime, timezone
from unittest.mock import patch
import hashlib
import hmac
import json
import unittest

from hnr_monitor.config import (
    ConsoleConfig,
    EmailConfig,
    HermesConfig,
    NotificationConfig,
    QqConfig,
    WebhookConfig,
    WechatConfig,
)
from hnr_monitor.models import Alert
from hnr_monitor.notify import _render_message, send_alerts


class FakeResponse:
    status = 200

    def __init__(self, body: bytes = b'{"errcode":0,"errmsg":"ok"}') -> None:
        self.body = body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self.body


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

    def test_wechat_robot_payload_contains_titles_and_mentions(self) -> None:
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
            )
        ]
        config = NotificationConfig(
            console=ConsoleConfig(enabled=False),
            email=EmailConfig(enabled=False),
            webhook=WebhookConfig(enabled=False),
            hermes=HermesConfig(enabled=False),
            wechat=WechatConfig(
                enabled=True,
                webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test",
                msgtype="text",
                mention_mobiles=["13800138000"],
            ),
            qq=QqConfig(enabled=False),
        )
        captured = []

        def fake_urlopen(request, timeout):
            captured.append((request, timeout))
            return FakeResponse()

        with patch("hnr_monitor.notify.urlopen", fake_urlopen):
            send_alerts(config, alerts, now, "Asia/Shanghai")

        self.assertEqual(len(captured), 1)
        request, timeout = captured[0]
        self.assertEqual(timeout, 30)
        self.assertEqual(request.full_url, "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["msgtype"], "text")
        self.assertIn("标题: Title A", payload["text"]["content"])
        self.assertIn("当前完成时间: 0:44:17", payload["text"]["content"])
        self.assertEqual(payload["text"]["mentioned_mobile_list"], ["13800138000"])

    def test_qq_onebot_group_payload_contains_title_and_token(self) -> None:
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
            )
        ]
        config = NotificationConfig(
            console=ConsoleConfig(enabled=False),
            email=EmailConfig(enabled=False),
            webhook=WebhookConfig(enabled=False),
            hermes=HermesConfig(enabled=False),
            wechat=WechatConfig(enabled=False),
            qq=QqConfig(
                enabled=True,
                api_base_url="http://127.0.0.1:3000",
                access_token="secret",
                message_type="group",
                group_id="10000",
            ),
        )
        captured = []

        def fake_urlopen(request, timeout):
            captured.append((request, timeout))
            return FakeResponse(b'{"status":"ok","retcode":0,"data":{"message_id":1}}')

        with patch("hnr_monitor.notify.urlopen", fake_urlopen):
            send_alerts(config, alerts, now, "Asia/Shanghai")

        self.assertEqual(len(captured), 1)
        request, timeout = captured[0]
        self.assertEqual(timeout, 30)
        self.assertEqual(request.full_url, "http://127.0.0.1:3000/send_group_msg")
        self.assertEqual(request.headers["Authorization"], "Bearer secret")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["group_id"], 10000)
        self.assertTrue(payload["auto_escape"])
        self.assertIn("标题: Title A", payload["message"])
        self.assertIn("当前完成时间: 0:44:17", payload["message"])

    def test_hermes_payload_contains_text_and_structured_alerts(self) -> None:
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
            )
        ]
        config = NotificationConfig(
            console=ConsoleConfig(enabled=False),
            email=EmailConfig(enabled=False),
            webhook=WebhookConfig(enabled=False),
            hermes=HermesConfig(
                enabled=True,
                url="http://127.0.0.1:8765/agent/inbox",
                token="secret",
                token_header="X-Hermes-Token",
                token_prefix="",
                hmac_secret="test-hmac-secret",
                signature_header="X-Hub-Signature-256",
                agent_name="H&R Monitor",
            ),
            wechat=WechatConfig(enabled=False),
            qq=QqConfig(enabled=False),
        )
        captured = []

        def fake_urlopen(request, timeout):
            captured.append((request, timeout))
            return FakeResponse(b'{"ok":true}')

        with patch("hnr_monitor.notify.urlopen", fake_urlopen):
            send_alerts(config, alerts, now, "Asia/Shanghai")

        self.assertEqual(len(captured), 1)
        request, timeout = captured[0]
        self.assertEqual(timeout, 30)
        self.assertEqual(request.full_url, "http://127.0.0.1:8765/agent/inbox")
        self.assertEqual(request.headers["X-hermes-token"], "secret")
        expected_signature = hmac.new(
            b"test-hmac-secret",
            request.data,
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(
            request.headers["X-hub-signature-256"],
            f"sha256={expected_signature}",
        )
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["source"], "chdbits-hnr-monitor")
        self.assertEqual(payload["agent"], "H&R Monitor")
        self.assertIn("标题: Title A", payload["message"])
        self.assertEqual(payload["alerts"][0]["title"], "Title A")
        self.assertEqual(payload["alerts"][0]["completion_time"], "0:44:17")


if __name__ == "__main__":
    unittest.main()
