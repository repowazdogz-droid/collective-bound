/-
CASE 5 -- ACCUMULATED ACTIONS omitted. A new "meter the aggregate" instance of the
general law (CrossLayer/General.lean). This is a Lean kernel-checked counterpart of
the collective-collusion result: per-agent-compliant draws whose collective sum
breaches a budget, closed by a conserved meter.

NOTE ON SCOPE / HONESTY: this file provides the kernel-checked WITNESS and REPAIR
instance ONLY. The exact boundary -- that a conserved meter bounds the collective
harm IFF the harm factors through the aggregate, and provably fails for
allocation-dependent harm -- is the separate Z3 result (collective-collusion,
sound within its linear-integer encoding) and is NOT re-proved here. Do not read
this file as mechanising that iff.

THE OMITTED VARIABLE: the accumulated / aggregate state. The per-agent rule reads
each agent's own draw against a per-agent cap but never the running total; a set of
individually-compliant draws can sum past the collective budget.

  * WITNESS: every agent draws exactly the per-agent cap (`perCap`), so every
    per-agent check passes; with enough agents the total exceeds the collective
    budget (`N * perCap > budget`). The collective objective is violated.
    `accumulation_witness`, via `omission_has_witness`.

  * REPAIR (the conserved meter): observe the aggregate `g p = total p`; it DECIDES
    the objective (`conserved_meter_captures`, by `Iff.rfl`), so the metered relation
    removes every witness (`conserved_meter_removes_witness`, via `captures_repairs`).

This is the AGGREGATE-METER repair shape, shared with Case 4b (CrossLayer/
ForkWitness.lean): the same meter on a population here, a delegation tree there.

DISCIPLINE: kernel-checked, zero `sorry`/`admit`/`native_decide`, no user axioms;
hand-rolled recursive folds (NO `List.map`/`List.all`), everything reduces to `rfl`
/ `decide` over closed data. Audited with `#print axioms`. ADDITIVE: existing files
byte-unchanged; new root in `lakefile.lean`.
-/

import CrossLayer.General

namespace CrossLayer.AccumulationWitness

open CrossLayer.General

/-! ### The population model -/

/-- A profile of per-agent draws (one round). -/
abbrev Profile := List Nat

/-- The per-agent cap (the local rule each agent obeys). -/
def perCap : Nat := 10

/-- The collective budget (the aggregate bound). With `N = 6` agents at the cap,
    `6 * 10 = 60 > 40 = budget`, which is exactly when the per-agent rule is defeated. -/
def budget : Nat := 40

/-- The per-agent local check: this agent's draw is within the per-agent cap. -/
def agentOK (d : Nat) : Bool := Nat.ble d perCap

/-- Weak observation: the list of per-agent verdicts. Hand-rolled recursion so it
    reduces under `rfl`. Carries no aggregate. -/
def bits : Profile → List Bool
  | []        => []
  | d :: rest => agentOK d :: bits rest

/-- Every agent passes its own cap check (no `List.all`). -/
def allTrue : List Bool → Bool
  | []        => true
  | b :: rest => b && allTrue rest

/-- Weak relation: every per-agent cap check passes. -/
def ConsCap (os : List Bool) : Prop := allTrue os = true

/-- The aggregate the per-agent relation omits: the running total. -/
def total : Profile → Nat
  | []        => 0
  | d :: rest => d + total rest

/-- Security objective / forbidden behaviour: the collective total exceeds the
    budget. Reducible so `decide` sees through it. -/
@[reducible] def PViolates (p : Profile) : Prop := Nat.blt budget (total p) = true

/-! ### Concrete profiles -/

/-- The collusion witness: six agents, each drawing exactly the per-agent cap. Every
    per-agent check passes; the total `60 > 40` breaches the budget. -/
def witnessProfile : Profile := [perCap, perCap, perCap, perCap, perCap, perCap]

/-- The benign partner: same per-agent verdicts (each draw within the cap), but the
    last two draw nothing, so the total stays within budget. -/
def benignProfile : Profile := [perCap, perCap, perCap, perCap, 0, 0]

/-! ### Witness side -- the omission conflates, hence a witness exists -/

/-- The per-agent observation conflates the colluding profile with the benign one:
    identical per-agent verdicts `[true, ..., true]`, the relation accepts, the first
    breaches the budget and the second does not. The conflated variable is the total. -/
theorem accumulation_conflates : Conflates bits ConsCap PViolates :=
  ⟨witnessProfile, benignProfile, rfl, rfl, rfl, by decide⟩

/-- A witness exists, via the general omission law. -/
theorem accumulation_witness : HasWitness bits ConsCap PViolates :=
  omission_has_witness accumulation_conflates

/-- The generic "per-agent enforcement is insufficient" form: every agent obeys the
    per-agent cap, yet the collective total breaches the budget. -/
theorem per_agent_cap_insufficient :
    allTrue (bits witnessProfile) = true ∧ PViolates witnessProfile :=
  ⟨rfl, rfl⟩

/-! ### Repair side -- the conserved meter DECIDES the objective -/

/-- The added observation: the conserved meter (running total). -/
def gSum (p : Profile) : Nat := total p

/-- The decision predicate: the total exceeds the budget. -/
@[reducible] def decSum (_ : List Bool) (s : Nat) : Prop := Nat.blt budget s = true

/-- `Captures` holds by `Iff.rfl`: `PViolates p` and `decSum (bits p) (gSum p)` are
    the same predicate. -/
theorem conserved_meter_captures : Captures bits gSum PViolates decSum := fun _ => Iff.rfl

/-- THE REPAIR: the conserved-meter relation removes every collusion witness, via the
    general `captures_repairs`. -/
theorem conserved_meter_removes_witness :
    ∀ p, ConsRepaired ConsCap decSum (bits p) (gSum p) → ¬ PViolates p :=
  captures_repairs conserved_meter_captures

/-- The repair is not vacuous: it still accepts the within-budget benign profile. -/
theorem conserved_meter_not_vacuous :
    ConsRepaired ConsCap decSum (bits benignProfile) (gSum benignProfile) :=
  ⟨rfl, by decide⟩

/-! ### Axiom audit -/

#print axioms accumulation_conflates
#print axioms accumulation_witness
#print axioms per_agent_cap_insufficient
#print axioms conserved_meter_captures
#print axioms conserved_meter_removes_witness
#print axioms conserved_meter_not_vacuous

end CrossLayer.AccumulationWitness
