#!/usr/bin/env python3
"""Validate JSON Lines records against required fields.

Use: python jsonl_contract_check.py events.jsonl --required id timestamp status
Self-test: python jsonl_contract_check.py --self-test
Purpose: reject malformed JSONL, missing fields, and null required values before ingestion.
Synthetic record: {"id":"evt-1","timestamp":"2026-01-01T12:00:00Z","status":"ok"}
Expected: VALID and exit 0 for a valid file; detailed line errors and exit 2 otherwise.
"""
import argparse,json,tempfile
from pathlib import Path

def validate(path,required):
    errors=[]
    for n,raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(),1):
        if not raw.strip(): continue
        try: item=json.loads(raw)
        except json.JSONDecodeError as e: errors.append(f"line {n}: invalid JSON ({e.msg})"); continue
        if not isinstance(item,dict): errors.append(f"line {n}: record must be a JSON object"); continue
        for field in required:
            if field not in item: errors.append(f"line {n}: missing required field '{field}'")
            elif item[field] is None: errors.append(f"line {n}: required field '{field}' is null")
    return errors
def self_test():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"events.jsonl"; p.write_text('{"id":"a","status":"ok"}\n{"id":"b","status":null}\nnot-json\n',encoding="utf-8")
        e=validate(p,["id","status"])
    assert len(e)==2 and "is null" in e[0] and "invalid JSON" in e[1]
    print("SELF_TEST_OK")

def main():
    ap=argparse.ArgumentParser(description="Validate JSONL records against required fields.")
    ap.add_argument("jsonl",nargs="?",type=Path); ap.add_argument("--required",nargs="+",default=["id"]); ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test: self_test(); return 0
    if not a.jsonl: ap.error("jsonl is required unless --self-test is used")
    errors=validate(a.jsonl,a.required)
    if errors:
        print("\n".join(errors)); return 2
    print("VALID"); return 0
if __name__=="__main__": raise SystemExit(main())