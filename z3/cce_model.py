"""cce_model.py - the colluding-population commons, its shared coordination
channel, and the Z3 queries behind the three theorems of
"Collective Enforcement Under Collusion".

Unique module prefix (cce_*) on purpose: this directory imports nothing generic
(model / engine / run), so it can never be shadowed by a sibling engine's
same-named module on sys.path (see the cross-engine-import-hygiene rule that
produced the omega_seal consolidation).

----------------------------------------------------------------------------
THE SETTING
----------------------------------------------------------------------------
N agents share a resource. In one round each agent i takes an integer draw
d_i >= 0. (Multi-round reduces to this: the aggregate over (agent, step) is
still ONE conserved scalar; we keep a single round so the collusion story is
crisp and the witnesses are readable.)

----------------------------------------------------------------------------
COLLUSION, MODELED AS JOINT WORST CASE  (the strongest collusion)
----------------------------------------------------------------------------
The agents collude through a shared coordination channel: every agent observes
a broadcast plan before acting and may condition its draw on it, with full
mutual knowledge. The STRONGEST possible collusion is for the population to
choose the entire action profile jointly to maximise harm. In the solver this
is exactly an existential over the whole draw vector: Z3 selects every d_i
together. No coordination scheme - secret, steganographic, or otherwise - can
beat the unconstrained joint optimum, so this existential IS the worst case.
A real stego channel (de Witt et al., secret collusion among generative AI
agents) is one concrete realisation of this worst case, not a stronger one.

Consequence we exploit throughout: a breach query over the FREE joint profile
is universally quantified over all coordination strategies at once. UNSAT of
such a query therefore means "no coordination plan whatsoever breaches".

----------------------------------------------------------------------------
TWO GOVERNORS
----------------------------------------------------------------------------
  - per-agent cap   (LOCAL rule)      :  for all i.  d_i <= per_cap
  - conserved meter (AGGREGATE rule)  :  sum_i d_i <= G

----------------------------------------------------------------------------
TWO HARM KINDS  (the boundary of T2)
----------------------------------------------------------------------------
  - conserved            harm = sum_i d_i     (a function of the aggregate)
  - allocation-dependent harm = d_victim      (depends on WHICH agent acts)

Every question below is answered by the real solver. UNSAT of a breach query
is Z3's proof that no jointly-chosen (fully colluding) profile breaches; SAT is
a concrete, individually-compliant colluding witness.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import z3


# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Params:
    """One modeled colluding-commons instance."""
    N: int                # number of (colluding) agents
    per_cap: int          # per-agent cap used in the per-agent-only contrast
    G: int                # conserved threshold; the meter enforces sum <= G
    h: int                # allocation danger threshold (d_victim must stay <= h)
    victim: int           # designated agent for allocation-dependent harm
    min_viable: int = 1   # smallest draw at which an agent is still functional

    def label(self) -> str:
        return (f"N={self.N} per_cap={self.per_cap} G={self.G} "
                f"h={self.h} victim=a{self.victim} min_viable={self.min_viable}")


# ----------------------------------------------------------------------------
# small helpers
def _draws(N: int, tag: str = "d") -> List[z3.ArithRef]:
    return [z3.Int(f"{tag}_{i}") for i in range(N)]


def _profile(model, d: List[z3.ArithRef]) -> List[int]:
    return [model.eval(x, model_completion=True).as_long() for x in d]


def _nonzero(profile: List[int]) -> List[List[int]]:
    return [[i, v] for i, v in enumerate(profile) if v != 0]


# ============================================================================
# THEOREM 1 - collusion-indifference
# ============================================================================
def t1_per_agent_defeated(p: Params) -> Dict[str, Any]:
    """T1, contrast half: a per-agent cap alone (NO conserved meter) is defeated
    by the colluding population.

    Each agent obeys per_cap; the colluders jointly choose every draw. Is there
    a compliant profile with sum > G? SAT means the per-agent rule fails under
    collusion. The reported witness is the maximal coordinated profile (each at
    per_cap), which Z3 confirms is individually-compliant yet breaches - the
    plainest coordination there is, and fully deterministic.
    """
    s = z3.Solver()
    d = _draws(p.N)
    for x in d:
        s.add(x >= 0, x <= p.per_cap)
    s.add(z3.Sum(d) > p.G)
    reachable = s.check() == z3.sat

    witness = None
    if reachable:
        chk = z3.Solver()
        dm = _draws(p.N, "m")
        for x in dm:
            chk.add(x == p.per_cap)        # the maximal coordinated profile
        chk.add(z3.Sum(dm) > p.G)
        assert chk.check() == z3.sat, "maximal profile must witness the breach"
        prof = _profile(chk.model(), dm)
        witness = {
            "profile": prof,
            "nonzero_draws": _nonzero(prof),
            "sum": sum(prof),
            "G": p.G,
            "each_within_per_cap": all(v <= p.per_cap for v in prof),
            "note": ("every agent obeys per_cap; coordinated, the population's "
                     "aggregate exceeds G - the per-agent rule cannot see the sum"),
        }
    return {
        "claim": "per-agent cap defeated under collusion",
        "query": "exists individually-compliant profile (d_i<=per_cap) with sum>G, no meter",
        "breach_reachable": reachable,
        "verdict": "SAT" if reachable else "UNSAT",
        "structural": {"N_times_per_cap": p.N * p.per_cap, "G": p.G,
                       "per_agent_fails_when": "N*per_cap > G"},
        "witness": witness,
    }


def t1_conserved_meter_holds(p: Params) -> Dict[str, Any]:
    """T1, headline half: the conserved meter holds REGARDLESS of collusion.

    The meter enforces sum <= G. Agents are individually UNBOUNDED (no per_cap)
    and fully colluding (joint free choice over the entire profile = quantified
    over every coordination plan at once). Attempt a breach: sum <= G AND
    sum > G. UNSAT is Z3's proof that NO coordination plan breaches - the
    guarantee is indifferent to whatever the agents secretly communicate,
    because it constrains the aggregate they jointly produce.
    """
    s = z3.Solver()
    d = _draws(p.N)
    for x in d:
        s.add(x >= 0)                  # individually unbounded
    S = z3.Sum(d)
    s.add(S <= p.G)                    # the conserved meter
    s.add(S > p.G)                     # attempt to breach it
    reachable = s.check() == z3.sat
    return {
        "claim": "conserved meter holds under worst-case collusion",
        "query": "exists coordinated profile with sum<=G and sum>G (meter on, agents unbounded)",
        "breach_reachable": reachable,
        "verdict": "SAT" if reachable else "UNSAT",
        "indifference": ("the breach query is universally quantified over all "
                         "coordination plans; UNSAT => the verdict is the same "
                         "for every channel content"),
    }


def t1_meter_not_vacuous(p: Params) -> Dict[str, Any]:
    """The conserved meter is not vacuous: the population can still do useful
    work. Every agent draws at least min_viable and the aggregate reaches the
    cap G. SAT with a witness reaching sum == G."""
    s = z3.Solver()
    d = _draws(p.N)
    for x in d:
        s.add(x >= p.min_viable)
    S = z3.Sum(d)
    s.add(S == p.G)                    # use the full conserved budget
    functional = s.check() == z3.sat
    witness = None
    if functional:
        prof = _profile(s.model(), d)
        witness = {"profile": prof, "sum": sum(prof),
                   "all_at_least_min_viable": all(v >= p.min_viable for v in prof)}
    return {
        "claim": "conserved meter leaves agents functional",
        "query": "exists profile with every d_i>=min_viable and sum==G",
        "functional": functional,
        "verdict": "SAT" if functional else "UNSAT",
        "witness": witness,
    }


# ============================================================================
# THEOREM 2 - the exact boundary (conserved vs allocation-dependent)
# ============================================================================
def t2_conserved_bounded(p: Params) -> Dict[str, Any]:
    """Conserved side of the boundary: a conserved harm (= the aggregate) is
    bounded by the conserved meter under collusion. This is the same UNSAT proof
    as T1's headline, restated as the harm-bound it delivers: harm = sum <= G."""
    res = t1_conserved_meter_holds(p)
    return {
        "claim": "conserved harm is bounded by the conserved meter under collusion",
        "query": "exists coordinated profile with harm=sum<=G and harm>G",
        "breach_reachable": res["breach_reachable"],
        "verdict": res["verdict"],
        "harm_kind": "conserved (harm = sum_i d_i)",
        "bound_delivered": f"harm <= G = {p.G}",
    }


def t2_allocation_escapes(p: Params) -> Dict[str, Any]:
    """Allocation side of the boundary: an allocation-dependent harm ESCAPES the
    conserved meter under collusion.

    Harm = d_victim, dangerous above h (with h < G). The colluders obey the
    conserved meter (sum <= G) yet route the resource to the victim so that
    d_victim > h. We take the MINIMAL-aggregate such profile (Optimize), which
    is unique: d_victim = h+1, every other agent 0 (so sum = h+1 <= G). SAT is a
    concrete colluding witness that satisfies the meter and still does the harm.
    """
    opt = z3.Optimize()
    d = _draws(p.N)
    for x in d:
        opt.add(x >= 0)
    S = z3.Sum(d)
    opt.add(S <= p.G)                  # conserved meter satisfied
    opt.add(d[p.victim] > p.h)         # allocation harm triggered
    opt.minimize(S)                    # unique minimal witness: victim=h+1, rest 0
    reachable = opt.check() == z3.sat
    witness = None
    if reachable:
        prof = _profile(opt.model(), d)
        witness = {
            "profile": prof,
            "nonzero_draws": _nonzero(prof),
            "sum": sum(prof),
            "meter_satisfied": sum(prof) <= p.G,
            "victim": p.victim,
            "d_victim": prof[p.victim],
            "h": p.h,
            "note": ("aggregate obeys the conserved meter (sum<=G) yet the "
                     "victim's draw exceeds h: the meter never constrained WHO "
                     "drew, only HOW MUCH in total"),
        }
    return {
        "claim": "allocation-dependent harm escapes the conserved meter under collusion",
        "query": "exists coordinated profile with sum<=G and d_victim>h",
        "breach_reachable": reachable,
        "verdict": "SAT" if reachable else "UNSAT",
        "harm_kind": "allocation-dependent (harm = d_victim)",
        "witness": witness,
    }


def factors_through_aggregate(p: Params, harm_kind: str) -> Dict[str, Any]:
    """The EXACT-LINE certificate. A conserved meter bounds a harm under
    worst-case collusion iff the harm factors through the aggregate, i.e. iff
    there is NO pair of profiles with equal aggregate but different harm.

    Query: do two profiles exist with equal sum but different harm?
      - UNSAT  => harm is determined by the aggregate (it FACTORS through it);
                  the conserved meter controls it.
      - SAT    => harm is NOT a function of the aggregate; two equal-aggregate
                  profiles differ in harm, so capping the aggregate cannot bound
                  it. The witness pair is the exact reason the meter is blind.

    For the allocation harm we report a constructed canonical witness pair
    (victim carries the mass vs a non-victim carries it, same total) so the
    certificate is deterministic; Z3 confirms it.
    """
    a = _draws(p.N, "a")
    b = _draws(p.N, "b")
    s = z3.Solver()
    for x in a + b:
        s.add(x >= 0)
    s.add(z3.Sum(a) == z3.Sum(b))      # equal aggregate
    if harm_kind == "conserved":
        ha, hb = z3.Sum(a), z3.Sum(b)
    elif harm_kind == "allocation":
        ha, hb = a[p.victim], b[p.victim]
    else:
        raise ValueError(harm_kind)
    s.add(ha != hb)                    # different harm at equal aggregate?
    differs = s.check() == z3.sat

    witness = None
    if differs and harm_kind == "allocation":
        # canonical deterministic pair, both sum to 1:
        #   profile_1: all mass on the victim   -> harm = 1
        #   profile_2: all mass on a non-victim -> harm = 0
        other = 0 if p.victim != 0 else 1
        p1 = [0] * p.N; p1[p.victim] = 1
        p2 = [0] * p.N; p2[other] = 1
        chk = z3.Solver()
        ca, cb = _draws(p.N, "ca"), _draws(p.N, "cb")
        for i in range(p.N):
            chk.add(ca[i] == p1[i], cb[i] == p2[i])
        chk.add(z3.Sum(ca) == z3.Sum(cb))
        chk.add(ca[p.victim] != cb[p.victim])
        assert chk.check() == z3.sat, "canonical witness pair must hold"
        witness = {
            "profile_1": p1, "harm_1": p1[p.victim],
            "profile_2": p2, "harm_2": p2[p.victim],
            "equal_aggregate": sum(p1) == sum(p2), "aggregate": sum(p1),
            "note": ("same aggregate, different allocation harm: the harm "
                     "carries information the aggregate does not"),
        }
    return {
        "claim": (f"{harm_kind} harm "
                  + ("factors through the aggregate (meter can bound it)"
                     if not differs else
                     "does NOT factor through the aggregate (meter is blind to it)")),
        "harm_kind": harm_kind,
        "query": "exists two profiles with equal aggregate but different harm",
        "differs_at_equal_aggregate": differs,
        "verdict": "SAT" if differs else "UNSAT",
        "factors_through_aggregate": not differs,
        "conserved_meter_can_bound_it": not differs,
        "witness": witness,
    }


def t2_allocation_meter_closes(p: Params) -> Dict[str, Any]:
    """The closure: what the conserved meter cannot do, an allocation-aware meter
    can. Add a per-recipient cap (d_i <= h for all i). Now can the colluders
    push d_victim > h? UNSAT. This is the 'needs more' side of the boundary:
    allocation-dependent harm needs an allocation-level constraint."""
    s = z3.Solver()
    d = _draws(p.N)
    for x in d:
        s.add(x >= 0, x <= p.h)        # allocation-level meter (per-recipient cap)
    s.add(d[p.victim] > p.h)
    reachable = s.check() == z3.sat
    return {
        "claim": "an allocation-aware meter closes what the conserved meter cannot",
        "query": "under a per-recipient cap (d_i<=h), exists profile with d_victim>h",
        "breach_reachable": reachable,
        "verdict": "SAT" if reachable else "UNSAT",
        "needs": "an allocation-level constraint (per-recipient cap), not just sum<=G",
    }


# ============================================================================
# THEOREM 3 - undetectability-independence  (the bridge to de Witt)
# ============================================================================
def t3_detection_defeated(p: Params) -> Dict[str, Any]:
    """The de Witt perfect-security (zero-KL) regime, modeled as its CONCLUSION:
    a colluding execution and an innocent execution share an IDENTICAL channel
    observation. Any monitor that reads only the observation returns the same
    verdict on both and therefore cannot flag the colluder.

    We do NOT re-derive the steganographic construction. We encode its
    guarantee directly: the colluding observation equals an innocent cover
    (the observation carries zero information about the collusion). We fix the
    cover to a constant so the witness is deterministic.

      innocent behaviour : every agent at min_viable
      colluding behaviour: every agent at per_cap (a coordinated maximal draw)
      observation        : identical on both sides (perfect security)
    """
    K = 2
    s = z3.Solver()
    inn = _draws(p.N, "inn")
    col = _draws(p.N, "col")
    obs_i = [z3.Int(f"obs_i_{j}") for j in range(K)]
    obs_c = [z3.Int(f"obs_c_{j}") for j in range(K)]
    for x in inn:
        s.add(x == p.min_viable)
    for x in col:
        s.add(x == p.per_cap)
    s.add(z3.Or([col[i] != inn[i] for i in range(p.N)]))   # behaviours differ
    for j in range(K):
        s.add(obs_i[j] == 0)                               # fixed innocent cover
        s.add(obs_c[j] == obs_i[j])                        # perfect security: same obs
    indistinguishable = s.check() == z3.sat
    witness = None
    if indistinguishable:
        m = s.model()
        witness = {
            "innocent_profile": _profile(m, inn),
            "colluding_profile": _profile(m, col),
            "shared_observation": [m.eval(o, model_completion=True).as_long() for o in obs_i],
            "behaviours_differ": True,
            "note": ("two genuinely different behaviours, one observation: a "
                     "monitor reading the channel cannot tell them apart"),
        }
    return {
        "claim": "detection is defeated in the perfect-security (zero-KL) regime",
        "query": "exists colluding & innocent executions with identical channel observation",
        "indistinguishable": indistinguishable,
        "verdict": "SAT" if indistinguishable else "UNSAT",
        "monitor_can_distinguish": not indistinguishable,
        "encoding_honesty": ("we encode de Witt's CONCLUSION (observational "
                             "indistinguishability / KL=0) as an assumption, not "
                             "his steganographic construction"),
        "witness": witness,
    }


def t3_meter_channel_blind(p: Params) -> Dict[str, Any]:
    """The conserved meter's verdict is a function of the AGGREGATE ALONE. Two
    executions that agree on the aggregate get the same verdict, regardless of
    how their per-agent allocation or channel content differs.

    Query for a violation: equal aggregate, different meter verdict. UNSAT
    proves the verdict is reallocation-invariant and channel-blind - the meter
    never reads the channel, so an undetectable channel cannot affect it.
    """
    a = _draws(p.N, "a")
    b = _draws(p.N, "b")
    s = z3.Solver()
    for x in a + b:
        s.add(x >= 0)
    s.add(z3.Sum(a) == z3.Sum(b))                  # equal aggregate
    va = z3.Sum(a) <= p.G                           # meter verdict reads aggregate only
    vb = z3.Sum(b) <= p.G
    s.add(va != vb)                                 # try to make the verdict differ
    violation = s.check() == z3.sat
    return {
        "claim": "the conserved meter is channel-blind (non-interference)",
        "query": "exists equal-aggregate executions with differing conserved-meter verdict",
        "violation_reachable": violation,
        "verdict": "SAT" if violation else "UNSAT",
        "channel_blind": not violation,
        "consequence": ("the verdict depends only on the aggregate; channel "
                        "content - detectable or not - cannot change it"),
    }


def t3_bound_survives_undetected(p: Params) -> Dict[str, Any]:
    """The payload: on a perfectly-coordinated, perfectly-hidden colluding
    execution, with the conserved meter active, can the population breach? The
    colluders use the invisible channel to choose any joint profile (free,
    individually unbounded); the meter admits only sum <= G. Breach sum > G is
    UNSAT. Perfect coordination plus perfect invisibility still cannot defeat a
    bound that only observes the aggregate."""
    s = z3.Solver()
    d = _draws(p.N)
    for x in d:
        s.add(x >= 0)
    S = z3.Sum(d)
    s.add(S <= p.G)
    s.add(S > p.G)
    reachable = s.check() == z3.sat
    return {
        "claim": "the conserved bound survives an information-theoretically-undetectable channel",
        "query": "exists invisibly-coordinated profile with sum<=G and sum>G",
        "breach_reachable": reachable,
        "verdict": "SAT" if reachable else "UNSAT",
        "bridge": ("undetectability is orthogonal to the guarantee: the meter "
                   "never tried to observe the channel, only the aggregate"),
    }
