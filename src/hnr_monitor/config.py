from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
import copy
import os

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - used by Python 3.9/3.10
    from . import simple_toml as tomllib


class ConfigError(RuntimeError):
    pass


DEFAULT_CONFIG: dict[str, Any] = {
    "site": {
        "base_url": "https://ptchdbits.co",
        "hnr_path": "/hnr.php",
        "user_id": 0,
        "cookie_env": "CHDBITS_COOKIE",
        "cookie": "",
        "user_agent": "Mozilla/5.0 (compatible; chdbits-hnr-monitor/0.1.5)",
        "timeout_seconds": 30,
    },
    "monitor": {
        "state_path": "/data/hnr-monitor.sqlite3",
        "check_interval_minutes": 30,
        "stalled_after_hours": 24,
        "notify_repeat_hours": 12,
        "timezone": "Asia/Shanghai",
    },
    "parser": {
        "progress_columns": [
            "完成时间",
            "H&R完成时间",
            "H&R 完成时间",
            "H&R百分比",
            "做种时间",
            "已完成",
            "已做种",
            "剩余时间",
        ],
        "name_columns": ["种子", "种子名称", "标题", "名称", "Torrent", "Name"],
        "status_columns": ["状态", "H&R状态", "Status"],
        "name_column_index": -1,
        "progress_column_index": -1,
        "status_column_index": -1,
        "torrent_id_patterns": [
            "details\\.php\\?id=(\\d+)",
            "details\\.php\\?id=(\\d+)&hit=1",
            "download\\.php\\?id=(\\d+)",
            "id=(\\d+)",
        ],
        "login_failed_markers": ["登录", "login", "password", "密码"],
    },
    "notifications": {
        "console": {"enabled": True},
        "email": {
            "enabled": False,
            "smtp_host": "",
            "smtp_port": 465,
            "use_ssl": True,
            "starttls": False,
            "username": "",
            "password_env": "SMTP_PASSWORD",
            "password": "",
            "from": "",
            "to": [],
        },
        "webhook": {
            "enabled": False,
            "url_env": "HNR_WEBHOOK_URL",
            "url": "",
        },
        "wechat": {
            "enabled": False,
            "provider": "wecom_robot",
            "webhook_url_env": "HNR_WECHAT_WEBHOOK_URL",
            "webhook_url": "",
            "msgtype": "text",
            "mention_mobiles": [],
            "mention_user_ids": [],
            "at_all": False,
        },
    },
}


@dataclass(frozen=True)
class SiteConfig:
    base_url: str
    hnr_path: str
    user_id: int
    cookie_env: str = "CHDBITS_COOKIE"
    cookie: str = ""
    user_agent: str = "Mozilla/5.0 (compatible; chdbits-hnr-monitor/0.1.5)"
    timeout_seconds: int = 30

    @property
    def cookie_value(self) -> str:
        return os.getenv(self.cookie_env, self.cookie).strip()

    @property
    def hnr_url(self) -> str:
        base = self.base_url.rstrip("/")
        path = self.hnr_path if self.hnr_path.startswith("/") else f"/{self.hnr_path}"
        sep = "&" if "?" in path else "?"
        return f"{base}{path}{sep}id={self.user_id}"


@dataclass(frozen=True)
class MonitorConfig:
    state_path: Path
    check_interval_minutes: int = 30
    stalled_after_hours: int = 24
    notify_repeat_hours: int = 12
    timezone: str = "Asia/Shanghai"

    @property
    def tzinfo(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.timezone)
        except Exception as exc:
            raise ConfigError(f"Invalid timezone: {self.timezone}") from exc

    @property
    def interval_seconds(self) -> int:
        return self.check_interval_minutes * 60


@dataclass(frozen=True)
class ParserConfig:
    progress_columns: list[str] = field(default_factory=list)
    name_columns: list[str] = field(default_factory=list)
    status_columns: list[str] = field(default_factory=list)
    name_column_index: int = -1
    progress_column_index: int = -1
    status_column_index: int = -1
    torrent_id_patterns: list[str] = field(default_factory=list)
    login_failed_markers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ConsoleConfig:
    enabled: bool = True


@dataclass(frozen=True)
class EmailConfig:
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 465
    use_ssl: bool = True
    starttls: bool = False
    username: str = ""
    password_env: str = "SMTP_PASSWORD"
    password: str = ""
    from_addr: str = ""
    to: list[str] = field(default_factory=list)

    @property
    def password_value(self) -> str:
        return os.getenv(self.password_env, self.password)


@dataclass(frozen=True)
class WebhookConfig:
    enabled: bool = False
    url_env: str = "HNR_WEBHOOK_URL"
    url: str = ""

    @property
    def url_value(self) -> str:
        return os.getenv(self.url_env, self.url).strip()


@dataclass(frozen=True)
class WechatConfig:
    enabled: bool = False
    provider: str = "wecom_robot"
    webhook_url_env: str = "HNR_WECHAT_WEBHOOK_URL"
    webhook_url: str = ""
    msgtype: str = "text"
    mention_mobiles: list[str] = field(default_factory=list)
    mention_user_ids: list[str] = field(default_factory=list)
    at_all: bool = False

    @property
    def webhook_url_value(self) -> str:
        return os.getenv(self.webhook_url_env, self.webhook_url).strip()


@dataclass(frozen=True)
class NotificationConfig:
    console: ConsoleConfig
    email: EmailConfig
    webhook: WebhookConfig
    wechat: WechatConfig


@dataclass(frozen=True)
class AppConfig:
    site: SiteConfig
    monitor: MonitorConfig
    parser: ParserConfig
    notifications: NotificationConfig


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    raw = copy.deepcopy(DEFAULT_CONFIG)
    if config_path.exists():
        with config_path.open("rb") as fh:
            raw = _deep_merge(raw, tomllib.load(fh))
    _apply_env_overrides(raw)

    try:
        site_raw = raw["site"]
        monitor_raw = raw["monitor"]
    except KeyError as exc:
        raise ConfigError(f"Missing required config section: {exc}") from exc

    parser_raw = raw.get("parser", {})
    notifications_raw = raw.get("notifications", {})
    email_raw = notifications_raw.get("email", {})
    wechat_raw = notifications_raw.get("wechat", {})

    site = SiteConfig(
        base_url=str(site_raw["base_url"]),
        hnr_path=str(site_raw.get("hnr_path", "/hnr.php")),
        user_id=int(site_raw["user_id"]),
        cookie_env=str(site_raw.get("cookie_env", "CHDBITS_COOKIE")),
        cookie=str(site_raw.get("cookie", "")),
        user_agent=str(site_raw.get("user_agent", SiteConfig.user_agent)),
        timeout_seconds=int(site_raw.get("timeout_seconds", 30)),
    )
    monitor = MonitorConfig(
        state_path=Path(str(monitor_raw.get("state_path", "./data/hnr-monitor.sqlite3"))),
        check_interval_minutes=int(monitor_raw.get("check_interval_minutes", 30)),
        stalled_after_hours=int(monitor_raw.get("stalled_after_hours", 24)),
        notify_repeat_hours=int(monitor_raw.get("notify_repeat_hours", 12)),
        timezone=str(monitor_raw.get("timezone", "Asia/Shanghai")),
    )
    parser = ParserConfig(
        progress_columns=_string_list(parser_raw.get("progress_columns", [])),
        name_columns=_string_list(parser_raw.get("name_columns", [])),
        status_columns=_string_list(parser_raw.get("status_columns", [])),
        name_column_index=int(parser_raw.get("name_column_index", -1)),
        progress_column_index=int(parser_raw.get("progress_column_index", -1)),
        status_column_index=int(parser_raw.get("status_column_index", -1)),
        torrent_id_patterns=_string_list(parser_raw.get("torrent_id_patterns", [])),
        login_failed_markers=_string_list(parser_raw.get("login_failed_markers", [])),
    )
    notifications = NotificationConfig(
        console=ConsoleConfig(
            enabled=bool(notifications_raw.get("console", {}).get("enabled", True)),
        ),
        email=EmailConfig(
            enabled=bool(email_raw.get("enabled", False)),
            smtp_host=str(email_raw.get("smtp_host", "")),
            smtp_port=int(email_raw.get("smtp_port", 465)),
            use_ssl=bool(email_raw.get("use_ssl", True)),
            starttls=bool(email_raw.get("starttls", False)),
            username=str(email_raw.get("username", "")),
            password_env=str(email_raw.get("password_env", "SMTP_PASSWORD")),
            password=str(email_raw.get("password", "")),
            from_addr=str(email_raw.get("from", "")),
            to=_string_list(email_raw.get("to", [])),
        ),
        webhook=WebhookConfig(
            enabled=bool(notifications_raw.get("webhook", {}).get("enabled", False)),
            url_env=str(notifications_raw.get("webhook", {}).get("url_env", "HNR_WEBHOOK_URL")),
            url=str(notifications_raw.get("webhook", {}).get("url", "")),
        ),
        wechat=WechatConfig(
            enabled=bool(wechat_raw.get("enabled", False)),
            provider=str(wechat_raw.get("provider", "wecom_robot")),
            webhook_url_env=str(wechat_raw.get("webhook_url_env", "HNR_WECHAT_WEBHOOK_URL")),
            webhook_url=str(wechat_raw.get("webhook_url", "")),
            msgtype=str(wechat_raw.get("msgtype", "text")),
            mention_mobiles=_string_list(wechat_raw.get("mention_mobiles", [])),
            mention_user_ids=_string_list(wechat_raw.get("mention_user_ids", [])),
            at_all=bool(wechat_raw.get("at_all", False)),
        ),
    )

    _validate(site, monitor, parser, notifications)
    return AppConfig(site=site, monitor=monitor, parser=parser, notifications=notifications)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _apply_env_overrides(raw: dict[str, Any]) -> None:
    _set_env(raw, ("site", "base_url"), "HNR_BASE_URL")
    _set_env(raw, ("site", "hnr_path"), "HNR_PATH")
    _set_env(raw, ("site", "user_id"), "HNR_USER_ID", int)
    _set_env(raw, ("site", "cookie_env"), "HNR_COOKIE_ENV")
    _set_env(raw, ("site", "cookie"), "HNR_COOKIE")
    _set_env(raw, ("site", "user_agent"), "HNR_USER_AGENT")
    _set_env(raw, ("site", "timeout_seconds"), "HNR_TIMEOUT_SECONDS", int)

    _set_env(raw, ("monitor", "state_path"), "HNR_STATE_PATH")
    _set_env(raw, ("monitor", "check_interval_minutes"), "HNR_CHECK_INTERVAL_MINUTES", int)
    _set_env(raw, ("monitor", "stalled_after_hours"), "HNR_STALLED_AFTER_HOURS", int)
    _set_env(raw, ("monitor", "notify_repeat_hours"), "HNR_NOTIFY_REPEAT_HOURS", int)
    _set_env(raw, ("monitor", "timezone"), "TZ")
    _set_env(raw, ("monitor", "timezone"), "HNR_TIMEZONE")

    _set_env(raw, ("parser", "progress_columns"), "HNR_PROGRESS_COLUMNS", _env_list)
    _set_env(raw, ("parser", "name_columns"), "HNR_NAME_COLUMNS", _env_list)
    _set_env(raw, ("parser", "status_columns"), "HNR_STATUS_COLUMNS", _env_list)
    _set_env(raw, ("parser", "name_column_index"), "HNR_NAME_COLUMN_INDEX", int)
    _set_env(raw, ("parser", "progress_column_index"), "HNR_PROGRESS_COLUMN_INDEX", int)
    _set_env(raw, ("parser", "status_column_index"), "HNR_STATUS_COLUMN_INDEX", int)

    _set_env(raw, ("notifications", "console", "enabled"), "HNR_CONSOLE_ENABLED", _env_bool)
    _set_env(raw, ("notifications", "email", "enabled"), "HNR_EMAIL_ENABLED", _env_bool)
    _set_env(raw, ("notifications", "email", "smtp_host"), "HNR_SMTP_HOST")
    _set_env(raw, ("notifications", "email", "smtp_port"), "HNR_SMTP_PORT", int)
    _set_env(raw, ("notifications", "email", "use_ssl"), "HNR_SMTP_USE_SSL", _env_bool)
    _set_env(raw, ("notifications", "email", "starttls"), "HNR_SMTP_STARTTLS", _env_bool)
    _set_env(raw, ("notifications", "email", "username"), "HNR_SMTP_USERNAME")
    _set_env(raw, ("notifications", "email", "password"), "HNR_SMTP_PASSWORD")
    _set_env(raw, ("notifications", "email", "password_env"), "HNR_SMTP_PASSWORD_ENV")
    _set_env(raw, ("notifications", "email", "from"), "HNR_EMAIL_FROM")
    _set_env(raw, ("notifications", "email", "to"), "HNR_EMAIL_TO", _env_list)

    _set_env(raw, ("notifications", "webhook", "enabled"), "HNR_WEBHOOK_ENABLED", _env_bool)
    _set_env(raw, ("notifications", "webhook", "url"), "HNR_WEBHOOK_URL")
    _set_env(raw, ("notifications", "webhook", "url_env"), "HNR_WEBHOOK_URL_ENV")

    _set_env(raw, ("notifications", "wechat", "enabled"), "HNR_WECHAT_ENABLED", _env_bool)
    _set_env(raw, ("notifications", "wechat", "provider"), "HNR_WECHAT_PROVIDER")
    _set_env(raw, ("notifications", "wechat", "webhook_url"), "HNR_WECHAT_WEBHOOK_URL")
    _set_env(raw, ("notifications", "wechat", "webhook_url_env"), "HNR_WECHAT_WEBHOOK_URL_ENV")
    _set_env(raw, ("notifications", "wechat", "msgtype"), "HNR_WECHAT_MSGTYPE")
    _set_env(raw, ("notifications", "wechat", "mention_mobiles"), "HNR_WECHAT_MENTION_MOBILES", _env_list)
    _set_env(raw, ("notifications", "wechat", "mention_user_ids"), "HNR_WECHAT_MENTION_USER_IDS", _env_list)
    _set_env(raw, ("notifications", "wechat", "at_all"), "HNR_WECHAT_AT_ALL", _env_bool)


def _set_env(
    raw: dict[str, Any],
    path: tuple[str, ...],
    env_name: str,
    convert: Any = str,
) -> None:
    value = os.getenv(env_name)
    if value is None or value == "":
        return
    cursor = raw
    for key in path[:-1]:
        cursor = cursor.setdefault(key, {})
    try:
        cursor[path[-1]] = convert(value)
    except ValueError as exc:
        raise ConfigError(f"Invalid value for {env_name}: {value}") from exc


def _env_bool(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(value)


def _env_list(value: str) -> list[str]:
    return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()]


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise ConfigError(f"Expected string list, got {type(value).__name__}")


def _validate(
    site: SiteConfig,
    monitor: MonitorConfig,
    parser: ParserConfig,
    notifications: NotificationConfig,
) -> None:
    if not site.base_url.startswith(("http://", "https://")):
        raise ConfigError("site.base_url must start with http:// or https://")
    if site.user_id <= 0:
        raise ConfigError("site.user_id must be a positive integer")
    if monitor.check_interval_minutes <= 0:
        raise ConfigError("monitor.check_interval_minutes must be positive")
    if monitor.interval_seconds <= 0:
        raise ConfigError("monitor interval must be positive")
    if monitor.stalled_after_hours <= 0:
        raise ConfigError("monitor.stalled_after_hours must be positive")
    if monitor.notify_repeat_hours <= 0:
        raise ConfigError("monitor.notify_repeat_hours must be positive")
    monitor.tzinfo
    if parser.progress_column_index < 0 and not parser.progress_columns:
        raise ConfigError("parser.progress_columns is required when progress_column_index is -1")
    if notifications.email.enabled:
        if not notifications.email.smtp_host:
            raise ConfigError("notifications.email.smtp_host is required when email is enabled")
        if not notifications.email.from_addr:
            raise ConfigError("notifications.email.from is required when email is enabled")
        if not notifications.email.to:
            raise ConfigError("notifications.email.to is required when email is enabled")
    if notifications.webhook.enabled and not notifications.webhook.url_value:
        raise ConfigError("Webhook is enabled but URL is empty")
    if notifications.wechat.enabled:
        if notifications.wechat.provider != "wecom_robot":
            raise ConfigError("notifications.wechat.provider only supports wecom_robot")
        if notifications.wechat.msgtype not in {"text", "markdown"}:
            raise ConfigError("notifications.wechat.msgtype must be text or markdown")
        if not notifications.wechat.webhook_url_value:
            raise ConfigError("Wechat notification is enabled but webhook URL is empty")
