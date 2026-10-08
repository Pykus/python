#!/usr/bin/env python3
"""
JSONL field consistency checker.

Purpose
-------
Detect inconsistent object fields across JSON Lines records before ingestion.
The tool reports field presence counts and line numbers with missing fields.

Usage
-----
python jsonl_field_consistency.py events.jsonl
python jsonl_field_consistency.py events.jsonl --required id --required timestamp
python jsonl_field_consistency.py --self-test

Synthetic example
-----------------
Input:
{"id":1,"name":"Ada"}
{"id":2}
{"id":3,"name":"Lin"}

Expected behavior:
- reports records=3
- reports id present on 3 lines and name on 2
- with --required name, reports line 2 as missing and exits 2

Exact expected stdout for `python jsonl_field_consistency.py events.jsonl --required name`:
```text
records=3
field	present	missing
id	3	0
name	2	1
missing_required=name; lines=2
```
Exit code: 2. Without `--required name`, omit the last line and exit with code 0.
"""
from __future__ import annotations
import argparse,json,sys,tempfile
from collections import Counter,defaultdict
from pathlib import Path

def check(path:Path, required:list[str], limit:int)->tuple[int,str]:
    present=Counter(); missing=defaultdict(list); records=0
    with path.open("r",encoding="utf-8-sig") as fh:
        for line_no,line in enumerate(fh,1):
            if not line.strip(): continue
            obj=json.loads(line)
            if not isinstance(obj,dict): raise ValueError(f"Line {line_no} is not a JSON object.")
            records+=1
            for k in obj: present[k]+=1
            for k in required:
                if k not in obj: missing[k].append(line_no)
    lines=[f"records={records}","field\tpresent\tmissing"]
    for k in sorted(present.keys()|set(required)):
        lines.append(f"{k}\t{present[k]}\t{records-present[k]}")
    for k in required:
        if missing[k]:
            lines.append(f"missing_required={k}; lines={','.join(map(str,missing[k][:limit]))}")
    return (2 if any(missing.values()) else 0),"\n".join(lines)

def self_test():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"x.jsonl"; p.write_text('{"id":1,"name":"Ada"}\n{"id":2}\n{"id":3,"name":"Lin"}\n',encoding="utf-8")
        code,r=check(p,["name"],10)
        assert code==2 and "records=3" in r and "name\t2\t1" in r and "lines=2" in r
        code,_=check(p,["id"],10); assert code==0
    print("SELF_TEST=PASS")

def main()->int:
    ap=argparse.ArgumentParser(description="Check JSONL field consistency.")
    ap.add_argument("jsonl_file",nargs="?",type=Path)
    ap.add_argument("--required",action="append",default=[])
    ap.add_argument("--limit",type=int,default=20)
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test: self_test(); return 0
    if not a.jsonl_file: ap.error("jsonl_file is required unless --self-test is used")
    try:
        code,r=check(a.jsonl_file,a.required,max(0,a.limit)); print(r); return code
    except (OSError,ValueError,json.JSONDecodeError) as e:
        print(f"ERROR: {e}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())