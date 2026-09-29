#!/usr/bin/env python3
"""CSV schema guard.

Problem
-------
Operational CSV exports often drift: columns disappear, identifiers become
blank, or duplicate rows appear. This tool fails fast before downstream jobs
consume a malformed snapshot.

Use cases
---------
- inventory exports
- scheduled reports
- ETL input validation
- pre-import checks

Run
---
python csv_schema_guard.py data.csv --required asset_id,hostname --unique asset_id
python csv_schema_guard.py --self-test

Example input:
asset_id,hostname,status
A-100,edge-01,active
A-101,edge-02,active

Expected output:
OK rows=2 required=asset_id,hostname unique=asset_id

Exit codes: 0 valid, 2 validation failure, 1 file/runtime error.
Only the Python standard library is required.
"""
from __future__ import annotations
import argparse, csv, io, sys
from pathlib import Path

def validate(stream, required, unique):
    reader = csv.DictReader(stream)
    fields = reader.fieldnames or []
    missing = [c for c in required if c not in fields]
    if missing:
        return False, f"missing columns: {','.join(missing)}", 0
    seen = set()
    rows = 0
    for line_no, row in enumerate(reader, start=2):
        rows += 1
        for col in required:
            if not (row.get(col) or "").strip():
                return False, f"blank required value at line {line_no}: {col}", rows
        if unique:
            value = (row.get(unique) or "").strip()
            if not value:
                return False, f"blank unique key at line {line_no}: {unique}", rows
            if value in seen:
                return False, f"duplicate {unique}={value} at line {line_no}", rows
            seen.add(value)
    return True, "valid", rows

def self_test():
    good = io.StringIO("asset_id,hostname\nA-100,edge-01\nA-101,edge-02\n")
    dup = io.StringIO("asset_id,hostname\nA-100,edge-01\nA-100,edge-02\n")
    assert validate(good, ["asset_id", "hostname"], "asset_id")[0]
    assert not validate(dup, ["asset_id", "hostname"], "asset_id")[0]
    print("SELF_TEST_OK")

def main():
    p = argparse.ArgumentParser(description="Validate CSV columns, required values and one unique key.")
    p.add_argument("csv_file", nargs="?")
    p.add_argument("--required", default="", help="Comma-separated required columns.")
    p.add_argument("--unique", default="", help="Column that must contain unique nonblank values.")
    p.add_argument("--self-test", action="store_true")
    a = p.parse_args()
    if a.self_test:
        self_test(); return 0
    if not a.csv_file:
        p.error("csv_file is required unless --self-test is used")
    required = [x.strip() for x in a.required.split(",") if x.strip()]
    try:
        with Path(a.csv_file).open("r", encoding="utf-8-sig", newline="") as f:
            ok, msg, rows = validate(f, required, a.unique or None)
    except OSError as e:
        print(f"ERROR {e}", file=sys.stderr); return 1
    if not ok:
        print(f"INVALID {msg}", file=sys.stderr); return 2
    print(f"OK rows={rows} required={','.join(required) or '-'} unique={a.unique or '-'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())