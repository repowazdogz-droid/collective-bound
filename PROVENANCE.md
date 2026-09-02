# Provenance

This artifact was extracted on 2 September 2026 from two private research repositories. It
was created so that the claims on https://www.omegaprotocol.org/collective/ can be re-derived
without access to the author's machine. Nothing in the extracted files was edited.

| file(s) | source | commit | note |
|---|---|---|---|
| `lean/CrossLayer/General.lean`, `lean/CrossLayer/AccumulationWitness.lean`, `lean/lean-toolchain` | private repository `honest-layer-witness` (a larger Lean development of which these are two of 23 files) | `2f23868` | byte-identical copies; `AccumulationWitness.lean` imports only `General.lean` |
| `lean/lakefile.lean`, `lean/Axioms.lean` | written for this artifact | | the lakefile lists only the two roots; `Axioms.lean` is the audit probe |
| `z3/cce_model.py`, `z3/cce_record.py`, `z3/run_cce.py`, `z3/cce_rl.py`, `z3/run_rl.py` | private repository `collective-collusion` | `155f500` | byte-identical copies of the committed versions |
| `z3/records/collective-collusion-*.json` | private repository `collective-collusion` | `155f500` | the sealed records, unmodified; `0001` to `0003` dated June 2026, `exp-0003` July 2026 |
| `z3/vendor/omega_seal/` | https://github.com/repowazdogz-droid/proof-carrying-evals (`vendor/omega_seal`, itself vendored from the private `omega-seal` package, MIT) | | byte-identical to the installed package the records were sealed with |
| `z3/reproduce.py`, `z3/reproduce_rl.py`, `z3/controls/mutations.py`, `lean/controls/lean-mutation.sh`, `Makefile`, `README.md`, this file | written for this artifact | | runners write only under `out/` or a temporary directory |

What was NOT carried over: the paper drafts, the simulation and steganographic-channel stages
(`cce_sim.py`, `cce_stego.py`, `run_sim.py`, `run_stage2.py`) and their figures, an unfinished
extension of the model (uncommitted in the source repository), and the other 21 files of the
Lean development. None of the published claims rest on them.

Verification performed before publication, all on 2 September 2026: `lake build` and the axiom
audit on the extracted Lean files; `reproduce.py` regenerating records 0001 to 0003
byte-identically under z3 4.16.0; `reproduce_rl.py` regenerating `exp-0003` byte-identically in
89 seconds; the three Z3 mutation controls and the Lean mutation control all failing as
required; a scan of every file for paths, hostnames, addresses and credentials.

The git history of this repository begins with its publication. It does not reconstruct the
private history and should not be read as a timeline of the research.
