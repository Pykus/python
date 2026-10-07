#!/usr/bin/env python3
"""
CSV join-key coverage checker.

Purpose
-------
Compare key coverage between two CSV files before a join. It reports keys that
exist only on the left, only on the right, or are duplicated on either side.

Usage
-----
python csv_join_key_coverage.py orders.csv customers.csv --left-key customer_id --right-key id
python csv_join_key_coverage.py left.csv right.csv --left-key country --left-key id --right-key country --right-key id
python csv_join_key_coverage.py --self-test

Synthetic example
-----------------
Left keys: A, B, C
Right keys: B, C, D

Expected behavior:
- left_only=1 (A)
- right_only=1 (D)
- matched=2 (B, C)
- exit code 2 when coverage gaps or duplicate keys exist
"""

from __future__ import annotations
import argparse
import csv
import io
import sys
import tempfile
from collections import Counter
from pathlib import Path

def load_keys(path: Path, columns: list[str]) -> Counter[tuple[str, ...]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError(f"{path}: CSV has no header row.")
        missing = [c for c in columns if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"{path}: missing column(s): {', '.join(missing)}")
        return Counter(tuple((row.get(c) or "").strip() for c in columns) for row in reader)

def compare(left: Path, right: Path, left_keys: list[str], right_keys: list[str], limit: int) -> tuple[int, str]:
    if len(left_keys) != len(right_keys):
        raise ValueError("Left and right key column counts must match.")
    lc = load_keys(left, left_keys)
    rc = load_keys(right, right_keys)
    ls, rs = set(lc), set(rc)
    left_only = sorted(ls - rs)
    right_only = sorted(rs - ls)
    matched = ls & rs
    left_dupes = sorted(k for k, n in lc.items() if n > 1)
    right_dupes = sorted(k for k, n in rc.items() if n > 1)

    out = io.StringIO()
    print(f"left_unique_keys={len(ls)}", file=out)
    print(f"right_unique_keys={len(rs)}", file=out)
    print(f"matched={len(matched)}", file=out)
    print(f"left_only={len(left_only)}", file=out)
    print(f"right_only={len(right_only)}", file=out)
    print(f"left_duplicate_keys={len(left_dupes)}", file=out)
    print(f"right_duplicate_keys={len(right_dupes)}", file=out)
    for label, values in (("left_only_key", left_only), ("right_only_key", right_only)):
        for key in values[:limit]:
            print(f"{label}={' | '.join(v if v else '<blank>' for v in key)}", file=out)

    issues = left_only or right_only or left_dupes or right_dupes
    return (2 if issues else 0), out.getvalue().rstrip()

def self_test() -> None:
    with tempfile.TemporaryDirectory() as td:
        left = Path(td) / "left.csv"
        right = Path(td) / "right.csv"
        left.write_text("id\nA\nB\nC\n", encoding="utf-8")
        right.write_text("id\nB\nC\nD\n", encoding="utf-8")
        code, report = compare(left, right, ["id"], ["id"], 10)
        assert code == 2
        assert "matched=2" in report and "left_only=1" in report and "right_only=1" in report
        right.write_text("id\nA\nB\nC\n", encoding="utf-8")
        code, report = compare(left, right, ["id"], ["id"], 10)
        assert code == 0
    print("SELF_TEST=PASS")

def main() -> int:
    ap = argparse.ArgumentParser(description="Check CSV join-key coverage before merging datasets.")
    ap.add_argument("left", nargs="?", type=Path)
    ap.add_argument("right", nargs="?", type=Path)
    ap.add_argument("--left-key", action="append", default=[])
    ap.add_argument("--right-key", action="append", default=[])
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.left or not args.right or not args.left_key or not args.right_key:
        ap.error("left, right, --left-key and --right-key are required unless --self-test is used")
    try:
        code, report = compare(args.left, args.right, args.left_key, args.right_key, max(0, args.limit))
        print(report)
        return code
    except (OSError, ValueError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())