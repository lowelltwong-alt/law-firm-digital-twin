from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from law_firm_digital_twin.hashio import canonical_json, digest  # noqa: E402
from law_firm_digital_twin.replay_qualification import (  # noqa: E402
    REPLAY_HARNESS_REVISION,
    REPLAY_WORKER_REVISION,
    FreshProcessReplayReceipt,
    qualify_fresh_process_replay,
    run_replay_subprocess,
)


CACHE_SCHEMA = "design_c_e2_state_keyed_cache_v2"
OUTPUT = ROOT / "generated" / "design-c-e2-replay-v1"
CACHE_ROOT = ROOT / "private" / "checks" / "design-c-e2-replay-v1"


def _receipt_id(receipt: FreshProcessReplayReceipt) -> str:
    payload = {
        "harness": receipt.harness_revision,
        "worker": receipt.worker_revision,
        "environment": receipt.environment_hash,
        "input": receipt.input_commitment,
        "semantics": receipt.replay_semantics_hash,
        "runs": receipt.fresh_process_count,
        "process_ids": receipt.unique_process_id_count,
        "verified_launches": receipt.verified_launch_count,
        "launch_commitments": receipt.unique_launch_commitment_count,
        "launch_evidence_chain": receipt.launch_evidence_chain_hash,
    }
    return f"REPLAY-QUAL-{digest(payload)[:18]}"


def _cache_key(
    *,
    environment_hash: str,
    input_commitment: str,
    replay_semantics_hash: str,
    run_count: int,
) -> str:
    return digest(
        {
            "schema": CACHE_SCHEMA,
            "harness": REPLAY_HARNESS_REVISION,
            "worker": REPLAY_WORKER_REVISION,
            "environment": environment_hash,
            "input": input_commitment,
            "semantics": replay_semantics_hash,
            "runs": run_count,
        }
    )


def _validate_cached_receipt(
    receipt: FreshProcessReplayReceipt,
    *,
    environment_hash: str,
    input_commitment: str,
    replay_semantics_hash: str,
    run_count: int,
) -> tuple[str, ...]:
    errors: list[str] = []
    if receipt.receipt_id != _receipt_id(receipt):
        errors.append("E2C-001:receipt_id_invalid")
    if receipt.harness_revision != REPLAY_HARNESS_REVISION:
        errors.append("E2C-002:harness_revision_invalid")
    if receipt.worker_revision != REPLAY_WORKER_REVISION:
        errors.append("E2C-003:worker_revision_invalid")
    if receipt.environment_hash != environment_hash:
        errors.append("E2C-004:environment_stale")
    if receipt.input_commitment != input_commitment:
        errors.append("E2C-005:input_stale")
    if receipt.replay_semantics_hash != replay_semantics_hash:
        errors.append("E2C-006:semantics_stale")
    if receipt.fresh_process_count != run_count:
        errors.append("E2C-007:run_count_invalid")
    if not (0 < receipt.unique_process_id_count <= run_count):
        errors.append("E2C-008:process_telemetry_invalid")
    if (
        receipt.verified_launch_count != run_count
        or receipt.unique_launch_commitment_count != run_count
    ):
        errors.append("E2C-014:fresh_launch_evidence_invalid")
    evidence_ordinals = tuple(item[0] for item in receipt.launch_evidence)
    evidence_commitments = tuple(item[1] for item in receipt.launch_evidence)
    if (
        len(receipt.launch_evidence) != run_count
        or evidence_ordinals != tuple(range(1, run_count + 1))
        or len(set(evidence_commitments)) != run_count
        or any(len(value) != 64 for value in evidence_commitments)
        or digest(receipt.launch_evidence)
        != receipt.launch_evidence_chain_hash
    ):
        errors.append("E2C-015:launch_evidence_chain_invalid")
    if not (
        receipt.all_semantics_identical
        and receipt.environment_lock_validated
        and receipt.stale_environment_rejected
        and receipt.subprocess_isolation_used
    ):
        errors.append("E2C-009:qualification_evidence_incomplete")
    if (
        receipt.changed_input_same_hash_required
        or receipt.canonical_admission
        or receipt.canonical_write
        or receipt.external_effects
        or receipt.contains_case_identifiers
    ):
        errors.append("E2C-010:authority_or_information_boundary_invalid")
    return tuple(errors)


def _write_cache(
    path: Path,
    receipt: FreshProcessReplayReceipt,
    *,
    evidence_basis: str,
    evidence_summary_sha256: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": CACHE_SCHEMA,
        "evidence_basis": evidence_basis,
        "evidence_summary_sha256": evidence_summary_sha256,
        "receipt": asdict(receipt),
    }
    path.write_text(canonical_json(payload) + "\n", encoding="utf-8")


def _load_cache(path: Path) -> FreshProcessReplayReceipt:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != CACHE_SCHEMA:
        raise ValueError("E2C-011:cache_schema_invalid")
    if (
        payload.get("evidence_basis") != "fresh_full_qualification"
        or payload.get("evidence_summary_sha256") != "not_applicable"
    ):
        raise ValueError("E2C-016:cache_evidence_basis_invalid")
    return FreshProcessReplayReceipt(**payload["receipt"])


def load_or_qualify(
    *,
    run_count: int,
) -> tuple[FreshProcessReplayReceipt, str]:
    preflight = run_replay_subprocess(
        ROOT, run_ordinal=0, expected_environment_hash=None
    )
    cache_key = _cache_key(
        environment_hash=preflight.environment_hash,
        input_commitment=preflight.input_commitment,
        replay_semantics_hash=preflight.replay_semantics_hash,
        run_count=run_count,
    )
    cache_path = CACHE_ROOT / f"{cache_key}.json"
    if cache_path.exists():
        receipt = _load_cache(cache_path)
        errors = _validate_cached_receipt(
            receipt,
            environment_hash=preflight.environment_hash,
            input_commitment=preflight.input_commitment,
            replay_semantics_hash=preflight.replay_semantics_hash,
            run_count=run_count,
        )
        if errors:
            raise ValueError(f"state_keyed_replay_cache_invalid:{errors}")
        return receipt, "cache_hit"
    receipt = qualify_fresh_process_replay(ROOT, run_count=run_count)
    _write_cache(
        cache_path,
        receipt,
        evidence_basis="fresh_full_qualification",
        evidence_summary_sha256="not_applicable",
    )
    return receipt, "fresh_qualification"


def build_public_summary(
    receipt: FreshProcessReplayReceipt,
) -> dict[str, object]:
    return {
        "schema": "design_c_e2_replay_public_summary_v1",
        "run_count": receipt.fresh_process_count,
        "unique_process_id_count": receipt.unique_process_id_count,
        "verified_launch_count": receipt.verified_launch_count,
        "unique_launch_commitment_count": (
            receipt.unique_launch_commitment_count
        ),
        "all_semantics_identical": receipt.all_semantics_identical,
        "environment_lock_validated": receipt.environment_lock_validated,
        "stale_environment_rejected": receipt.stale_environment_rejected,
        "subprocess_isolation_used": receipt.subprocess_isolation_used,
        "changed_input_same_hash_required": receipt.changed_input_same_hash_required,
        "canonical_admission": receipt.canonical_admission,
        "canonical_write": receipt.canonical_write,
        "external_effects": receipt.external_effects,
        "contains_case_identifiers": receipt.contains_case_identifiers,
        "contains_replay_or_environment_commitments": False,
        "nonjoinable": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100)
    args = parser.parse_args()
    receipt, disposition = load_or_qualify(run_count=args.runs)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "summary.json").write_text(
        json.dumps(build_public_summary(receipt), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUTPUT / "README.md").write_text(
        "# Design C E-2 Replay Fixture\n\n"
        "Aggregate qualification evidence only. Hashes, seeds, case identifiers, "
        "cassettes, environment commitments, and cache disposition are excluded.\n",
        encoding="utf-8",
    )
    print(disposition)


if __name__ == "__main__":
    main()
