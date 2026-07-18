from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Protocol

from .hashio import digest


COMMIT_CORE_REVISION = "design-c-commit-protocol-g0c-v1"
COMMIT_SCHEMA_REVISION = "design-c-commit-sqlite-schema-g0c-v1"
GENESIS_HEAD_HASH = digest("design-c-commit-genesis-g0c-v1")

CommitDisposition = Literal[
    "accepted",
    "duplicate_replay",
    "rejected_stale_parent",
    "rejected_idempotency_conflict",
]


@dataclass(frozen=True)
class CommitProposal:
    proposal_id: str
    idempotency_key: str
    command_commitment: str
    expected_parent_hash: str
    dependency_hash: str
    event_type: str
    result_commitment: str
    core_revision: str = COMMIT_CORE_REVISION
    contains_payload: Literal[False] = False
    external_effect_requested: Literal[False] = False
    canonical_write_requested: Literal[False] = False

    @property
    def proposal_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class CommitDecision:
    decision_id: str
    proposal_hash: str
    disposition: CommitDisposition
    event_sequence: int | None
    event_hash: str
    head_hash: str
    outbox_id: str
    duplicate: bool
    rejection_code: str
    adapter_revision: str
    schema_revision: str
    ephemeral_test_only: Literal[True]
    canonical_admission: Literal[False]
    external_effects: Literal[False]

    @property
    def decision_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class CommitStoreSnapshot:
    adapter_revision: str
    schema_revision: str
    head_hash: str
    event_count: int
    command_count: int
    outbox_count: int
    pending_outbox_count: int
    acknowledged_outbox_count: int
    event_chain_hash: str
    outbox_state_hash: str
    invariant_errors: tuple[str, ...]
    sqlite_integrity: str
    ephemeral_test_only: Literal[True]
    canonical_store: Literal[False]
    external_effects: Literal[False]

    @property
    def checkpoint_hash(self) -> str:
        return digest(self)


FaultHook = Callable[[str], None]


class CommitRuntimeAdapter(Protocol):
    adapter_revision: str
    schema_revision: str

    def commit(
        self,
        proposal: CommitProposal,
        *,
        fault_hook: FaultHook | None = None,
    ) -> CommitDecision: ...

    def snapshot(self) -> CommitStoreSnapshot: ...

