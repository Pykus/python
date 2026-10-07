#!/usr/bin/env python3
"""
JSON object-key inventory.

Purpose
-------
Inspect a JSON document and count object keys by dotted path. This helps detect
shape drift in configuration exports or API samples without exposing values.

Usage
-----
python json_key_inventory.py sample.json
python json_key_inventory.py sample.json --max-depth 4 --top 30
python json_key_inventory.py --self-test

Synthetic example
-----------------
Input:
{"users":[{"id":1,"profile":{"name":"Ada"}},{"id":2,"profile":{"name":"Lin"}}]}

Expected behavior:
- reports users[].id twice
- reports users[].profile.name twice
- never prints scalar values
"""

from __future__ import annotations
import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

def inventory(value: Any, max_depth: int) -> Counter[str]:
    counts: Counter[str] = Counter()
    def walk(node: Any, path: str, depth: int) -> None:
        if depth > max_depth:
            return
        if isinstance(node, dict):
            for key, child in node.items():
                child_path = f"{path}.{key}" if path else key
                counts[child_path] += 1
                walk(child, child_path, depth + 1)
        elif isinstance(node, list):
            list_path = f"{path}[]" if path else "[]"
            for child in node:
                walk(child, list_path, depth + 1)
    walk(value, "", 0)
    return counts

def run(path: Path, max_depth: int, top: int) -> str:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    counts = inventory(data, max_depth)
    lines = [f"distinct_paths={len(counts)}"]
    for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top]:
        lines.append(f"{count}\t{name}")
    return "\n".join(lines)

def self_test() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "sample.json"
        p.write_text('{"users":[{"id":1,"profile":{"name":"Ada"}},{"id":2,"profile":{"name":"Lin"}}]}', encoding="utf-8")
        report = run(p, 10, 20)
        assert "2\tusers[].id" in report
        assert "2\tusers[].profile.name" in report
        assert "Ada" not in report and "Lin" not in report
    print("SELF_TEST=PASS")

def main() -> int:
    ap = argparse.ArgumentParser(description="Count JSON object-key paths without printing values.")
    ap.add_argument("json_file", nargs="?", type=Path)
    ap.add_argument("--max-depth", type=int, default=8)
    ap.add_argument("--top", type=int, default=100)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.json_file:
        ap.error("json_file is required unless --self-test is used")
    try:
        print(run(args.json_file, max(0, args.max_depth), max(0, args.top)))
        return 0
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())