from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .hashio import digest


OPERATIONAL_MESH_REVISION = "operational-expert-mesh-g2-v1"
DataClass = Literal["synthetic", "public", "private", "client"]
EffectClass = Literal[
    "advisory_only",
    "simulation_planning_only",
    "external_write",
    "legal_decision",
    "financial_posting",
]
RouteStatus = Literal["routed", "blocked", "human_gate_required"]


@dataclass(frozen=True)
class OperationalRole:
    role_id: str
    domain: str
    capability_ids: tuple[str, ...]
    input_contract_ids: tuple[str, ...]
    output_contract_ids: tuple[str, ...]
    checker_role_id: str
    separation_group: str
    required_authority_kinds: tuple[str, ...] = ()
    required_prerequisite_kinds: tuple[str, ...] = ()
    human_gate_ids: tuple[str, ...] = ()
    requires_source_admission: bool = False
    requires_reuse_release: bool = False
    adapter_kind: str | None = None
    active: bool = True
    provider_neutral: Literal[True] = True
    simulation_only: Literal[True] = True
    canonical_truth_write: Literal[False] = False
    external_effects: Literal[False] = False

    @property
    def role_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class OperationalWorkRequest:
    request_id: str
    matter_commitment: str
    capability_id: str
    requester_role_id: str
    data_class: DataClass = "synthetic"
    effect_class: EffectClass = "simulation_planning_only"
    source_admission_receipt_ids: tuple[str, ...] = ()
    reuse_release_receipt_ids: tuple[str, ...] = ()
    authority_artifact_ids: tuple[str, ...] = ()
    prerequisite_receipt_ids: tuple[str, ...] = ()
    requested_adapter: str | None = None
    synthetic_only: bool = True
    external_io: bool = False

    @property
    def request_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class VerifiedOperationalRecord:
    record_id: str
    record_kind: str
    issuer_id: str
    issuer_class: Literal["named_human", "kernel"]
    subject_matter_commitment: str
    scope_capability_ids: tuple[str, ...]
    valid_from_revision: str
    valid_through_revision: str
    asset_digest: str
    source_class: Literal[
        "synthetic",
        "public",
        "released_local_asset",
        "kernel_event",
    ]
    approved: bool

    @property
    def record_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class OperationalAuthorityLedger:
    ledger_id: str
    issuer_id: Literal["kernel.operational_authority_registry.v1"]
    known_matter_commitments: tuple[str, ...]
    known_requester_role_ids: tuple[str, ...]
    records: tuple[VerifiedOperationalRecord, ...]

    @property
    def ledger_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class OperationalRoutingDecision:
    request_id: str
    request_hash: str
    status: RouteStatus
    worker_role_id: str | None
    checker_role_id: str | None
    reason_codes: tuple[str, ...]
    required_human_gates: tuple[str, ...]
    registry_commitment: str
    authority_ledger_commitment: str
    mesh_revision: str = OPERATIONAL_MESH_REVISION
    proposal_only: Literal[True] = True
    external_effects: Literal[False] = False
    canonical_admission: Literal[False] = False

    @property
    def decision_hash(self) -> str:
        return digest(self)
