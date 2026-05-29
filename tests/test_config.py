from pathlib import Path
import os
import tempfile
import unittest

from hnr_monitor.config import load_config


class ConfigTest(unittest.TestCase):
    def test_loads_from_environment_without_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_config = Path(tmp_dir) / "missing.toml"
            old_values = {
                key: os.environ.get(key)
                for key in [
                    "HNR_USER_ID",
                    "CHDBITS_COOKIE",
                    "HNR_EMAIL_ENABLED",
                    "HNR_CHECK_INTERVAL_MINUTES",
                    "HNR_SMTP_HOST",
                    "HNR_EMAIL_FROM",
                    "HNR_EMAIL_TO",
                    "HNR_WECHAT_ENABLED",
                    "HNR_WECHAT_WEBHOOK_URL",
                    "HNR_WECHAT_MSGTYPE",
                    "HNR_WECHAT_MENTION_MOBILES",
                ]
            }
            try:
                os.environ["HNR_USER_ID"] = "1"
                os.environ["CHDBITS_COOKIE"] = "uid=test"
                os.environ["HNR_EMAIL_ENABLED"] = "true"
                os.environ["HNR_CHECK_INTERVAL_MINUTES"] = "10"
                os.environ["HNR_SMTP_HOST"] = "smtp.example.com"
                os.environ["HNR_EMAIL_FROM"] = "from@example.com"
                os.environ["HNR_EMAIL_TO"] = "to-a@example.com,to-b@example.com"
                os.environ["HNR_WECHAT_ENABLED"] = "true"
                os.environ["HNR_WECHAT_WEBHOOK_URL"] = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
                os.environ["HNR_WECHAT_MSGTYPE"] = "text"
                os.environ["HNR_WECHAT_MENTION_MOBILES"] = "13800138000,13900139000"

                config = load_config(missing_config)

                self.assertEqual(config.site.user_id, 1)
                self.assertEqual(config.site.cookie_value, "uid=test")
                self.assertEqual(config.monitor.check_interval_minutes, 10)
                self.assertEqual(config.monitor.interval_seconds, 600)
                self.assertTrue(config.notifications.email.enabled)
                self.assertEqual(config.notifications.email.smtp_host, "smtp.example.com")
                self.assertEqual(
                    config.notifications.email.to,
                    ["to-a@example.com", "to-b@example.com"],
                )
                self.assertTrue(config.notifications.wechat.enabled)
                self.assertEqual(config.notifications.wechat.msgtype, "text")
                self.assertEqual(
                    config.notifications.wechat.mention_mobiles,
                    ["13800138000", "13900139000"],
                )
            finally:
                for key, value in old_values.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
