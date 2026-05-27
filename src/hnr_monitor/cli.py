from __future__ import annotations

from pathlib import Path
import argparse
import logging
import os
import sys
from datetime import datetime, timezone

from .config import ConfigError, load_config
from .notify import send_alerts, test_notifications
from .parser import parse_hnr_records, summarize_tables
from .runner import run_forever, run_once
from .storage import StateStore


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="hnr-monitor")
    parser.add_argument(
        "--config",
        default=os.getenv("HNR_CONFIG", "config.toml"),
        help="Path to config TOML file. Missing files are allowed when using environment variables.",
    )
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"))

    subparsers = parser.add_subparsers(dest="command", required=True)

    once_parser = subparsers.add_parser("once", help="Run one check and exit.")
    once_parser.add_argument("--no-notify", action="store_true", help="Do not send alerts.")
    once_parser.add_argument("--html", help="Use a local HTML file instead of fetching the site.")

    subparsers.add_parser("run", help="Run forever.")

    parse_parser = subparsers.add_parser("parse-fixture", help="Parse a local HTML file and print records.")
    parse_parser.add_argument("html_file")
    parse_parser.add_argument("--summary", action="store_true", help="Only print table summary.")

    subparsers.add_parser("test-notify", help="Send a test notification.")

    simulate_parser = subparsers.add_parser(
        "simulate-stall",
        help="Mark existing records as stalled in the local state database for alert testing.",
    )
    simulate_parser.add_argument(
        "--hours",
        type=float,
        help="How many hours ago to pretend the completion time last changed. Defaults to stalled_after_hours + 1.",
    )
    simulate_parser.add_argument(
        "--limit",
        type=int,
        default=2,
        help="How many active records to simulate. Defaults to 2.",
    )
    simulate_parser.add_argument(
        "--all",
        action="store_true",
        help="Simulate all active records instead of using --limit.",
    )

    simulate_alert_parser = subparsers.add_parser(
        "simulate-alert",
        help="Send a simulated multi-record alert from the local state database without fetching the site.",
    )
    simulate_alert_parser.add_argument(
        "--hours",
        type=float,
        help="How many stalled hours to show. Defaults to stalled_after_hours + 1.",
    )
    simulate_alert_parser.add_argument(
        "--limit",
        type=int,
        default=2,
        help="How many active records to include. Defaults to 2.",
    )
    simulate_alert_parser.add_argument(
        "--all",
        action="store_true",
        help="Include all active records instead of using --limit.",
    )

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        config = load_config(args.config)
        if args.command == "once":
            html = Path(args.html).read_text(encoding="utf-8") if args.html else None
            result = run_once(config, notify=not args.no_notify, html=html)
            print(
                "seen={seen} new={new} changed={changed} stalled={stalled} "
                "missing={missing} alerts={alerts}".format(
                    seen=result.records_seen,
                    new=result.new_records,
                    changed=result.changed_records,
                    stalled=result.stalled_records,
                    missing=result.missing_records,
                    alerts=len(result.alerts),
                )
            )
        elif args.command == "run":
            run_forever(config)
        elif args.command == "parse-fixture":
            html = Path(args.html_file).read_text(encoding="utf-8")
            if args.summary:
                print(summarize_tables(html))
            else:
                records = parse_hnr_records(html, config.parser, config.site.base_url)
                for record in records:
                    print(
                        "\t".join(
                            [
                                record.key,
                                record.name,
                                record.progress_value,
                                record.status,
                                record.detail_url,
                            ]
                        )
                    )
        elif args.command == "test-notify":
            test_notifications(config.notifications, config.monitor.timezone)
        elif args.command == "simulate-stall":
            hours = args.hours if args.hours is not None else config.monitor.stalled_after_hours + 1
            store = StateStore(config.monitor.state_path)
            try:
                changed = store.simulate_stall(
                    now=datetime.now(timezone.utc),
                    stalled_hours=hours,
                    limit=args.limit,
                    include_all=args.all,
                )
            finally:
                store.close()

            if not changed:
                print("simulated=0; state database has no active records yet. Run once first.")
            else:
                print(f"simulated={len(changed)} stalled_hours={hours:g}")
                for item in changed:
                    print(
                        "\t".join(
                            [
                                item["key"],
                                item["title"],
                                item["completion_time"],
                            ]
                        )
                    )
        elif args.command == "simulate-alert":
            hours = args.hours if args.hours is not None else config.monitor.stalled_after_hours + 1
            now = datetime.now(timezone.utc)
            store = StateStore(config.monitor.state_path)
            try:
                alerts = store.build_simulated_alerts(
                    now=now,
                    stalled_hours=hours,
                    limit=args.limit,
                    include_all=args.all,
                )
            finally:
                store.close()

            if not alerts:
                print("alerts=0; state database has no active records yet. Run once first.")
            else:
                send_alerts(
                    config.notifications,
                    [
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
                        for alert in alerts
                    ],
                    now.astimezone(config.monitor.tzinfo),
                    config.monitor.timezone,
                )
                print(f"alerts={len(alerts)} stalled_hours={hours:g}")
    except (ConfigError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
