# Changelog

No release or tag exists for this repository. The entry below describes the current state
of `main`.

## Unreleased (last commit 2026-09-25)

- Added CI (`.github/workflows/ci.yml`): installs elan with the Lean toolchain pinned in
  `lean/lean-toolchain` (4.30.0) and z3-solver 4.16.0, then runs `make all`.
- README: opens with the claim, a Try it block and a "What this does not show" section;
  states the commands that reproduce the counts (6 axiom-free theorems, 11 Z3 verdicts, 4
  negative controls). Added `CITATION.cff` and this changelog.
- 2026-09-25: README withdraws the universal "if and only if" on the aggregate boundary and
  states the two-instance contrast that is shown. Sealed records and source files unchanged.
- 2026-09-20: linked the AMLUCS 2026 evidence and poster.
- 2026-09-02: published. Lean 4 core (six theorems), three sealed Z3 records (eleven
  verdicts), the sealed learning-adversary record, and the Z3 and Lean negative controls.
  README attributes the perfect-security construction to Schroeder de Witt et al. (ICLR 2023)
  and the collusion setting to Motwani et al. (NeurIPS 2024).
