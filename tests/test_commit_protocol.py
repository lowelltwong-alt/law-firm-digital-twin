from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from law_firm_digital_twin.commit_protocol import (
    GENESIS_HEAD_HASH,
    CommitProposal,
)
from law_firm_digital_twin.commit_protocol_validator import (
    validate_commit_snapshot,
    validate_commit_transition,
)
from law_firm_digital_twin.hashio import digest
from law_firm_digital_twin.sqlite_commit_adapter import (
    FAULT_POINTS,
    SQLiteCommitAdapter,
)


def _proposal(
    *,
    ordinal: int = 1,
    parent: str = GENESIS_HEAD_HASH,
    key: str | None = None,
) -> CommitProposal:
    return CommitProposal(
        proposal_id=f"CPROP-{ordinal}",
        idempotency_key=key or f"commit-fixture:{ordinal}:r1",
        command_commitment=digest({"command": ordinal}),
        expected_parent_hash=parent,
        dependency_hash=digest({"dependency": ordinal}),
        event_type=f"fixture_event_{ordinal}",
        result_commitment=digest({"result": ordinal}),
    )


def _adapter(tmp_path: Path) -> SQLiteCommitAdapter:
    return SQLiteCommitAdapter(tmp_path / "commit.sqlite3")


def test_first_commit_atomically_appends_event_command_and_outbox(
    tmp_path: Path,
) -> None:
    adapter = _adapter(tmp_path)
    proposal = _proposal()
    before = adapter.snapshot()
    decision = adapter.commit(proposal)
    after = adapter.snapshot()
    assert decision.disposition == "accepted"
    assert after.event_count == after.command_count == after.outbox_count == 1
    assert after.pending_outbox_count == 1
    assert after.head_hash == decision.event_hash
    assert validate_commit_transition(proposal, before, decision, after) == ()


def test_identical_idempotent_replay_returns_original_without_new_records(
    tmp_path: Path,
) -> None:
    adapter = _adapter(tmp_path)
    proposal = _proposal()
    accepted = adapter.commit(proposal)
    before = adapter.snapshot()
    duplicate = adapter.commit(proposal)
    after = adapter.snapshot()
    assert duplicate.disposition == "duplicate_replay"
    assert duplicate.event_hash == accepted.event_hash
    assert duplicate.outbox_id == accepted.outbox_id
    assert before == after
    assert validate_commit_transition(proposal, before, duplicate, after) == ()


def test_changed_input_cannot_reuse_idempotency_key(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    original = _proposal()
    adapter.commit(original)
    before = adapter.snapshot()
    attacked = replace(
        original, command_commitment=digest("changed-command")
    )
    rejected = adapter.commit(attacked)
    after = adapter.snapshot()
    assert rejected.disposition == "rejected_idempotency_conflict"
    assert before == after
    assert validate_commit_transition(attacked, before, rejected, after) == ()


def test_stale_parent_is_rejected_without_mutation(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    adapter.commit(_proposal())
    before = adapter.snapshot()
    stale = _proposal(ordinal=2, parent=GENESIS_HEAD_HASH)
    rejected = adapter.commit(stale)
    after = adapter.snapshot()
    assert rejected.disposition == "rejected_stale_parent"
    assert before == after
    assert validate_commit_transition(stale, before, rejected, after) == ()


@pytest.mark.parametrize("fault_point", FAULT_POINTS[:-1])
def test_precommit_fault_rolls_back_every_record(
    tmp_path: Path, fault_point: str
) -> None:
    adapter = SQLiteCommitAdapter(tmp_path / f"{fault_point}.sqlite3")
    proposal = _proposal()

    def inject(point: str) -> None:
        if point == fault_point:
            raise RuntimeError(f"injected:{point}")

    with pytest.raises(RuntimeError, match=fault_point):
        adapter.commit(proposal, fault_hook=inject)
    snapshot = adapter.snapshot()
    assert snapshot.event_count == 0
    assert snapshot.command_count == 0
    assert snapshot.outbox_count == 0
    assert snapshot.head_hash == GENESIS_HEAD_HASH
    assert validate_commit_snapshot(snapshot) == ()


def test_fault_after_commit_recovers_as_one_event_and_duplicate(
    tmp_path: Path,
) -> None:
    adapter = _adapter(tmp_path)
    proposal = _proposal()

    def inject(point: str) -> None:
        if point == "after_commit_before_return":
            raise RuntimeError("injected:after_commit_before_return")

    with pytest.raises(RuntimeError, match="after_commit_before_return"):
        adapter.commit(proposal, fault_hook=inject)
    recovered = _adapter(tmp_path)
    before = recovered.snapshot()
    assert before.event_count == 1
    duplicate = recovered.commit(proposal)
    after = recovered.snapshot()
    assert duplicate.disposition == "duplicate_replay"
    assert before == after
    assert validate_commit_transition(proposal, before, duplicate, after) == ()


def test_outbox_acknowledgement_is_idempotent_and_never_external(
    tmp_path: Path,
) -> None:
    adapter = _adapter(tmp_path)
    decision = adapter.commit(_proposal())
    assert adapter.acknowledge_outbox(decision.outbox_id)
    first = adapter.snapshot()
    assert adapter.acknowledge_outbox(decision.outbox_id)
    second = adapter.snapshot()
    assert first == second
    assert second.pending_outbox_count == 0
    assert second.acknowledged_outbox_count == 1
    assert not second.external_effects


def test_concurrent_identical_delivery_commits_once(tmp_path: Path) -> None:
    database = tmp_path / "concurrent.sqlite3"
    SQLiteCommitAdapter(database)
    proposal = _proposal()

    def submit() -> str:
        return SQLiteCommitAdapter(database).commit(proposal).disposition

    with ThreadPoolExecutor(max_workers=2) as executor:
        dispositions = sorted(executor.map(lambda _: submit(), range(2)))
    assert dispositions == ["accepted", "duplicate_replay"]
    snapshot = SQLiteCommitAdapter(database).snapshot()
    assert snapshot.event_count == 1
    assert validate_commit_snapshot(snapshot) == ()


def test_adapter_refuses_canonical_activation_and_prohibited_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="requires_h10"):
        SQLiteCommitAdapter(tmp_path / "canonical.sqlite3", ephemeral_test_only=False)
    with pytest.raises(ValueError, match="prohibited_root"):
        SQLiteCommitAdapter(
            tmp_path / "inside" / "store.sqlite3",
            prohibited_roots=(tmp_path,),
        )


def test_payload_and_authority_claims_are_rejected(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    for attacked in (
        replace(_proposal(), contains_payload=True),
        replace(_proposal(), external_effect_requested=True),
        replace(_proposal(), canonical_write_requested=True),
    ):
        with pytest.raises(ValueError, match="authority_invalid"):
            adapter.commit(attacked)
    assert adapter.snapshot().event_count == 0

def test_commit_adapter_releases_sqlite_handles(tmp_path: Path) -> None:
    database = tmp_path / "handle-release.sqlite3"
    adapter = SQLiteCommitAdapter(database)
    adapter.snapshot()
    database.unlink()
    assert not database.exists()
