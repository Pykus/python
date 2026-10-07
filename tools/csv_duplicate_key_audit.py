#!/usr/bin/env python3
"""
CSV duplicate-key auditor.

Purpose
-------
Find duplicate logical records in a CSV by one or more key columns. The tool is
read-only and useful before imports, merges, deduplication, or database loads.

Usage
-----
python csv_duplicate_key_audit.py data.csv --key customer_id
python csv_duplicate_key_audit.py data.csv --key country --key external_id --limit 5
python csv_duplicate_key_audit.py --self-test

Synthetic example
-----------------
Input:
customer_id,name
A-100,Ada
A-200,Lin
A-100,Grace

Command:
python csv_duplicate_key_audit.py customers.csv --key customer_id

Expected behavior:
- reports one duplicate key: A-100
- reports two rows participating in duplicate groups
- exits with code 2 when duplicates exist, 0 when keys are unique, 1 on invalid input
"""

from __future__ import annotations
import argparse
import csv
import io
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

def audit(path: Path, keys: list[str], limit: int) -> tuple[int, str]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")
        missing = [k for k in keys if k not in reader.fieldnames]
        if missing:
            raise ValueError("Missing key column(s): " + ", ".join(missing))
        groups: dict[tuple[str, ...], list[int]] = defaultdict(list)
        total = 0
        for row_number, row in enumerate(reader, start=2):
            total += 1
            key = tuple((row.get(k) or "").strip() for k in keys)
            groups[key].append(row_number)

    duplicates = [(key, rows) for key, rows in groups.items() if len(rows) > 1]
    duplicates.sort(key=lambda item: (-len(item[1]), item[0]))
    duplicate_rows = sum(len(rows) for _, rows in duplicates)

    out = io.StringIO()
    print(f"rows={total}", file=out)
    print(f"key_columns={','.join(keys)}", file=out)
    print(f"duplicate_keys={len(duplicates)}", file=out)
    print(f"rows_in_duplicate_groups={duplicate_rows}", file=out)
    for key, rows in duplicates[:limit]:
        printable = " | ".join(v if v else "<blank>" for v in key)
        print(f"duplicate={printable}; rows={','.join(map(str, rows))}", file=out)
    return (2 if duplicates else 0), out.getvalue().rstrip()

def self_test() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "sample.csv"
        p.write_text("id,name\nA,Ada\nB,Lin\nA,Grace\n", encoding="utf-8")
        code, report = audit(p, ["id"], 10)
        assert code == 2
        assert "duplicate_keys=1" in report
        assert "rows_in_duplicate_groups=2" in report
        p.write_text("id,name\nA,Ada\nB,Lin\n", encoding="utf-8")
        code, report = audit(p, ["id"], 10)
        assert code == 0
        assert "duplicate_keys=0" in report
    print("SELF_TEST=PASS")

def main() -> int:
    ap = argparse.ArgumentParser(description="Audit duplicate logical keys in a CSV file.")
    ap.add_argument("csv_file", nargs="?", type=Path)
    ap.add_argument("--key", action="append", default=[], help="Key column. Repeat for composite keys.")
    ap.add_argument("--limit", type=int, default=10, help="Maximum duplicate groups to print.")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.csv_file or not args.key:
        ap.error("csv_file and at least one --key are required unless --self-test is used")
    try:
        code, report = audit(args.csv_file, args.key, max(0, args.limit))
        print(report)
        return code
    except (OSError, ValueError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())