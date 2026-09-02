"""cce_record.py - wire a "Collective Enforcement Under Collusion" theorem onto
the OMEGA governed-record format, using the ONE canonical omega_seal provenance
spine (imported by name, never copied, never by sys.path).

Unique module name (cce_record, not omega_record) so importing this never
collides with another engine's record module on sys.path.

Each theorem becomes one typed, sealed record. The verdict travels WITH its
evidence (the SAT/UNSAT queries and their witnesses) under a single content
hash, and the three records are hash-chained so the whole proof is
tamper-evident as a sequence.
"""

from typing import Any, Dict, List, Optional

from omega_seal import base_record, seal, verify_seal, verify_chain

RECORD_TYPE = "CollectiveCollusionRecord"
SCHEMA_VERSION = "omega/1.0"
CONTRACTS_VERSION = "0.2.2"


def build_record(*, record_id: str, created_at: str, theorem_id: str,
                 title: str, subject: Dict[str, Any], claims: Dict[str, Any],
                 outcome: Dict[str, Any], boundary: Dict[str, Any],
                 previous_hash: Optional[str] = None) -> dict:
    """Build one theorem record. `claims` holds the named SAT/UNSAT query
    results (with witnesses); `outcome` holds the theorem-level verdict and the
    OMEGA gate result."""
    return base_record(
        RECORD_TYPE,
        record_id=record_id,
        created_at=created_at,
        previous_hash=previous_hash,
        schema_version=SCHEMA_VERSION,
        contracts_version=CONTRACTS_VERSION,
        theorem_id=theorem_id,
        title=title,
        subject=subject,
        claims=claims,
        outcome=outcome,
        boundary=boundary,
    )


EXPERIMENT_RECORD_TYPE = "CollectiveCollusionExperimentRecord"


def build_experiment_record(*, record_id: str, created_at: str, stage: str,
                            title: str, subject: Dict[str, Any],
                            scenarios: List[Dict[str, Any]],
                            cross_check: Dict[str, Any], outcome: Dict[str, Any],
                            boundary: Dict[str, Any],
                            previous_hash: Optional[str] = None) -> dict:
    """Build one Phase-2 experiment record. `scenarios` holds the realised
    controller episodes; `cross_check` records that each empirical breach verdict
    matches the corresponding Phase-1 Z3 SAT/UNSAT."""
    return base_record(
        EXPERIMENT_RECORD_TYPE,
        record_id=record_id,
        created_at=created_at,
        previous_hash=previous_hash,
        schema_version=SCHEMA_VERSION,
        contracts_version=CONTRACTS_VERSION,
        stage=stage,
        title=title,
        subject=subject,
        scenarios=scenarios,
        cross_check=cross_check,
        outcome=outcome,
        boundary=boundary,
    )


def seal_record(record: dict) -> dict:
    sealed = seal(record)
    assert verify_seal(sealed), "seal failed to verify immediately after sealing"
    return sealed
