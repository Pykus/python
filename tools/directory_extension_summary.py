#!/usr/bin/env python3
"""
Directory extension summary.

Purpose
-------
Summarize file counts and byte totals by extension in a directory tree. This is
useful for repository cleanup, migration planning, storage audits, and quickly
spotting unexpected file types.

Usage
-----
python directory_extension_summary.py .
python directory_extension_summary.py data --top 20 --min-bytes 1024
python directory_extension_summary.py --self-test

Synthetic example
-----------------
A directory has two .csv files totaling 300 bytes and one .json file of 100 bytes.

Expected behavior:
- reports 2 files for .csv and 1 for .json
- reports byte totals and percentages
- does not read file contents
"""

from __future__ import annotations
import argparse
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

def summarize(root: Path, min_bytes: int, top: int) -> str:
    stats: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    total_files = 0
    total_bytes = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size < min_bytes:
            continue
        ext = path.suffix.lower() or "<no-extension>"
        stats[ext][0] += 1
        stats[ext][1] += size
        total_files += 1
        total_bytes += size

    lines = [f"files={total_files}", f"bytes={total_bytes}", "extension\tfiles\tbytes\tpercent_bytes"]
    ordered = sorted(stats.items(), key=lambda item: (-item[1][1], item[0]))[:top]
    for ext, (count, size) in ordered:
        pct = (size / total_bytes * 100.0) if total_bytes else 0.0
        lines.append(f"{ext}\t{count}\t{size}\t{pct:.2f}")
    return "\n".join(lines)

def self_test() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.csv").write_bytes(b"x" * 100)
        (root / "b.csv").write_bytes(b"x" * 200)
        (root / "c.json").write_bytes(b"x" * 100)
        report = summarize(root, 0, 10)
        assert ".csv\t2\t300\t75.00" in report
        assert ".json\t1\t100\t25.00" in report
    print("SELF_TEST=PASS")

def main() -> int:
    ap = argparse.ArgumentParser(description="Summarize file counts and bytes by extension.")
    ap.add_argument("root", nargs="?", type=Path, default=Path("."))
    ap.add_argument("--top", type=int, default=50)
    ap.add_argument("--min-bytes", type=int, default=0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.root.exists() or not args.root.is_dir():
        print("ERROR: root must be an existing directory", file=sys.stderr)
        return 1
    print(summarize(args.root, max(0, args.min_bytes), max(0, args.top)))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())