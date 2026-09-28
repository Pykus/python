from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_inventory(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read inventory: {exc}") from exc

    if not isinstance(payload, list):
        raise ValueError("Inventory root must be a JSON array")

    records: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Record {index} must be an object")

        hostname = str(item.get("hostname", "")).strip()
        observed_at = str(item.get("observed_at", "")).strip()
        if not hostname or not observed_at:
            raise ValueError(f"Record {index} requires hostname and observed_at")

        records.append(
            {
                **item,
                "hostname": hostname,
                "hostname_norm": hostname.lower(),
                "serial": str(item.get("serial", "") or "").strip(),
                "observed_at": observed_at,
                "observed_dt": parse_timestamp(observed_at),
            }
        )
    return records


def command_summary(records: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "devices": len(records),
        "missing_serial": sum(not record["serial"] for record in records),
        "duplicate_hostnames": len(records)
        - len({record["hostname_norm"] for record in records}),
    }


def command_show(records: list[dict[str, Any]], hostname: str) -> dict[str, Any] | None:
    wanted = hostname.strip().lower()
    for record in records:
        if record["hostname_norm"] == wanted:
            return {
                key: value
                for key, value in record.items()
                if key not in {"hostname_norm", "observed_dt"}
            }
    return None


def command_audit(
    records: list[dict[str, Any]],
    *,
    now: datetime,
    stale_days: int,
) -> list[dict[str, Any]]:
    threshold = now - timedelta(days=stale_days)
    findings: list[dict[str, Any]] = []

    for record in records:
        reasons: list[str] = []
        if not record["serial"]:
            reasons.append("missing_serial")
        if record["observed_dt"] < threshold:
            reasons.append("stale_observation")

        if reasons:
            findings.append(
                {
                    "hostname": record["hostname"],
                    "observed_at": record["observed_at"],
                    "reasons": reasons,
                }
            )

    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only JSON inventory inspection utility"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to a JSON inventory export",
    )
    parser.add_argument(
        "--now",
        help="Override current UTC time with an ISO-8601 timestamp",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("summary", help="Show inventory data-quality summary")

    show = subparsers.add_parser("show", help="Show one device by hostname")
    show.add_argument("hostname")

    audit = subparsers.add_parser("audit", help="Find stale or incomplete records")
    audit.add_argument("--stale-days", type=int, default=30)
    audit.add_argument("--json", action="store_true", dest="as_json")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        records = load_inventory(args.input)
        now = (
            parse_timestamp(args.now)
            if args.now
            else datetime.now(timezone.utc)
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "summary":
        print(json.dumps(command_summary(records), indent=2))
        return 0

    if args.command == "show":
        result = command_show(records, args.hostname)
        if result is None:
            print(f"Host not found: {args.hostname}", file=sys.stderr)
            return 3
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "audit":
        if args.stale_days < 1:
            print("error: --stale-days must be at least 1", file=sys.stderr)
            return 2
        findings = command_audit(records, now=now, stale_days=args.stale_days)
        if args.as_json:
            print(json.dumps(findings, indent=2))
        else:
            for finding in findings:
                print(
                    f"{finding['hostname']}: "
                    + ", ".join(finding["reasons"])
                )
            if not findings:
                print("No audit findings")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
