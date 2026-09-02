# collective-bound

The formal core behind one result: **a population of agents can each stay inside its own
cap while their draws together breach a shared pool, and a single rule on the sum removes
every such breach, with an exact statement of where that rule stops holding.**

This repository contains only what the published claims rest on, so that anyone can
re-derive them without access to the author's machine. It is the reproduction surface for
https://www.omegaprotocol.org/collective/ and for the AMLUCS 2026 poster
"Per-Agent Compliant, Collectively Unsafe: A Deployable Collective Bound for Colluding AI Agents".

## What is here

| part | files | what it establishes | checked by |
|---|---|---|---|
| Lean 4 core | `lean/CrossLayer/General.lean`, `lean/CrossLayer/AccumulationWitness.lean` | six theorems over closed data: cap 10, budget 40, six agents | the Lean 4.30.0 kernel; `#print axioms` reports no axioms for each |
| Z3 extensions | `z3/cce_model.py`, `z3/run_cce.py`, `z3/records/collective-collusion-000{1,2,3}.json` | eleven SAT/UNSAT verdicts with witnesses: the per-agent cap is defeated, the sum rule holds for every profile, the exact boundary (harm must factor through the aggregate), channel-blindness | z3 4.16.0; the sealed records regenerate byte for byte |
| Learning adversary | `z3/cce_rl.py`, `z3/run_rl.py`, `z3/records/collective-collusion-exp-0003.json` | 180,000 hold episodes never exceed the bound; three hand-built relaxations are each exploitable to the magnitude the law predicts, with a Z3 witness each | seeded numpy; the sealed record regenerates byte for byte (about 90 s) |
| Negative controls | `z3/controls/mutations.py`, `lean/controls/lean-mutation.sh` | three Z3 mutations flip their verdicts; one Lean mutation breaks the build | run them; a reproduction that cannot fail certifies nothing |

`z3/records/collective-collusion-exp-000{1,2}.json` are the two earlier experiment records
of the hash chain that `exp-0003` seals onto. They are included so the chain verifies; their
generators (a simulation stage and a steganographic-channel stage) are not part of this
artifact and nothing on the site rests on them.

## Reproduce

Requirements: Lean 4.30.0 through [elan](https://github.com/leanprover/elan) (the
`lean/lean-toolchain` file pins it), Python 3.10 or newer, `pip install -r z3/requirements.txt`
(z3-solver 4.16.0, numpy). No network access is needed after that.

```
make lean       # kernel-checks both files
make axioms     # prints "does not depend on any axioms" for each of the six theorems, then the two totals 60 and 40
make z3         # re-derives the three proof records into z3/out/ and compares with z3/records/ byte for byte
make controls   # three Z3 mutations must flip; the Lean budget mutation must fail to build
make rl         # re-runs the learning adversary (about 90 s) and compares with the sealed exp-0003 record
```

Expected sealed content hashes, which `make z3` and `make rl` must reproduce exactly:

```
collective-collusion-0001      3fd7b869901c69430c41d64306ea6fd954cc2f4fe1d8ab2f300702fd36615fb3
collective-collusion-0002      95a0989fed30781002aa34bd24b16cfcf5396d7df83a363738bb198970824440
collective-collusion-0003      34142856bfe3b0f1144debde6282d8ab7236f58b99416babc1d95eef4079a220
collective-collusion-exp-0003  23f5d07874bc6ebf2e7f6386edd3b75f9026225ecfbc37f82459cb69979f6a2d
```

A different z3 release may print the same verdicts with a different witness for a SAT query
and therefore a different hash. The verdicts are the claim; the hash is the seal on this
exact run.

## The six Lean theorems

Parameters: `perCap = 10`, `budget = 40`, `witnessProfile = [10,10,10,10,10,10]` (total 60),
`benignProfile = [10,10,10,10,0,0]` (total 40).

| theorem | plain reading |
|---|---|
| `per_agent_cap_insufficient` | a profile in which every agent is within its cap breaches the budget |
| `conserved_meter_removes_witness` | for every profile the conserved meter accepts, the budget is not breached |
| `conserved_meter_not_vacuous` | the meter still accepts a within-budget profile |
| `accumulation_conflates` | the per-agent observation cannot distinguish a violating population from a compliant one |
| `accumulation_witness` | a concrete witness of that conflation exists |
| `conserved_meter_captures` | the sum observation decides the violation exactly |

Zero `sorry`, `admit` or `native_decide` in code; the two files are the whole development
(`General.lean` is the abstract witness/repair law the instance is built on).

## The eleven Z3 queries

Instance: N = 6, per-agent cap 10, pool G = 40, allocation threshold h = 15, victim = agent 2.
Collusion is modelled as joint worst-case action: an existential over the whole draw vector,
so an UNSAT breach query holds against every coordination strategy at once.

| record | query | verdict | witness |
|---|---|---|---|
| 0001 | per_agent_defeated | SAT | [10,10,10,10,10,10], sum 60 > 40 |
| 0001 | conserved_meter_holds | UNSAT | |
| 0001 | meter_not_vacuous | SAT | [35,1,1,1,1,1], sum 40 |
| 0002 | conserved_bounded | UNSAT | |
| 0002 | allocation_escapes | SAT | [0,0,16,0,0,0], sum 16 <= 40, victim draw 16 > 15 |
| 0002 | factors_conserved | UNSAT | |
| 0002 | factors_allocation | SAT | [0,0,1,0,0,0] harm 1 versus [1,0,0,0,0,0] harm 0 |
| 0002 | allocation_meter_closes | UNSAT | |
| 0003 | detection_defeated | SAT | colluding [10,...] and innocent [1,...] share observation [0,0] |
| 0003 | meter_channel_blind | UNSAT | |
| 0003 | bound_survives | UNSAT | |

## The learning adversary

Independent tabular Q-learners with a shared team reward, rewarded to drive the shared draw
over the cap, with full sight of the meter's state, horizon T = 8. Hold: 2 instances
(N = 6, G = 40 and N = 10, G = 63) × 3 seeds × 30,000 episodes = 180,000; the realised
aggregate never exceeded G. The bound is the Z3 UNSAT result; the run corroborates that no
learned policy evaded it. Three relaxations, one per precondition, were hand-built in advance
and run for 15,000 episodes each; the learner reached the predicted magnitude at every sweep
point:

| precondition relaxed | law | sweep (learner max = Z3 max) |
|---|---|---|
| P1 harm factors through the aggregate | allocation harm escapes to G | victim draw 40 against h = 15 |
| P2 conserved over the full horizon | cumulative = ceil(T / period) × G | period 8: 40 (UNSAT); 4: 80; 2: 160; 1: 320 |
| P3 atomic observation | true aggregate = delay × G | delay 1: 40 (UNSAT); 2: 80; 3: 120; 4: 160 |

The learner did not discover these preconditions. They were specified first and the learner
confirmed each is exploitable as far as predicted.

## Frame, trusted base, limitations

- Everything here is a statement about the encoded model: one shared scalar pool, one round,
  integer draws, a known population. Nothing here is a claim about any deployed multi-agent
  system, and the Lean results are over closed data (this profile shape only).
- Trusted base for the Lean part: the Lean 4 kernel and toolchain. For the Z3 part: the solver
  and the faithfulness of a linear-integer encoding to the informal model; the boundary
  (harm factors through the aggregate) is not re-proved in Lean.
- The channel-blindness result (0003) encodes the *conclusion* of perfectly secure
  steganography (identical observations, KL = 0) as the adversary, following
  Schroeder de Witt et al., *Secret Collusion among AI Agents*, NeurIPS 2024
  (https://arxiv.org/abs/2402.07510). It does not re-derive that construction.
- The per-agent cap is not shown to be unfixable. A local allowance of floor(G / N) is
  collectively safe when the population and its utilisation are known and fixed; what the
  results show is that the local rule needs assumptions the sum rule does not.
- This work was not preregistered. The companion empirical study on language-model agents,
  https://github.com/repowazdogz-droid/commons-agent-lab, was.
- Independent reproduction by someone other than the author: none known. If you run this and
  the hashes match, you are the first, and the site will say so.

## Provenance

See [PROVENANCE.md](PROVENANCE.md). Short form: the files are copied unmodified from two
private research repositories at named commits, with the seal package vendored from a public
repository where it already appears; one runner file (`reproduce.py`, `reproduce_rl.py`) and
the controls were written for this artifact. The history of this repository starts at its
publication and does not reconstruct the private history.

## Licence

MIT. Copyright Warren Smith, 2026.
