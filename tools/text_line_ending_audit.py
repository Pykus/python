#!/usr/bin/env python3
"""
Text line-ending auditor.

Purpose
-------
Detect LF, CRLF, mixed line endings, missing final newlines, and binary-looking
files in a directory tree. Useful before cross-platform releases or formatter
migration.

Usage
-----
python text_line_ending_audit.py .
python text_line_ending_audit.py src --extensions .py .md .txt
python text_line_ending_audit.py --self-test

Synthetic example
-----------------
A directory contains a.txt with LF and b.txt with CRLF.

Expected behavior:
- lists each file with its line-ending style
- summary counts LF and CRLF files
- exits 2 if mixed line endings are found inside any single file
"""

from __future__ import annotations
import argparse
import sys
import tempfile
from collections import Counter
from pathlib import Path

def classify(data: bytes) -> tuple[str, bool]:
    if b"\x00" in data:
        return "binary", False
    crlf = data.count(b"\r\n")
    remaining = data.replace(b"\r\n", b"")
    lf = remaining.count(b"\n")
    cr = remaining.count(b"\r")
    kinds = sum(bool(x) for x in (crlf, lf, cr))
    if kinds == 0:
        style = "none"
    elif kinds > 1:
        style = "mixed"
    elif crlf:
        style = "crlf"
    elif lf:
        style = "lf"
    else:
        style = "cr"
    final_newline = data.endswith((b"\n", b"\r"))
    return style, final_newline

def audit(root: Path, extensions: set[str]) -> tuple[int, str]:
    rows = []
    counts = Counter()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if extensions and path.suffix.lower() not in extensions:
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        style, final_newline = classify(data)
        counts[style] += 1
        rows.append((path.relative_to(root).as_posix(), style, final_newline))
    lines = [f"files={len(rows)}"]
    for name in ("lf", "crlf", "cr", "mixed", "none", "binary"):
        lines.append(f"{name}={counts[name]}")
    lines.append("missing_final_newline=" + str(sum(1 for _, style, final in rows if style != "binary" and not final)))
    for rel, style, final in rows:
        lines.append(f"{style}\tfinal_newline={'yes' if final else 'no'}\t{rel}")
    return (2 if counts["mixed"] else 0), "\n".join(lines)

def self_test() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.txt").write_bytes(b"a\nb\n")
        (root / "b.txt").write_bytes(b"a\r\nb\r\n")
        (root / "c.txt").write_bytes(b"a\r\nb\n")
        code, report = audit(root, {".txt"})
        assert code == 2
        assert "lf=1" in report and "crlf=1" in report and "mixed=1" in report
    print("SELF_TEST=PASS")

def main() -> int:
    ap = argparse.ArgumentParser(description="Audit text line endings in a directory tree.")
    ap.add_argument("root", nargs="?", type=Path, default=Path("."))
    ap.add_argument("--extensions", nargs="*", default=[], help="Optional suffix filter, for example .py .md")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    exts = {e.lower() if e.startswith(".") else "." + e.lower() for e in args.extensions}
    if not args.root.exists() or not args.root.is_dir():
        print("ERROR: root must be an existing directory", file=sys.stderr)
        return 1
    code, report = audit(args.root, exts)
    print(report)
    return code

if __name__ == "__main__":
    raise SystemExit(main())