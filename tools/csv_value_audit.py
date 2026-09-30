#!/usr/bin/env python3
"""Audit CSV value quality with the Python standard library.

Use: python csv_value_audit.py data.csv
Self-test: python csv_value_audit.py --self-test
Purpose: profile missing values, uniqueness, and numeric parseability before ETL/import.
Synthetic example: name,age,team / Ada,36,blue / Ben,,red / Cy,41,blue.
Expected: one JSON object per column with rows, missing, unique_non_empty and numeric_parseable_pct.
"""
import argparse,csv,json,tempfile
from pathlib import Path

def audit(path):
    with path.open(newline="",encoding="utf-8-sig") as f:
        r=csv.DictReader(f)
        if not r.fieldnames: raise ValueError("CSV must contain a header row")
        rows=list(r)
    out=[]
    for name in r.fieldnames:
        vals=[(row.get(name,"") or "").strip() for row in rows]
        present=[v for v in vals if v]
        numeric=sum(1 for v in present if _is_number(v))
        out.append({"column":name,"rows":len(rows),"missing":len(rows)-len(present),
"unique_non_empty":len(set(present)),"numeric_parseable_pct":round(100*numeric/len(present),1) if present else 0.0})
    return out

def _is_number(value):
    try: float(value); return True
    except ValueError: return False

def self_test():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"sample.csv"; p.write_text("name,age,team\nAda,36,blue\nBen,,red\nCy,41,blue\n",encoding="utf-8")
        data=audit(p)
    assert data[1]["missing"]==1 and data[1]["numeric_parseable_pct"]==100.0
    assert data[2]["unique_non_empty"]==2
    print("SELF_TEST_OK")

def main():
    ap=argparse.ArgumentParser(description="Profile CSV column value quality.")
    ap.add_argument("csv",nargs="?",type=Path); ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test: self_test(); return
    if not a.csv: ap.error("csv is required unless --self-test is used")
    for item in audit(a.csv): print(json.dumps(item,ensure_ascii=True))
if __name__=="__main__": main()