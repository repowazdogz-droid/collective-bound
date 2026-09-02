"""omega_seal - the ONE canonical provenance spine for the verification/synthesis
tower.

Every engine used to carry its own copied sealer (omega_record.py and renamed
variants: frontier_record.py, hyp_omega.py, meta_record.py, redteam_record.py,
fss_record.py, ...). Those copies shared one generic importable name and sat on
sys.path together, so a bare `import omega_record` from one engine could resolve
to another engine's copy. The seal algorithm was identical in every copy, so a
mis-resolved import sealed correctly while silently carrying the WRONG
record_type: a provenance bug that no seal check could catch.

This package removes the copies. The seal/chain/tamper-check logic lives here once,
installed as a real top-level package (`omega_seal`), imported by name, never by
sys.path manipulation. Each engine still gets its own typed record (it sets
record_type and builds its own body), but the sealing comes from this single
source of truth.

Canonical algorithm (preserved byte-for-byte from the original copies, so every
record sealed before consolidation re-seals to the identical hash):

  - canonical_stringify: sorted keys, None values dropped from objects,
    JS-compatible number formatting (integers print without a trailing .0).
    A faithful port of the OMEGA omega-record.ts canonicalStringify.
  - sha256 over the canonical string.
  - seal: attach content_hash = sha256(record body), where the body is the record
    WITHOUT its content_hash field.
  - verify: recompute sha256 over the body (content_hash excluded) and compare.
  - verify_chain: each record verifies its own seal AND previous_hash links the
    sequence, so a run is tamper-evident as a chain.

Compatibility aliases are provided because the copies exposed the same algorithm
under different names: seal_omega == seal, verify_omega == verify,
verify_seal == verify. New code should use seal / verify / verify_chain.
"""

import hashlib
import json

__all__ = [
    "OMEGA_SCHEMA_VERSION", "OMEGA_CONTRACTS_VERSION",
    "canonical_stringify", "sha256",
    "seal", "verify", "verify_chain",
    "seal_omega", "verify_omega", "verify_seal",
    "base_record",
]

OMEGA_SCHEMA_VERSION = "omega/1.0"
OMEGA_CONTRACTS_VERSION = "0.2.2"


def canonical_stringify(value) -> str:
    """Sorted keys, None dropped from objects, JS-compatible number formatting
    (integers print without a trailing .0). Faithful to omega-record.ts.

    The bool check MUST precede the int check: in Python bool is a subclass of
    int, and the two render differently (true/false vs 1/0). This ordering is
    load-bearing for hash reproduction; do not reorder."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonical_stringify(v) for v in value) + "]"
    if isinstance(value, dict):
        keys = [k for k in sorted(value.keys()) if value[k] is not None]
        return "{" + ",".join(
            json.dumps(k, ensure_ascii=False) + ":" + canonical_stringify(value[k])
            for k in keys) + "}"
    raise TypeError(f"cannot canonicalise {type(value)}")


def sha256(value) -> str:
    s = value if isinstance(value, str) else canonical_stringify(value)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def seal(record) -> dict:
    """Attach content_hash over the canonical record - the tamper-evident seal
    that also chains to previous_hash. The input record must not already contain
    a content_hash (it is computed over the body as given)."""
    sealed = dict(record)
    sealed["content_hash"] = sha256(record)
    return sealed


def verify(sealed) -> bool:
    """Recompute the seal over the body (content_hash excluded) and compare."""
    claimed = sealed.get("content_hash")
    if not claimed:
        return False
    body = {k: v for k, v in sealed.items() if k != "content_hash"}
    return sha256(body) == claimed


def verify_chain(sealed_records) -> dict:
    """Verify each record's own seal AND that previous_hash links the chain."""
    ok = True
    prev = None
    for r in sealed_records:
        if not verify(r):
            ok = False
        if r.get("previous_hash") != prev:
            ok = False
        prev = r.get("content_hash")
    return {"chain_intact": ok, "length": len(sealed_records),
            "head_hash": sealed_records[-1]["content_hash"] if sealed_records else None}


def base_record(record_type, *, record_id, created_at, previous_hash=None,
                schema_version=OMEGA_SCHEMA_VERSION,
                contracts_version=OMEGA_CONTRACTS_VERSION, **fields):
    """Optional sugar for declaring a per-engine typed record from the shared
    spine. Builds the common envelope (record_type + schema/contracts versions +
    id + created_at + previous_hash) and merges engine-specific **fields. Key
    order does not affect the seal (canonical_stringify sorts keys), so engines
    may also build the dict themselves and call seal() directly."""
    rec = {
        "record_type": record_type,
        "schema_version": schema_version,
        "contracts_version": contracts_version,
        "record_id": record_id,
        "created_at": created_at,
    }
    rec.update(fields)
    rec["previous_hash"] = previous_hash
    return rec


# --- compatibility aliases (the copies exposed one algorithm under many names) --
seal_omega = seal
verify_omega = verify
verify_seal = verify
