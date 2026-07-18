from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .hashio import digest


SPECIALIST_MESH_REVISION = "artifact-specialist-mesh-g2-v1"
MeshPhase = Literal["planner", "writer", "renderer", "checker"]
MeshReadiness = Literal["active_g2", "design_only"]


@dataclass(frozen=True)
class EvidenceDomainPack:
    pack_id: str
    revision: str
    case_family_id: str
    case_family_manifest_hash: str
    readiness: MeshReadiness
    evidence_capability_ids: tuple[str, ...]
    expertise_topics: tuple[str, ...]
    required_validator_ids: tuple[str, ...]
    protected_fixture_id: str
    activation_gate: str
    provider_neutral: Literal[True] = True
    synthetic_only: Literal[True] = True
    external_source_access: Literal[False] = False

    @property
    def pack_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class SpecialistAssignment:
    assignment_id: str
    phase: MeshPhase
    specialist_capability_id: str
    specialist_revision: str
    specialist_capability_contract_hash: str
    capability_classification: str
    input_contract_ids: tuple[str, ...]
    output_contract_ids: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    effect_scope: str
    independent_of_capability_ids: tuple[str, ...]
    runtime_executed: Literal[False] = False
    canonical_truth_write: Literal[False] = False

    @property
    def assignment_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class ArtifactProductionManifest:
    manifest_id: str
    mesh_revision: str
    world_namespace_commitment: str
    matter_namespace_commitment: str
    case_family_id: str
    case_family_manifest_hash: str
    domain_pack_id: str
    domain_pack_revision: str
    domain_pack_hash: str
    evidence_capability_id: str
    evidence_capability_revision: str
    evidence_capability_contract_hash: str
    artifact_family_id: str
    channel_kind: str
    plan_id: str
    plan_hash: str
    renderer_projection_id: str
    renderer_projection_hash: str
    persona_state_id: str
    persona_state_hash: str
    persona_view_hash: str
    assertion_scope_commitment: str
    knowledge_frontier_commitment: str
    authority_frontier_commitment: str
    relationship_scope_commitment: str
    lineage_commitment: str
    required_metadata_commitment: str
    simulated_target_native_format: str
    assignments: tuple[SpecialistAssignment, ...]
    required_validator_ids: tuple[str, ...]
    excluded_input_planes: tuple[str, ...]
    proposal_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    canonical_admission: Literal[False] = False

    @property
    def manifest_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class ArtifactMeshLocalReceipt:
    receipt_id: str
    mesh_revision: str
    manifest_id: str
    manifest_hash: str
    plan_hash: str
    renderer_projection_hash: str
    staged_artifact_hash: str
    local_shape_receipt_hash: str
    decision: Literal["local_mesh_contract_validated_only"]
    runtime_specialists_executed: Literal[False] = False
    fact_authority_validated: Literal[False] = False
    lineage_graph_validated: Literal[False] = False
    canonical_admission: Literal[False] = False

    @property
    def receipt_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class ArtifactMeshValidationFinding:
    code: str
    subject: str
    message: str


@dataclass(frozen=True)
class ArtifactMeshValidationReport:
    passed: bool
    findings: tuple[ArtifactMeshValidationFinding, ...]
    mesh_commitment: str
    validator_revision: str = SPECIALIST_MESH_REVISION
