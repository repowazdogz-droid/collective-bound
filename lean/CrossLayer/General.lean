/-
THE ABSTRACTION FRONTIER: the general law the single-step (egress) and multi-step
(provenance) results are instances of.

A consistency relation's verdict factors through a function `obs : E → O` (a
projection in single-step, a fold in multi-step). The objective is `Violates`.
The whole development reduces to: does `obs` determine `Violates`?

This file proves the abstract laws and pins down EXACTLY which condition governs
which half:

  * WITNESS side -- the weak `Conflates` condition (the observation conflates a
    violating execution with an accepted safe one) suffices:
        `omission_has_witness : Conflates → HasWitness`.

  * REFINEMENT -- adding an observation `g` that `Separates` (never conflates a
    violation with a safe execution) removes the conflation:
        `separates_removes_conflation : Separates → ¬ Conflates2 (any relation)`.

  * REPAIR side -- `Separates` is NECESSARY but NOT SUFFICIENT for an adequate
    repair. The repair theorem needs the STRONGER `Captures` (the observation
    DECIDES `Violates`):
        `captures_repairs : Captures → repaired relation has no witness`,
    and `separates_not_sufficient` exhibits a concrete setting where `Separates`
    holds yet a relation still admits a witness.

The finding (see CrossLayer/GeneralInstances.lean for the two recoveries): the
witness and repair halves are governed by DIFFERENT conditions. `Separates`
characterises conflation-removal; `Captures` (decidability of the objective from
the observation) is what the repair actually needs. Both instances satisfy
`Captures` (single-step trivially, multi-step by induction); `Separates` alone
never recovers a repair.

DISCIPLINE: kernel-checked, zero `sorry`, no user axioms (propext-free: the proofs
use `Iff`/`And`/`Exists` introduction and elimination, `subst`, `congrArg` -- never
`simp` with `Iff` lemmas, never wildcard matches). ADDITIVE: existing files
byte-unchanged; new root in `lakefile.lean`.
-/

namespace CrossLayer.General

universe u v w
variable {E : Type u} {O : Type v} {V : Type w}

/-! ### Core objects: an observation, a relation on it, an objective -/

/-- A witness: the relation (on the honest observation) accepts a violating execution. -/
def HasWitness (obs : E → O) (Cons : O → Prop) (Violates : E → Prop) : Prop :=
  ∃ e, Cons (obs e) ∧ Violates e

/-- Adequacy: acceptance entails the objective is not violated. -/
def Adequate (obs : E → O) (Cons : O → Prop) (Violates : E → Prop) : Prop :=
  ∀ e, Cons (obs e) → ¬ Violates e

/-- THE OMISSION PREDICATE. The observation CONFLATES a violating execution with
    an accepted safe one: two executions the relation cannot tell apart, one of
    which violates and one of which is benign and accepted. Strictly stronger than
    `HasWitness` (it additionally exhibits the safe partner), so it is a structural
    cause, not a restatement of the conclusion. -/
def Conflates (obs : E → O) (Cons : O → Prop) (Violates : E → Prop) : Prop :=
  ∃ e_bad e_ok, obs e_bad = obs e_ok
              ∧ Cons (obs e_ok) ∧ Violates e_bad ∧ ¬ Violates e_ok

/-! ### Witness law -- the weak condition suffices -/

/-- The omission (conflation) produces a witness. The violating `e_bad` is accepted
    because it is observationally identical to the accepted safe `e_ok`. -/
theorem omission_has_witness {obs : E → O} {Cons : O → Prop} {Violates : E → Prop}
    (h : Conflates obs Cons Violates) : HasWitness obs Cons Violates := by
  obtain ⟨e_bad, e_ok, hobs, hcons, hvb, _⟩ := h
  refine ⟨e_bad, ?_, hvb⟩
  rw [hobs]; exact hcons

/-! ### Refinement -- adding `g` that Separates removes the conflation -/

/-- The refinement condition: `(obs, g)` together never conflate a violating with a
    safe execution. Equivalently, `Violates` is constant on the fibres of `(obs, g)`. -/
def Separates (obs : E → O) (g : E → V) (Violates : E → Prop) : Prop :=
  ∀ e1 e2, obs e1 = obs e2 ∧ g e1 = g e2 → (Violates e1 ↔ Violates e2)

/-- The refined observation. -/
def Obs2 (obs : E → O) (g : E → V) : E → O × V := fun e => (obs e, g e)

/-- Conflation at the refined level, for an arbitrary relation on the refined
    observation. -/
def Conflates2 (obs : E → O) (g : E → V) (Violates : E → Prop)
    (Cons2 : O × V → Prop) : Prop :=
  ∃ e_bad e_ok, Obs2 obs g e_bad = Obs2 obs g e_ok
              ∧ Cons2 (Obs2 obs g e_ok) ∧ Violates e_bad ∧ ¬ Violates e_ok

/-- Adding an observation that `Separates` removes the conflation entirely: no
    relation on the refined observation can conflate a violation with a safe
    execution. This is what `Separates` buys, and all it buys. -/
theorem separates_removes_conflation {obs : E → O} {g : E → V} {Violates : E → Prop}
    (hsep : Separates obs g Violates) (Cons2 : O × V → Prop) :
    ¬ Conflates2 obs g Violates Cons2 := by
  intro h
  obtain ⟨e_bad, e_ok, h2, _, hvb, hvo⟩ := h
  have hobs : obs e_bad = obs e_ok := congrArg Prod.fst h2
  have hg : g e_bad = g e_ok := congrArg Prod.snd h2
  exact hvo ((hsep e_bad e_ok ⟨hobs, hg⟩).mp hvb)

/-! ### Repair -- this needs the STRONGER Captures, not Separates -/

/-- The strong condition: `(obs, g)` DECIDE the objective via a predicate `decV`.
    Constructively stronger than `Separates` (it hands you the decision function,
    not merely the guarantee that one exists). -/
def Captures (obs : E → O) (g : E → V) (Violates : E → Prop)
    (decV : O → V → Prop) : Prop :=
  ∀ e, Violates e ↔ decV (obs e) (g e)

/-- The repaired relation: the weak relation, refined by rejecting the decided
    violations. -/
def ConsRepaired (Cons : O → Prop) (decV : O → V → Prop) : O → V → Prop :=
  fun o v => Cons o ∧ ¬ decV o v

/-- THE REPAIR THEOREM. Given `Captures`, the repaired relation removes every
    witness: on the honest observation, acceptance entails the objective is not
    violated. (Requires `Captures`; `Separates` is shown insufficient below.) -/
theorem captures_repairs {obs : E → O} {g : E → V} {Cons : O → Prop}
    {Violates : E → Prop} {decV : O → V → Prop}
    (hcap : Captures obs g Violates decV) :
    ∀ e, ConsRepaired Cons decV (obs e) (g e) → ¬ Violates e := by
  intro e hC hV
  exact hC.2 ((hcap e).mp hV)

/-- `Separates` is NECESSARY but NOT SUFFICIENT for an adequate repair. Concretely:
    a setting where `Separates` holds (the refined observation is even injective)
    yet a relation still admits a witness, because `Separates` does not force the
    relation to reject violations -- only `Captures`-style decision does. This is
    the precise gap between the two halves. -/
theorem separates_not_sufficient :
    ∃ (E' : Type) (obs' : E' → E') (g' : E' → Unit)
      (Viol' : E' → Prop) (Cons2' : E' × Unit → Prop),
      Separates obs' g' Viol'
        ∧ (∃ e, Cons2' (Obs2 obs' g' e) ∧ Viol' e) := by
  refine ⟨Bool, id, fun _ => (), (fun b => b = true), (fun _ => True), ?_, ?_⟩
  · intro e1 e2 h
    have he : e1 = e2 := h.1
    subst he; exact Iff.rfl
  · exact ⟨true, trivial, rfl⟩

/-! ### Axiom audit -/

#print axioms omission_has_witness
#print axioms separates_removes_conflation
#print axioms captures_repairs
#print axioms separates_not_sufficient

end CrossLayer.General
