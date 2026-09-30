#!/usr/bin/env python3
"""Build or verify a deterministic SHA-256 directory manifest.

Build: python directory_manifest.py build --root ./bundle --output manifest.json
Verify: python directory_manifest.py verify --root ./bundle --manifest manifest.json
Self-test: python directory_manifest.py self-test
Purpose: detect accidental changes in deployment bundles, exports, or backups.
Synthetic example: a bundle containing readme.txt and config.json.
Expected: build writes relative paths/sizes/hashes; verify prints MATCH or drift records.
"""
import argparse,hashlib,json,tempfile
from pathlib import Path

def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(65536),b""): h.update(c)
    return h.hexdigest()

def snapshot(root):
    return {p.relative_to(root).as_posix():{"size":p.stat().st_size,"sha256":digest(p)}
            for p in sorted(x for x in root.rglob("*") if x.is_file())}

def verify(root,expected):
    current=snapshot(root); issues=[]
    for n in sorted(expected.keys()-current.keys()): issues.append(f"MISSING {n}")
    for n in sorted(current.keys()-expected.keys()): issues.append(f"EXTRA {n}")
    for n in sorted(expected.keys()&current.keys()):
        if expected[n]!=current[n]: issues.append(f"CHANGED {n}")
    return issues

def self_test():
    with tempfile.TemporaryDirectory() as d:
        r=Path(d)/"bundle"; r.mkdir(); (r/"readme.txt").write_text("hello",encoding="utf-8")
        baseline=snapshot(r); assert verify(r,baseline)==[]
        (r/"readme.txt").write_text("hello!",encoding="utf-8")
        assert verify(r,baseline)==["CHANGED readme.txt"]
    print("SELF_TEST_OK")

def main():
    ap=argparse.ArgumentParser(description="Build or verify a SHA-256 directory manifest."); sub=ap.add_subparsers(dest="cmd",required=True)
    b=sub.add_parser("build"); b.add_argument("--root",type=Path,required=True); b.add_argument("--output",type=Path,required=True)
    v=sub.add_parser("verify"); v.add_argument("--root",type=Path,required=True); v.add_argument("--manifest",type=Path,required=True)
    sub.add_parser("self-test"); a=ap.parse_args()
    if a.cmd=="self-test": self_test(); return 0
    if a.cmd=="build": a.output.write_text(json.dumps(snapshot(a.root),indent=2,sort_keys=True),encoding="utf-8"); print(f"WROTE {a.output}"); return 0
    issues=verify(a.root,json.loads(a.manifest.read_text(encoding="utf-8"))); print("\n".join(issues) if issues else "MATCH"); return 2 if issues else 0
if __name__=="__main__": raise SystemExit(main())