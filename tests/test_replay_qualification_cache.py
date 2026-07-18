from __future__ import annotations

from dataclasses import asdict, replace
import importlib.util
import json
from pathlib import Path

from law_firm_digital_twin.replay_qualification import FreshProcessReplayReceipt


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_design_c_e2_replay_qualification_cached.py"
SPEC = importlib.util.spec_from_file_location("replay_cache_script", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _receipt() -> FreshProcessReplayReceipt:
    launch_evidence = tuple(
        (ordinal, f"{ordinal:064x}") for ordinal in range(1, 101)
    )
    receipt = FreshProcessReplayReceipt(
        receipt_id="PENDING",
        harness_revision=MODULE.REPLAY_HARNESS_REVISION,
        worker_revision=MODULE.REPLAY_WORKER_REVISION,
        environment_hash="1" * 64,
        input_commitment="2" * 64,
        replay_semantics_hash="3" * 64,
        fresh_process_count=100,
        unique_process_id_count=100,
        verified_launch_count=100,
        unique_launch_commitment_count=100,
        launch_evidence=launch_evidence,
        launch_evidence_chain_hash=MODULE.digest(launch_evidence),
        all_semantics_identical=True,
        environment_lock_validated=True,
        stale_environment_rejected=True,
        subprocess_isolation_used=True,
        changed_input_same_hash_required=False,
        canonical_admission=False,
        canonical_write=False,
        external_effects=False,
        contains_case_identifiers=False,
    )
    return replace(receipt, receipt_id=MODULE._receipt_id(receipt))


def test_state_keyed_cached_receipt_validates_exact_bindings() -> None:
    receipt = _receipt()
    assert MODULE._validate_cached_receipt(
        receipt,
        environment_hash=receipt.environment_hash,
        input_commitment=receipt.input_commitment,
        replay_semantics_hash=receipt.replay_semantics_hash,
        run_count=receipt.fresh_process_count,
    ) == ()


def test_cache_rejects_stale_tampered_or_authoritative_receipt() -> None:
    receipt = _receipt()
    attacked = replace(
        receipt,
        environment_hash="4" * 64,
        canonical_admission=True,
        verified_launch_count=99,
    )
    errors = MODULE._validate_cached_receipt(
        attacked,
        environment_hash="1" * 64,
        input_commitment=receipt.input_commitment,
        replay_semantics_hash=receipt.replay_semantics_hash,
        run_count=receipt.fresh_process_count,
    )
    assert "E2C-001:receipt_id_invalid" in errors
    assert "E2C-004:environment_stale" in errors
    assert "E2C-010:authority_or_information_boundary_invalid" in errors
    assert "E2C-014:fresh_launch_evidence_invalid" in errors


def test_cache_loader_rejects_public_summary_adoption_basis(
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "forged-cache.json"
    cache_path.write_text(
        json.dumps(
            {
                "schema": MODULE.CACHE_SCHEMA,
                "evidence_basis": (
                    "exact_summary_hash_plus_current_state_preflight"
                ),
                "evidence_summary_sha256": "1" * 64,
                "receipt": asdict(_receipt()),
            }
        ),
        encoding="utf-8",
    )
    try:
        MODULE._load_cache(cache_path)
    except ValueError as exc:
        assert "E2C-016:cache_evidence_basis_invalid" in str(exc)
    else:
        raise AssertionError("public aggregate was laundered into a cache")
    assert not hasattr(MODULE, "_reconstruct_from_existing_summary")

def test_cache_key_changes_on_every_qualification_binding() -> None:
    base = dict(
        environment_hash="1" * 64,
        input_commitment="2" * 64,
        replay_semantics_hash="3" * 64,
        run_count=100,
    )
    baseline = MODULE._cache_key(**base)
    mutations = (
        {**base, "environment_hash": "4" * 64},
        {**base, "input_commitment": "5" * 64},
        {**base, "replay_semantics_hash": "6" * 64},
        {**base, "run_count": 99},
    )
    assert all(MODULE._cache_key(**item) != baseline for item in mutations)


def test_cache_rejects_tampered_launch_evidence_chain() -> None:
    receipt = _receipt()
    attacked = replace(
        receipt,
        launch_evidence=(
            (1, "f" * 64),
            *receipt.launch_evidence[1:],
        ),
    )
    errors = MODULE._validate_cached_receipt(
        attacked,
        environment_hash=receipt.environment_hash,
        input_commitment=receipt.input_commitment,
        replay_semantics_hash=receipt.replay_semantics_hash,
        run_count=receipt.fresh_process_count,
    )
    assert "E2C-001:receipt_id_invalid" in errors
    assert "E2C-015:launch_evidence_chain_invalid" in errors

def test_cached_public_summary_excludes_state_keys_and_disposition() -> None:
    summary = MODULE.build_public_summary(_receipt())
    assert summary["contains_replay_or_environment_commitments"] is False
    assert summary["contains_case_identifiers"] is False
    assert summary["nonjoinable"] is True
    assert "environment_hash" not in summary
    assert "input_commitment" not in summary
    assert "replay_semantics_hash" not in summary
    assert "cache_hit" not in summary
