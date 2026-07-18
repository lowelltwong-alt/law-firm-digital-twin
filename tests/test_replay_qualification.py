from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from law_firm_digital_twin.replay_qualification import (
    StaleReplayEnvironmentError,
    build_environment_lock,
    qualify_fresh_process_replay,
    run_replay_subprocess,
)


ROOT = Path(__file__).resolve().parents[1]


def test_environment_lock_is_deterministic_complete_and_nonsecret() -> None:
    first = build_environment_lock(ROOT)
    replay = build_environment_lock(ROOT)
    assert first == replay
    assert first.environment_hash == replay.environment_hash
    assert first.python_hash_seed in {"UNSET", "0"}
    assert {item[0] for item in first.dependency_lock_hashes} == {
        "pyproject.toml",
        "requirements/simulation.lock",
    }
    assert first.package_versions == (("simpy", "4.1.2"),)
    assert len(first.source_tree_hash) == 64
    assert first.source_module_count >= 3
    assert not first.contains_secrets
    assert not first.contains_case_identifiers


def test_two_fresh_subprocesses_have_identical_replay_semantics() -> None:
    preflight = run_replay_subprocess(
        ROOT, run_ordinal=0, expected_environment_hash=None
    )
    first = run_replay_subprocess(
        ROOT,
        run_ordinal=1,
        expected_environment_hash=preflight.environment_hash,
    )
    second = run_replay_subprocess(
        ROOT,
        run_ordinal=2,
        expected_environment_hash=preflight.environment_hash,
    )
    assert first.replay_semantics_hash == second.replay_semantics_hash
    assert first.input_commitment == second.input_commitment
    assert first.environment_hash == second.environment_hash
    assert first.run_ordinal == 1
    assert second.run_ordinal == 2
    assert first.launch_nonce_commitment != second.launch_nonce_commitment
    assert len(first.launch_nonce_commitment) == 64
    assert not first.external_effects
    assert not first.canonical_write


def test_parent_rejects_wrong_launch_nonce_commitment(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "worker_revision": "hostile-worker",
        "environment_hash": "1" * 64,
        "input_commitment": "2" * 64,
        "event_hash": "3" * 64,
        "projection_hash": "4" * 64,
        "denial_hash": "5" * 64,
        "command_hash": "6" * 64,
        "berean_hash": "7" * 64,
        "finance_hash": "8" * 64,
        "process_id": 100,
        "run_ordinal": 7,
        "launch_nonce_commitment": "0" * 64,
    }
    completed = SimpleNamespace(
        stdout=json.dumps(payload), stderr="", returncode=0
    )
    monkeypatch.setattr(
        "law_firm_digital_twin.replay_qualification.subprocess.run",
        lambda *args, **kwargs: completed,
    )
    with pytest.raises(RuntimeError, match="replay_launch_nonce_mismatch"):
        run_replay_subprocess(
            ROOT, run_ordinal=7, expected_environment_hash=None
        )

def test_stale_environment_expectation_fails_loudly() -> None:
    with pytest.raises(
        StaleReplayEnvironmentError, match="stale_environment_or_dependency"
    ):
        run_replay_subprocess(
            ROOT,
            run_ordinal=99,
            expected_environment_hash="0" * 64,
        )


def test_bounded_fresh_process_qualification_is_noncanonical() -> None:
    receipt = qualify_fresh_process_replay(ROOT, run_count=3)
    assert receipt.fresh_process_count == 3
    assert 0 < receipt.unique_process_id_count <= 3
    assert receipt.verified_launch_count == 3
    assert receipt.unique_launch_commitment_count == 3
    assert receipt.all_semantics_identical
    assert receipt.environment_lock_validated
    assert receipt.stale_environment_rejected
    assert receipt.subprocess_isolation_used
    assert not receipt.changed_input_same_hash_required
    assert not receipt.canonical_admission
    assert not receipt.canonical_write
    assert not receipt.external_effects
    assert not receipt.contains_case_identifiers


@pytest.mark.parametrize("run_count", (0, 1, 1001))
def test_replay_run_count_ceiling_is_enforced(run_count: int) -> None:
    with pytest.raises(ValueError, match="replay_run_count_invalid"):
        qualify_fresh_process_replay(ROOT, run_count=run_count)


@pytest.mark.parametrize("max_workers", (0, 9))
def test_replay_worker_count_ceiling_is_enforced(max_workers: int) -> None:
    with pytest.raises(ValueError, match="replay_worker_count_invalid"):
        qualify_fresh_process_replay(
            ROOT, run_count=3, max_workers=max_workers
        )

def test_checked_in_public_replay_summary_is_nonjoinable() -> None:
    summary = json.loads(
        (
            ROOT
            / "generated"
            / "design-c-e2-replay-v1"
            / "summary.json"
        ).read_text(encoding="utf-8")
    )
    assert summary["run_count"] == 100
    assert summary["verified_launch_count"] == 100
    assert summary["unique_launch_commitment_count"] == 100
    assert summary["all_semantics_identical"] is True
    assert summary["environment_lock_validated"] is True
    assert summary["stale_environment_rejected"] is True
    assert summary["canonical_admission"] is False
    assert summary["canonical_write"] is False
    assert summary["contains_case_identifiers"] is False
    assert summary["contains_replay_or_environment_commitments"] is False
    assert summary["nonjoinable"] is True
    assert all(
        len(value) != 64
        for value in summary.values()
        if isinstance(value, str)
    )
