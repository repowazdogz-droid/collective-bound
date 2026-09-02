#!/usr/bin/env python3
"""Re-derive the three proof records (T1-T3) from source and compare them byte for byte with
the sealed records in records/. Writes only under out/. Exit 0 iff every verdict, witness and
content hash matches."""
import sys, os, json, filecmp, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor"))   # omega_seal, vendored unmodified
sys.path.insert(0, str(HERE))
import run_cce
OUT = HERE / "out" / "proofs"; OUT.mkdir(parents=True, exist_ok=True)
run_cce.RECORDS = str(OUT)
run_cce.main()
ok = True
for rid in ("0001", "0002", "0003"):
    a = HERE / "records" / f"collective-collusion-{rid}.json"; b = OUT / f"collective-collusion-{rid}.json"
    same = filecmp.cmp(a, b, shallow=False)
    ha, hb = json.load(open(a))["content_hash"], json.load(open(b))["content_hash"]
    print(f"record {rid}: {'IDENTICAL' if same else 'DIFFERENT'}  sealed {ha[:16]}  regenerated {hb[:16]}")
    ok &= same
try:
    import z3; print("z3", z3.get_version_string())
except Exception as e: print("z3 version unavailable:", e)
sys.exit(0 if ok else 1)
