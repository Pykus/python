#!/usr/bin/env python3
"""Check whether URLs are safe public HTTPS links before publishing them.

Why: automation often collects links from files, CMS exports or generated material.
This tiny checker rejects local/technical links such as sandbox:, file:, localhost and
127.0.0.1 before they accidentally reach a public page.

Examples:
    python url_safety_check.py https://example.com/page
    python url_safety_check.py https://example.com file:///C:/secret.txt

Exit code is 0 when every URL passes, 1 when at least one is rejected.
No third-party packages are required.
"""

import sys
from urllib.parse import urlparse

BLOCKED = ("sandbox:", "file:", "connector", "localhost", "127.0.0.1")


def check(url: str) -> tuple[bool, str]:
    """Return (allowed, reason) without opening the URL."""
    value = url.strip()
    if not value.startswith("https://"):
        return False, "HTTPS required"
    if any(marker in value.lower() for marker in BLOCKED):
        return False, "local or technical URL"
    if not urlparse(value).netloc:
        return False, "missing hostname"
    return True, "OK"


def main(urls: list[str]) -> int:
    if not urls:
        print("Usage: python url_safety_check.py URL [URL ...]")
        return 2

    failed = False
    for url in urls:
        allowed, reason = check(url)
        print(f"{'OK' if allowed else 'REJECT'}: {url} ({reason})")
        failed |= not allowed
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
