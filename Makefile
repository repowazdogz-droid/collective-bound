.PHONY: all lean axioms z3 controls rl clean
all: lean axioms z3 controls   ## everything the published claims rest on (the RL re-run is separate: see rl)

lean:                         ## kernel-check the two Lean files (Lean 4.30.0 via elan)
	cd lean && lake build

axioms: lean                  ## print the axiom audit for the six theorems; every line must say "does not depend on any axioms"
	cd lean && lake env lean Axioms.lean

z3:                           ## re-derive the three sealed proof records and compare them byte for byte
	cd z3 && python3 reproduce.py

controls:                     ## negative controls: three Z3 mutations must flip their verdicts; one Lean mutation must fail to build
	cd z3 && python3 controls/mutations.py
	cd lean && ./controls/lean-mutation.sh

rl:                           ## re-run the 180,000-episode learning adversary and compare with the sealed record (slow)
	cd z3 && python3 reproduce_rl.py

clean: ; rm -rf lean/.lake z3/out
