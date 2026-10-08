#!/usr/bin/env python3
"""
CSV column profiler.

Purpose
-------
Summarize completeness and basic shape for every CSV column without printing
raw values. Useful before imports, schema design, and data-cleaning work.

Usage
-----
python csv_column_profile.py data.csv
python csv_column_profile.py data.csv --top 20
python csv_column_profile.py --self-test

Synthetic example
-----------------
Input:
id,age,city
A-1,42,North
A-2,,South
A-3,37,

Expected behavior:
- reports row_count=3
- reports non_empty, blank, unique, numeric, min_length, max_length per column
- never prints the original cell values
"""
from __future__ import annotations
import argparse,csv,sys,tempfile
from pathlib import Path

def profile(path:Path, top:int)->str:
    with path.open("r",encoding="utf-8-sig",newline="") as fh:
        reader=csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")
        stats={name:{"non_empty":0,"blank":0,"values":set(),"numeric":0,"min_len":None,"max_len":0} for name in reader.fieldnames}
        rows=0
        for row in reader:
            rows+=1
            for name in reader.fieldnames:
                value=(row.get(name) or "").strip()
                st=stats[name]
                if not value:
                    st["blank"]+=1
                    continue
                st["non_empty"]+=1
                st["values"].add(value)
                ln=len(value)
                st["min_len"]=ln if st["min_len"] is None else min(st["min_len"],ln)
                st["max_len"]=max(st["max_len"],ln)
                try: float(value); st["numeric"]+=1
                except ValueError: pass
    lines=[f"row_count={rows}","column\tnon_empty\tblank\tunique\tnumeric\tmin_length\tmax_length"]
    for name in reader.fieldnames[:top]:
        st=stats[name]
        lines.append(f"{name}\t{st['non_empty']}\t{st['blank']}\t{len(st['values'])}\t{st['numeric']}\t{st['min_len'] or 0}\t{st['max_len']}")
    return "\n".join(lines)

def self_test():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"sample.csv"
        p.write_text("id,age,city\nA-1,42,North\nA-2,,South\nA-3,37,\n",encoding="utf-8")
        r=profile(p,20)
        assert "row_count=3" in r
        assert "age\t2\t1\t2\t2" in r
        assert "city\t2\t1\t2\t0" in r
        assert "North" not in r and "South" not in r
    print("SELF_TEST=PASS")

def main()->int:
    ap=argparse.ArgumentParser(description="Profile CSV columns without printing raw values.")
    ap.add_argument("csv_file",nargs="?",type=Path)
    ap.add_argument("--top",type=int,default=200)
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test: self_test(); return 0
    if not a.csv_file: ap.error("csv_file is required unless --self-test is used")
    try: print(profile(a.csv_file,max(0,a.top))); return 0
    except (OSError,ValueError,csv.Error) as e:
        print(f"ERROR: {e}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())