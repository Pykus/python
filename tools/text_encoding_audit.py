#!/usr/bin/env python3
"""
Text encoding auditor.

Purpose
-------
Scan likely text files and identify UTF-8, UTF-8 with BOM, undecodable bytes,
and binary-looking content. Useful before cross-platform migration or CI checks.

Usage
-----
python text_encoding_audit.py .
python text_encoding_audit.py src --extensions .py .md .json
python text_encoding_audit.py --self-test

Synthetic example
-----------------
A folder contains utf8.txt, bom.txt, and binary.bin.

Expected behavior:
- classifies UTF-8 and UTF-8-BOM separately
- reports binary-looking files without decoding them
- exits 2 when undecodable text-like files are found

For a reproducible example, create `utf8.txt` containing UTF-8 text, `bom.txt` containing a UTF-8 BOM followed by text, and `invalid.txt` containing byte 0xFF. Run `python text_encoding_audit.py sample --extensions .txt`.

Exact expected stdout:
```text
files=3
utf8=1
utf8-bom=1
invalid=1
binary=0
utf8-bom	bom.txt
invalid	invalid.txt
utf8	utf8.txt
```
Exit code: 2. The tool sorts filenames and does not print file contents. Note that a file containing NUL bytes would be reported as `binary`.
"""
from __future__ import annotations
import argparse,sys,tempfile
from collections import Counter
from pathlib import Path

def classify(data:bytes)->str:
    if b"\x00" in data: return "binary"
    if data.startswith(b"\xef\xbb\xbf"):
        try: data[3:].decode("utf-8"); return "utf8-bom"
        except UnicodeDecodeError: return "invalid"
    try: data.decode("utf-8"); return "utf8"
    except UnicodeDecodeError: return "invalid"

def audit(root:Path, exts:set[str])->tuple[int,str]:
    rows=[]; counts=Counter()
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        if exts and p.suffix.lower() not in exts: continue
        try: kind=classify(p.read_bytes())
        except OSError: continue
        counts[kind]+=1; rows.append((p.relative_to(root).as_posix(),kind))
    lines=[f"files={len(rows)}"]+[f"{k}={counts[k]}" for k in ("utf8","utf8-bom","invalid","binary")]
    lines += [f"{kind}\t{name}" for name,kind in rows]
    return (2 if counts["invalid"] else 0),"\n".join(lines)

def self_test():
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); (r/"a.txt").write_text("hello",encoding="utf-8"); (r/"b.txt").write_bytes(b"\xef\xbb\xbfhello"); (r/"c.txt").write_bytes(b"\xff\xfeA")
        code,out=audit(r,{".txt"})
        assert code==2 and "utf8=1" in out and "utf8-bom=1" in out and "invalid=1" in out
    print("SELF_TEST=PASS")

def main()->int:
    ap=argparse.ArgumentParser(description="Audit text encodings in a directory tree.")
    ap.add_argument("root",nargs="?",type=Path,default=Path("."))
    ap.add_argument("--extensions",nargs="*",default=[])
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test: self_test(); return 0
    if not a.root.is_dir(): print("ERROR: root must be an existing directory",file=sys.stderr); return 1
    exts={x.lower() if x.startswith(".") else "."+x.lower() for x in a.extensions}
    code,out=audit(a.root,exts); print(out); return code
if __name__=="__main__": raise SystemExit(main())