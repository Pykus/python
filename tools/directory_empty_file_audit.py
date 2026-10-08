#!/usr/bin/env python3
"""
Directory empty-file auditor.

Purpose
-------
Find zero-byte files and empty directories before packaging, migration, backup,
or repository cleanup.

Usage
-----
python directory_empty_file_audit.py .
python directory_empty_file_audit.py data --include-empty-dirs --limit 50
python directory_empty_file_audit.py --self-test

Synthetic example
-----------------
A folder contains data.csv (100 bytes), placeholder.txt (0 bytes), and empty/.

Expected behavior:
- reports one empty file
- optionally reports one empty directory
- exits 2 when empty files or requested empty directories are found
"""
from __future__ import annotations
import argparse,sys,tempfile
from pathlib import Path

def audit(root:Path, include_dirs:bool, limit:int)->tuple[int,str]:
    empty_files=[]; empty_dirs=[]
    for p in sorted(root.rglob("*")):
        try:
            if p.is_file() and p.stat().st_size==0: empty_files.append(p.relative_to(root).as_posix())
        except OSError: pass
    if include_dirs:
        dirs=sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True)
        for d in dirs:
            try:
                if not any(d.iterdir()): empty_dirs.append(d.relative_to(root).as_posix())
            except OSError: pass
    lines=[f"empty_files={len(empty_files)}",f"empty_dirs={len(empty_dirs)}"]
    lines += [f"empty_file={x}" for x in empty_files[:limit]]
    lines += [f"empty_dir={x}" for x in empty_dirs[:limit]]
    return (2 if empty_files or empty_dirs else 0),"\n".join(lines)

def self_test():
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); (r/"full.txt").write_text("x",encoding="utf-8"); (r/"empty.txt").write_bytes(b""); (r/"emptydir").mkdir()
        code,out=audit(r,True,10)
        assert code==2 and "empty_files=1" in out and "empty_dirs=1" in out
        (r/"empty.txt").write_text("ok",encoding="utf-8"); (r/"emptydir"/"x").write_text("ok",encoding="utf-8")
        code,_=audit(r,True,10); assert code==0
    print("SELF_TEST=PASS")

def main()->int:
    ap=argparse.ArgumentParser(description="Audit zero-byte files and empty directories.")
    ap.add_argument("root",nargs="?",type=Path,default=Path("."))
    ap.add_argument("--include-empty-dirs",action="store_true")
    ap.add_argument("--limit",type=int,default=100)
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test: self_test(); return 0
    if not a.root.is_dir(): print("ERROR: root must be an existing directory",file=sys.stderr); return 1
    code,out=audit(a.root,a.include_empty_dirs,max(0,a.limit)); print(out); return code
if __name__=="__main__": raise SystemExit(main())