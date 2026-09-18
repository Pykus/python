#!/usr/bin/env python3
"""Validate public HTTPS links before an automation publishes them.

Useful when links come from CMS exports, generated material or automation output.
URLs may be passed as arguments or piped one-per-line on stdin.

Examples:
    python url_safety_check.py https://example.com/page
    python url_safety_check.py --host kahoot.com https://create.kahoot.com/share/example
    type links.txt | python url_safety_check.py

Exit code: 0 = every URL passed, 1 = at least one rejected, 2 = bad usage.
The check is local: it validates URL structure but does not open the website.
"""

import argparse
import sys
from urllib.parse import urlparse

BLOCKED = ("sandbox:", "file:", "connector", "localhost", "127.0.0.1")


def check(url: str, expected_host: str | None = None) -> tuple[bool, str]:
    value = url.strip()
    if not value.startswith("https://"):
        return False, "HTTPS required"
    if any(marker in value.lower() for marker in BLOCKED):
        return False, "local or technical URL"
    host = (urlparse(value).hostname or "").lower()
    if not host:
        return False, "missing hostname"
    if expected_host:
        wanted = expected_host.lower().strip()
        if host != wanted and not host.endswith("." + wanted):
            return False, f"expected host {wanted}"
    return True, "OK"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="*", help="URLs to validate; stdin is used if omitted")
    parser.add_argument("--host", help="optional expected domain, e.g. kahoot.com")
    args = parser.parse_args()

    urls = args.urls or [line.strip() for line in sys.stdin if line.strip()]
    if not urls:
        parser.error("provide URL arguments or pipe URLs on stdin")

    failed = False
    for url in urls:
        allowed, reason = check(url, args.host)
        print(f"{'OK' if allowed else 'REJECT'}: {url} ({reason})")
        failed |= not allowed
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
