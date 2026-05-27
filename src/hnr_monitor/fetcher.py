from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import SiteConfig


class FetchError(RuntimeError):
    pass


def fetch_hnr_page(site: SiteConfig) -> str:
    cookie = site.cookie_value
    if not cookie:
        raise FetchError(
            "缺少站点 Cookie。请通过 Docker 环境变量 "
            f"{site.cookie_env} 或 config.toml 配置。"
        )

    request = Request(
        site.hnr_url,
        headers={
            "Cookie": cookie,
            "User-Agent": site.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=site.timeout_seconds) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except HTTPError as exc:
        raise FetchError(f"抓取 H&R 页面时发生 HTTP 错误：{exc.code}") from exc
    except URLError as exc:
        raise FetchError(f"抓取 H&R 页面时发生网络错误：{exc.reason}") from exc
    except TimeoutError as exc:
        raise FetchError("抓取 H&R 页面超时") from exc
