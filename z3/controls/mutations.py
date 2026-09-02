#!/usr/bin/env python3
"""NEGATIVE CONTROLS for the Z3 core. A reproduction that could not fail would certify nothing.
Each mutation changes ONE parameter of the model and the named verdict must FLIP; the unmutated
baseline must still give the published verdict. Exit non-zero if any expectation is not met."""
import sys, pathlib
HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import cce_model as M
from cce_model import Params
BASE = Params(N=6, per_cap=10, G=40, h=15, victim=2, min_viable=1)   # the published instance
CASES = [
  # label, params, query, expected baseline verdict, expected mutated verdict, why
  ("per-agent cap small enough that N*cap <= G", Params(N=6, per_cap=6, G=40, h=15, victim=2, min_viable=1),
   M.t1_per_agent_defeated, "sat", "unsat", "with 6 x 6 = 36 <= 40 no compliant profile can breach; the per-agent cap is then sufficient"),
  ("allocation threshold raised to the pool", Params(N=6, per_cap=10, G=40, h=40, victim=2, min_viable=1),
   M.t2_allocation_escapes, "sat", "unsat", "with h = G the victim cannot exceed h while the sum stays <= G; allocation harm no longer escapes"),
  ("meter bound below the smallest viable profile", Params(N=6, per_cap=10, G=5, h=15, victim=2, min_viable=1),
   M.t1_meter_not_vacuous, "sat", "unsat", "six agents each drawing at least 1 cannot sum to exactly 5; the meter becomes vacuous"),
]
def verdict(r): return str(r.get("verdict", r.get("status", ""))).lower()
bad = 0
for label, mut, fn, exp_base, exp_mut, why in CASES:
    vb, vm = verdict(fn(BASE)), verdict(fn(mut))
    ok = (vb == exp_base) and (vm == exp_mut)
    bad += 0 if ok else 1
    print(f"{'OK ' if ok else '** '} {fn.__name__:28s} baseline {vb:5s} (expected {exp_base})  mutated {vm:5s} (expected {exp_mut})  [{label}]")
    if not ok: print("     ", why)
sys.exit(1 if bad else 0)
