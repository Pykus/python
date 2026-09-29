#!/usr/bin/env python3
"""JSON configuration drift reporter.

Purpose
-------
Compare two JSON documents by logical key path instead of raw text. It reports
added, removed and changed values and can ignore volatile paths such as
metadata.generated_at.

Run
---
python json_config_diff.py before.json after.json --ignore metadata.generated_at
python json_config_diff.py --self-test

Synthetic example
-----------------
before: {"service":{"port":8080,"enabled":true}}
after:  {"service":{"port":8081,"enabled":true}}

Expected output:
CHANGED service.port: 8080 -> 8081
SUMMARY added=0 removed=0 changed=1

The tool is read-only, uses only the standard library, and exits 3 when drift
is found, 0 when documents are equivalent, and 1 on input/runtime errors.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def flatten(value, prefix=""):
    out = {}
    if isinstance(value, dict):
        for key in sorted(value):
            path = f"{prefix}.{key}" if prefix else key
            out.update(flatten(value[key], path))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            out.update(flatten(item, f"{prefix}[{i}]"))
    else:
        out[prefix] = value
    return out

def compare(a, b, ignored):
    fa, fb = flatten(a), flatten(b)
    def keep(k): return not any(k == x or k.startswith(x + ".") or k.startswith(x + "[") for x in ignored)
    fa = {k:v for k,v in fa.items() if keep(k)}
    fb = {k:v for k,v in fb.items() if keep(k)}
    added = sorted(set(fb) - set(fa))
    removed = sorted(set(fa) - set(fb))
    changed = sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k])
    return fa, fb, added, removed, changed

def self_test():
    a = {"service":{"port":8080},"metadata":{"generated_at":"a"}}
    b = {"service":{"port":8081},"metadata":{"generated_at":"b"}}
    _,_,added,removed,changed = compare(a,b,{"metadata.generated_at"})
    assert not added and not removed and changed == ["service.port"]
    print("SELF_TEST_OK")

def main():
    p=argparse.ArgumentParser(description="Report logical drift between two JSON files.")
    p.add_argument("before", nargs="?"); p.add_argument("after", nargs="?")
    p.add_argument("--ignore", action="append", default=[], help="Exact path or subtree to ignore; repeatable.")
    p.add_argument("--self-test", action="store_true")
    a=p.parse_args()
    if a.self_test: self_test(); return 0
    if not a.before or not a.after: p.error("before and after are required unless --self-test is used")
    try:
        before=json.loads(Path(a.before).read_text(encoding="utf-8"))
        after=json.loads(Path(a.after).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR {e}", file=sys.stderr); return 1
    fa,fb,added,removed,changed=compare(before,after,set(a.ignore))
    for k in added: print(f"ADDED {k}: {fb[k]!r}")
    for k in removed: print(f"REMOVED {k}: {fa[k]!r}")
    for k in changed: print(f"CHANGED {k}: {fa[k]!r} -> {fb[k]!r}")
    print(f"SUMMARY added={len(added)} removed={len(removed)} changed={len(changed)}")
    return 3 if added or removed or changed else 0

if __name__=="__main__":
    raise SystemExit(main())