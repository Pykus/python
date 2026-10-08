#!/usr/bin/env python3
"""
File age inventory.

Purpose
-------
Summarize files by modification-age buckets without reading file contents.
Useful for migration planning, archive cleanup, and storage reviews.

Usage
-----
python file_age_inventory.py .
python file_age_inventory.py data --now 2026-01-01T00:00:00+00:00
python file_age_inventory.py --self-test

Synthetic example
-----------------
Given files modified 3, 40, and 400 days before the reference time.

Expected behavior:
- classifies them into 0-7d, 31-90d, and >365d buckets
- reports file counts and bytes per bucket
- does not change timestamps or file contents

Exact expected stdout for three 10-byte files modified 3, 40, and 400 days before the supplied `--now` reference:
```text
bucket	files	bytes
0-7d	1	10
8-30d	0	0
31-90d	1	10
91-365d	0	0
>365d	1	10
```
Exit code: 0. These totals assume no other files in the example directory.
"""
from __future__ import annotations
import argparse,datetime as dt,os,sys,tempfile
from collections import defaultdict
from pathlib import Path

BUCKETS=[("0-7d",0,7),("8-30d",8,30),("31-90d",31,90),("91-365d",91,365),(">365d",366,None)]
def bucket(days:int)->str:
    for name,lo,hi in BUCKETS:
        if days>=lo and (hi is None or days<=hi): return name
    return "future"

def inventory(root:Path, now:dt.datetime)->str:
    stats=defaultdict(lambda:[0,0])
    for p in root.rglob("*"):
        if not p.is_file(): continue
        try: st=p.stat()
        except OSError: continue
        modified=dt.datetime.fromtimestamp(st.st_mtime,tz=dt.timezone.utc)
        days=max(0,int((now.astimezone(dt.timezone.utc)-modified).total_seconds()//86400))
        b=bucket(days); stats[b][0]+=1; stats[b][1]+=st.st_size
    lines=["bucket\tfiles\tbytes"]
    for name,_,_ in BUCKETS: lines.append(f"{name}\t{stats[name][0]}\t{stats[name][1]}")
    return "\n".join(lines)

def self_test():
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); now=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)
        for name,days in (("a",3),("b",40),("c",400)):
            p=r/name; p.write_bytes(b"x"*10); ts=(now-dt.timedelta(days=days)).timestamp(); os.utime(p,(ts,ts))
        out=inventory(r,now)
        assert "0-7d\t1\t10" in out and "31-90d\t1\t10" in out and ">365d\t1\t10" in out
    print("SELF_TEST=PASS")

def main()->int:
    ap=argparse.ArgumentParser(description="Summarize files by modification-age bucket.")
    ap.add_argument("root",nargs="?",type=Path,default=Path("."))
    ap.add_argument("--now",help="Reference ISO-8601 time. Defaults to current UTC time.")
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test: self_test(); return 0
    if not a.root.is_dir(): print("ERROR: root must be an existing directory",file=sys.stderr); return 1
    try: now=dt.datetime.fromisoformat(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
    except ValueError: print("ERROR: --now must be ISO-8601",file=sys.stderr); return 1
    if now.tzinfo is None: now=now.replace(tzinfo=dt.timezone.utc)
    print(inventory(a.root,now)); return 0
if __name__=="__main__": raise SystemExit(main())