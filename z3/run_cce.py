"""run_cce.py - Phase 1 of "Collective Enforcement Under Collusion".

Run:  python3 run_cce.py

Proves the three core theorems with the real solver (Z3), end to end, then seals
the whole proof as a hash-chained triple of OMEGA records.

  T1  collusion-indifference      : a per-agent cap is defeated by collusion (SAT),
                                     a conserved meter holds regardless (UNSAT).
  T2  the exact boundary          : conserved harm is bounded under collusion
                                     (UNSAT), allocation-dependent harm escapes
                                     the conserved meter (SAT); the dividing line
                                     is "does the harm factor through the
                                     aggregate", certified both ways.
  T3  undetectability-independence: detection is defeated in the de Witt
                                     perfect-security regime (SAT), the conserved
                                     meter is channel-blind (UNSAT to interfere),
                                     and the bound survives the undetectable
                                     channel anyway (UNSAT to breach).

Every SAT/UNSAT below is Z3's verdict, not arithmetic asserted by hand.
"""

import json
import os

import cce_model as M
from cce_model import Params
from cce_record import build_record, seal_record
from omega_seal import verify_seal, verify_chain

# Deterministic timestamp so a rerun reproduces the same content hash.
CREATED_AT = "2026-06-24T00:00:00Z"
HERE = os.path.dirname(os.path.abspath(__file__))
RECORDS = os.path.join(HERE, "records")

# One modeled instance carries all three theorems. N*per_cap = 60 > G = 40, so a
# per-agent cap is defeatable by collusion; h = 15 < G so allocation harm can
# hide under the conserved meter; min_viable = 1 keeps the meter non-vacuous.
P = Params(N=6, per_cap=10, G=40, h=15, victim=2, min_viable=1)

SUBJECT = {
    "domain": "colluding multi-agent commons",
    "instance": P.label(),
    "params": {"N": P.N, "per_cap": P.per_cap, "G": P.G, "h": P.h,
               "victim": P.victim, "min_viable": P.min_viable},
    "collusion_model": ("agents choose the entire draw profile jointly with full "
                        "mutual knowledge through a shared coordination channel - "
                        "the worst case, which every real channel realises"),
}

BOUNDARY = {
    "what_is_proven": (
        "Z3 certifies SAT/UNSAT of the ENCODED constraints. UNSAT of a breach "
        "query certifies that, within the modeled commons, NO jointly-chosen "
        "(fully colluding) profile breaches; SAT exhibits a concrete colluding "
        "witness. It does not certify that real agents obey the model."),
    "collusion_is_worst_case": (
        "collusion is modeled as joint worst-case action: the population selects "
        "the whole profile together to maximise harm. This dominates any "
        "coordination scheme, so a breach UNSAT holds against ALL of them at once. "
        "A real steganographic channel is one realisation of this worst case, not "
        "a stronger adversary."),
    "stego_bridge_honesty": (
        "T3 encodes de Witt's perfect-security CONCLUSION (observational "
        "indistinguishability, KL=0) as an assumption - two executions sharing "
        "one channel observation - not his steganographic construction. The "
        "result is that the conserved meter never reads the channel, so "
        "undetectability is irrelevant to its guarantee."),
    "modeled_vs_general": [
        "single scalar conserved pool; real systems may have several coupled resources",
        "single round of integer draws; real draws are repeated and may be continuous",
        "additive aggregate harm for the conserved case; real harm may be nonlinear in the sum",
        "fixed, known N; real colluding populations can grow or be unknown",
        "allocation harm modeled as one designated victim's draw; real allocation harms are richer",
    ],
    "exact_line": (
        "a conserved meter (sum<=G) bounds a harm under worst-case collusion iff "
        "the harm factors through the aggregate (no equal-aggregate pair differs "
        "in harm). Conserved harm factors (UNSAT to differ) and is bounded; "
        "allocation-dependent harm does not factor (SAT witness pair) and escapes."),
}


def _line(tag, res):
    v = res.get("verdict", "")
    print(f"   [{v:^5}] {tag}: {res['claim']}")


def prove_t1():
    print("\n" + "=" * 78)
    print("T1  COLLUSION-INDIFFERENCE")
    print("=" * 78)
    per_agent = M.t1_per_agent_defeated(P)
    meter = M.t1_conserved_meter_holds(P)
    usable = M.t1_meter_not_vacuous(P)

    _line("per-agent cap", per_agent)
    if per_agent["witness"]:
        w = per_agent["witness"]
        print(f"           witness: profile={w['profile']} sum={w['sum']} > G={P.G} "
              f"(each <= per_cap={P.per_cap})")
    _line("conserved meter", meter)
    print(f"           {meter['indifference']}")
    _line("not vacuous", usable)
    if usable["witness"]:
        print(f"           witness: profile={usable['witness']['profile']} "
              f"sum={usable['witness']['sum']} == G (all >= min_viable)")

    per_agent_fails = per_agent["breach_reachable"]
    meter_holds = not meter["breach_reachable"]
    outcome = {
        "gate_result": "COMMITTED" if meter_holds else "BREACHED",
        "per_agent_cap_defeated_by_collusion": per_agent_fails,
        "conserved_meter_holds_under_collusion": meter_holds,
        "meter_non_vacuous": usable["functional"],
        "headline": ("per-agent (local) rules fail under collusion; the conserved "
                     "(aggregate) meter holds regardless, because it constrains "
                     "the sum the colluders jointly produce"),
    }
    claims = {"per_agent_defeated": per_agent,
              "conserved_meter_holds": meter,
              "meter_not_vacuous": usable}
    assert per_agent_fails and meter_holds and usable["functional"], "T1 expectations"
    return claims, outcome


def prove_t2():
    print("\n" + "=" * 78)
    print("T2  THE EXACT BOUNDARY  (conserved vs allocation-dependent)")
    print("=" * 78)
    conserved = M.t2_conserved_bounded(P)
    allocation = M.t2_allocation_escapes(P)
    fac_cons = M.factors_through_aggregate(P, "conserved")
    fac_alloc = M.factors_through_aggregate(P, "allocation")
    closure = M.t2_allocation_meter_closes(P)

    _line("conserved harm", conserved)
    print(f"           bound delivered: {conserved['bound_delivered']}")
    _line("allocation harm", allocation)
    if allocation["witness"]:
        w = allocation["witness"]
        print(f"           witness: profile={w['profile']} sum={w['sum']}<=G={P.G} "
              f"BUT d_victim={w['d_victim']} > h={P.h}")
    _line("factors? conserved", fac_cons)
    _line("factors? allocation", fac_alloc)
    if fac_alloc["witness"]:
        w = fac_alloc["witness"]
        print(f"           equal-aggregate pair: {w['profile_1']} (harm {w['harm_1']}) "
              f"vs {w['profile_2']} (harm {w['harm_2']}), both sum {w['aggregate']}")
    _line("closure", closure)

    conserved_safe = not conserved["breach_reachable"]
    allocation_escapes = allocation["breach_reachable"]
    line_exact = (fac_cons["factors_through_aggregate"] and
                  not fac_alloc["factors_through_aggregate"])
    outcome = {
        "gate_result": "BOUNDED" if conserved_safe else "BREACHED",
        "conserved_harm_bounded_under_collusion": conserved_safe,
        "allocation_harm_escapes_conserved_meter": allocation_escapes,
        "boundary_is_factor_through_aggregate": line_exact,
        "allocation_needs": closure["needs"],
        "allocation_closed_by_allocation_meter": not closure["breach_reachable"],
        "headline": ("the conserved meter bounds exactly the harms that factor "
                     "through the aggregate; allocation-dependent harm provably "
                     "does not factor, so it escapes and needs an "
                     "allocation-level constraint"),
    }
    claims = {"conserved_bounded": conserved,
              "allocation_escapes": allocation,
              "factors_conserved": fac_cons,
              "factors_allocation": fac_alloc,
              "allocation_meter_closes": closure}
    assert conserved_safe and allocation_escapes and line_exact, "T2 expectations"
    assert not closure["breach_reachable"], "allocation meter must close it"
    return claims, outcome


def prove_t3():
    print("\n" + "=" * 78)
    print("T3  UNDETECTABILITY-INDEPENDENCE  (bridge to de Witt secret collusion)")
    print("=" * 78)
    detect = M.t3_detection_defeated(P)
    blind = M.t3_meter_channel_blind(P)
    survives = M.t3_bound_survives_undetected(P)

    _line("detection defeated", detect)
    if detect["witness"]:
        w = detect["witness"]
        print(f"           innocent={w['innocent_profile']} vs "
              f"colluding={w['colluding_profile']}, SAME obs={w['shared_observation']}")
    _line("meter channel-blind", blind)
    print(f"           {blind['consequence']}")
    _line("bound survives", survives)
    print(f"           {survives['bridge']}")

    detection_unsound = detect["indistinguishable"]
    meter_blind = blind["channel_blind"]
    bound_holds = not survives["breach_reachable"]
    outcome = {
        "gate_result": "COMMITTED" if (meter_blind and bound_holds) else "BREACHED",
        "detection_defeated_in_perfect_security_regime": detection_unsound,
        "conserved_meter_is_channel_blind": meter_blind,
        "bound_survives_undetectable_channel": bound_holds,
        "headline": ("the meter's guarantee does not depend on observing the "
                     "collusion channel; even an information-theoretically "
                     "undetectable channel cannot defeat a bound on the aggregate"),
    }
    claims = {"detection_defeated": detect,
              "meter_channel_blind": blind,
              "bound_survives": survives}
    assert detection_unsound and meter_blind and bound_holds, "T3 expectations"
    return claims, outcome


def main():
    os.makedirs(RECORDS, exist_ok=True)
    print("=" * 78)
    print("COLLECTIVE ENFORCEMENT UNDER COLLUSION  -  Phase 1 (machine-checked core)")
    print("instance:", P.label())
    print("=" * 78)

    t1_claims, t1_out = prove_t1()
    t2_claims, t2_out = prove_t2()
    t3_claims, t3_out = prove_t3()

    rec1 = build_record(
        record_id="collective-collusion-0001", created_at=CREATED_AT,
        theorem_id="T1", title="collusion-indifference",
        subject=SUBJECT, claims=t1_claims, outcome=t1_out, boundary=BOUNDARY,
        previous_hash=None)
    s1 = seal_record(rec1)

    rec2 = build_record(
        record_id="collective-collusion-0002", created_at=CREATED_AT,
        theorem_id="T2", title="exact boundary: conserved vs allocation-dependent",
        subject=SUBJECT, claims=t2_claims, outcome=t2_out, boundary=BOUNDARY,
        previous_hash=s1["content_hash"])
    s2 = seal_record(rec2)

    rec3 = build_record(
        record_id="collective-collusion-0003", created_at=CREATED_AT,
        theorem_id="T3", title="undetectability-independence",
        subject=SUBJECT, claims=t3_claims, outcome=t3_out, boundary=BOUNDARY,
        previous_hash=s2["content_hash"])
    s3 = seal_record(rec3)

    chain = verify_chain([s1, s2, s3])

    print("\n" + "=" * 78)
    print("SEALED OMEGA RECORDS (hash-chained triple)")
    print("=" * 78)
    for s in (s1, s2, s3):
        print(f"  {s['record_id']}  [{s['theorem_id']}] gate={s['outcome']['gate_result']:<10} "
              f"hash={s['content_hash'][:16]}  verify={verify_seal(s)}")
    print(f"  chain intact: {chain['chain_intact']}   head={chain['head_hash'][:16]}")

    # Tamper test: flip a sealed verdict and show the seal rejects it.
    tampered = json.loads(json.dumps(s2))
    tampered["outcome"]["allocation_harm_escapes_conserved_meter"] = False
    print(f"  tamper test: flip a sealed verdict -> verify = {verify_seal(tampered)} "
          f"(expected False)")

    for s in (s1, s2, s3):
        out = os.path.join(RECORDS, f"{s['record_id']}.json")
        with open(out, "w") as f:
            json.dump(s, f, indent=2, sort_keys=True)
        print(f"  sealed -> {out}")

    print("\nAll three theorems proven, sealed, chained, tamper-checked.")


if __name__ == "__main__":
    main()
