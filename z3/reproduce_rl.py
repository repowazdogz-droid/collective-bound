#!/usr/bin/env python3
"""Re-run the learning-adversary stage (exp-0003) and compare with the sealed record.
Slow: 180,000 hold episodes plus the three relaxation sweeps. Writes only under out/."""
import sys, os, json, filecmp, pathlib, shutil, time
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor")); sys.path.insert(0, str(HERE))
import run_rl
OUT = HERE / "out" / "rl"; (OUT / "records").mkdir(parents=True, exist_ok=True); (OUT / "paper").mkdir(exist_ok=True)
for r in ("0001","0002","0003","exp-0001","exp-0002"):   # chain context the stage seals onto
    shutil.copy(HERE / "records" / f"collective-collusion-{r}.json", OUT / "records")
run_rl.RECORDS = str(OUT / "records"); run_rl.PAPER = str(OUT / "paper")
t0 = time.time(); run_rl.main(); print(f"elapsed {time.time()-t0:.0f}s")
a = HERE / "records" / "collective-collusion-exp-0003.json"; b = OUT / "records" / "collective-collusion-exp-0003.json"
same = filecmp.cmp(a, b, shallow=False)
print("exp-0003:", "IDENTICAL" if same else "DIFFERENT", json.load(open(a))["content_hash"][:16], json.load(open(b))["content_hash"][:16])
sys.exit(0 if same else 1)
