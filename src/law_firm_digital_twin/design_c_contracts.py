from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .hashio import digest


DESIGN_C_CONTRACT_REVISION = "design-c-contract-library-v1"
DESIGN_C_REGISTRY_REVISION = "design-c-unified-registry-v2"
DESIGN_C_BASELINE_ID = "design-c-baseline-v1"

DecisionStatus = Literal["adopted", "delegated", "pending"]
AssetStatus = Literal["existing_partial", "proposed", "deferred"]
ObligationStatus = Literal["binding_existing", "proposed", "deferred", "retired"]
LoopStatus = Literal["proposed_active_g0c", "deferred"]
JobState = Literal["proposed", "running", "passed", "failed", "stopped"]


@dataclass(frozen=True)
class HumanDecisionRecord:
    decision_id: str
    title: str
    status: DecisionStatus
    owner: Literal["Lowell"]
    selected_policy: str
    blocks: tuple[str, ...]
    authority_self_activation: Literal[False] = False


@dataclass(frozen=True)
class DesignCAssetRecord:
    asset_id: str
    title: str
    portable_class: Literal[
        "portable_core",
        "runtime_adapter",
        "sealed_portable_core",
        "protected_portable_core",
    ]
    phase: str
    status: AssetStatus
    depends_on: tuple[str, ...]
    validator_ids: tuple[str, ...]
    human_gate_ids: tuple[str, ...]
    do_not_apply: tuple[str, ...]


@dataclass(frozen=True)
class GateAttachedObligation:
    obligation_id: str
    statement: str
    gate_id: str
    status: ObligationStatus
    source_ref: str
    evidence_ids: tuple[str, ...]
    supersedes: tuple[str, ...] = ()
    world_truth_authority: Literal[False] = False
    self_activation: Literal[False] = False


@dataclass(frozen=True)
class LearningLoopRegistryRow:
    loop_id: str
    title: str
    status: LoopStatus
    gate_id: str
    evidence_class: str
    checker_id: str
    never_modifies: tuple[str, ...]
    human_promotion_required: Literal[True] = True
    self_promotion: Literal[False] = False


@dataclass(frozen=True)
class RuntimeQualificationPointer:
    qualification_id: str
    capability_id: str
    portable_class: Literal["runtime_adapter"]
    state: Literal["qualified_optional_nondefault", "inactive"]
    contract_revision: str
    adapter_revision: str
    runtime_version: str
    evidence_paths: tuple[str, ...]
    canonical_authority: Literal[False] = False


@dataclass(frozen=True)
class DesignCUnifiedRegistry:
    registry_id: str
    baseline_id: str
    revision: str
    decisions: tuple[HumanDecisionRecord, ...]
    assets: tuple[DesignCAssetRecord, ...]
    obligations: tuple[GateAttachedObligation, ...]
    loops: tuple[LearningLoopRegistryRow, ...]
    runtime_qualifications: tuple[RuntimeQualificationPointer, ...]
    source_receipt_ids: tuple[str, ...]
    contains_source_rows: Literal[False]
    contains_secrets: Literal[False]
    external_effects: Literal[False]
    unattended_execution_authorized: Literal[False]
    canonical_activation_authorized: Literal[False]

    @property
    def registry_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class JobBudget:
    max_attempts: int
    max_repairs: int
    max_wall_seconds: int
    max_cost_units: int
    max_output_bytes: int


@dataclass(frozen=True)
class DesignCJobManifest:
    job_id: str
    campaign_id: str
    contract_revision: str
    objective: str
    non_goals: tuple[str, ...]
    input_commitments: tuple[tuple[str, str], ...]
    dependency_hashes: tuple[tuple[str, str], ...]
    output_paths: tuple[str, ...]
    write_owner: str
    checker_id: str
    idempotency_key: str
    checkpoint_path: str
    budget: JobBudget
    required_gate_ids: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    state: JobState = "proposed"
    external_effects: Literal[False] = False
    canonical_truth_write: Literal[False] = False
    human_gate_auto_advance: Literal[False] = False
    unattended_execution_authorized: Literal[False] = False

    @property
    def manifest_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class DesignCJobResult:
    result_id: str
    job_id: str
    manifest_hash: str
    state: Literal["passed", "failed", "stopped"]
    attempt_count: int
    repair_count: int
    output_commitments: tuple[tuple[str, str], ...]
    evidence_commitments: tuple[tuple[str, str], ...]
    failure_codes: tuple[str, ...]
    checker_id: str
    checker_passed: bool
    human_gate_ids_satisfied: tuple[str, ...]
    cost_units_used: int
    wall_seconds_used: int
    canonical_admission: Literal[False] = False
    self_approved: Literal[False] = False

    @property
    def result_hash(self) -> str:
        return digest(self)

