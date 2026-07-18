from __future__ import annotations

from .commit_protocol import (
    COMMIT_SCHEMA_REVISION,
    CommitDecision,
    CommitProposal,
    CommitStoreSnapshot,
)
from .sqlite_commit_adapter import SQLITE_COMMIT_ADAPTER_REVISION


COMMIT_CHECKER_REVISION = "design-c-commit-independent-checker-g0c-v1"


def validate_commit_snapshot(snapshot: CommitStoreSnapshot) -> tuple[str, ...]:
    errors: list[str] = []
    if snapshot.adapter_revision != SQLITE_COMMIT_ADAPTER_REVISION:
        errors.append("CPV-001:adapter_revision_invalid")
    if snapshot.schema_revision != COMMIT_SCHEMA_REVISION:
        errors.append("CPV-002:schema_revision_invalid")
    if snapshot.sqlite_integrity != "ok":
        errors.append("CPV-003:sqlite_integrity_failed")
    if snapshot.invariant_errors:
        errors.append("CPV-004:store_invariants_failed")
    if not (
        snapshot.event_count
        == snapshot.command_count
        == snapshot.outbox_count
        == snapshot.pending_outbox_count + snapshot.acknowledged_outbox_count
    ):
        errors.append("CPV-005:atomic_record_count_mismatch")
    if (
        not snapshot.ephemeral_test_only
        or snapshot.canonical_store
        or snapshot.external_effects
    ):
        errors.append("CPV-006:store_authority_boundary_invalid")
    if len(snapshot.head_hash) != 64:
        errors.append("CPV-007:head_hash_invalid")
    return tuple(errors)


def validate_commit_transition(
    proposal: CommitProposal,
    before: CommitStoreSnapshot,
    decision: CommitDecision,
    after: CommitStoreSnapshot,
) -> tuple[str, ...]:
    errors = list(validate_commit_snapshot(before))
    errors.extend(validate_commit_snapshot(after))
    if decision.proposal_hash != proposal.proposal_hash:
        errors.append("CPT-001:proposal_binding_invalid")
    if (
        not decision.ephemeral_test_only
        or decision.canonical_admission
        or decision.external_effects
    ):
        errors.append("CPT-002:decision_authority_boundary_invalid")
    if decision.disposition == "accepted":
        if before.head_hash != proposal.expected_parent_hash:
            errors.append("CPT-003:accepted_stale_parent")
        if not (
            after.event_count == before.event_count + 1
            and after.command_count == before.command_count + 1
            and after.outbox_count == before.outbox_count + 1
            and after.pending_outbox_count == before.pending_outbox_count + 1
        ):
            errors.append("CPT-004:accepted_commit_not_atomic")
        if (
            decision.event_sequence != after.event_count
            or decision.event_hash != after.head_hash
            or decision.head_hash != after.head_hash
            or decision.duplicate
            or decision.rejection_code
        ):
            errors.append("CPT-005:accepted_decision_invalid")
    elif decision.disposition == "duplicate_replay":
        if before.checkpoint_hash != after.checkpoint_hash:
            errors.append("CPT-006:duplicate_changed_store")
        if not decision.duplicate or not decision.event_hash or decision.rejection_code:
            errors.append("CPT-007:duplicate_decision_invalid")
    elif decision.disposition in {
        "rejected_stale_parent",
        "rejected_idempotency_conflict",
    }:
        if before.checkpoint_hash != after.checkpoint_hash:
            errors.append("CPT-008:rejection_changed_store")
        if decision.event_sequence is not None or decision.event_hash or decision.outbox_id:
            errors.append("CPT-009:rejection_claimed_event")
        if decision.duplicate or not decision.rejection_code:
            errors.append("CPT-010:rejection_decision_invalid")
    else:  # pragma: no cover - typed contract, retained for hostile runtime input
        errors.append("CPT-011:unknown_disposition")
    return tuple(dict.fromkeys(errors))

