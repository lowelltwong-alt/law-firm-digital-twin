from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .hashio import digest


DOMAIN_PACK_DESIGN_REVISION = "litigation-domain-pack-design-v1"
DesignStatus = Literal["design_only"]
LearningState = Literal["not_eligible"]
ArtifactIntent = Literal[
    "business_record",
    "system_record",
    "contract_record",
    "event_record",
    "technical_record",
    "expert_scope_record",
    "litigation_process_record",
    "causal_noise",
]
LifecycleKind = Literal[
    "preincident",
    "incident_or_service",
    "intake",
    "investigation",
    "claim_or_pleading",
    "discovery",
    "adr",
    "trial_preparation",
    "resolution",
    "closeout",
]


@dataclass(frozen=True)
class DesignArtifactFamily:
    artifact_family_id: str
    label: str
    intent: ArtifactIntent
    channel_kind: str
    author_role_ids: tuple[str, ...]
    recipient_role_ids: tuple[str, ...]
    fact_domain_ids: tuple[str, ...]
    lifecycle_from: LifecycleKind
    lifecycle_to: LifecycleKind
    expected_metadata_keys: tuple[str, ...]
    lineage_policy_id: str
    custody_risk_ids: tuple[str, ...]
    version_risk_ids: tuple[str, ...]
    causal_noise_sibling_ids: tuple[str, ...]
    allowed_synthetic_source_classes: tuple[str, ...]
    prohibited_content_classes: tuple[str, ...]

    @property
    def contract_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class DesignExpertDiscipline:
    discipline_id: str
    label: str
    material_family_ids: tuple[str, ...]
    method_categories: tuple[str, ...]
    limitation_categories: tuple[str, ...]
    independence_check_ids: tuple[str, ...]
    cross_domain_escalation_ids: tuple[str, ...]
    forbidden_conclusion_ids: tuple[str, ...]
    qualification_fixture_id: str
    permitted_output_boundary: Literal["scope_method_limitations_only"] = (
        "scope_method_limitations_only"
    )
    runtime_execution: Literal[False] = False
    legal_or_medical_truth_claims: Literal[False] = False
    credential_verification: Literal[False] = False

    @property
    def contract_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class DesignPersonaRole:
    role_id: str
    organization_side: str
    authority_categories: tuple[str, ...]
    knowledge_artifact_family_ids: tuple[str, ...]
    communication_context_ids: tuple[str, ...]
    memory_process_ids: tuple[str, ...]
    pressure_factor_ids: tuple[str, ...]
    organization_interface_ids: tuple[str, ...]
    prohibited_causal_uses: tuple[str, ...]
    time_varying: Literal[True] = True

    @property
    def contract_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class DesignOrganizationContext:
    context_id: str
    role_ids: tuple[str, ...]
    systems_and_records: tuple[str, ...]
    workflow_constraints: tuple[str, ...]
    review_and_escalation_paths: tuple[str, ...]
    retention_and_versioning_patterns: tuple[str, ...]
    incentive_or_resource_pressures: tuple[str, ...]
    prohibited_person_inferences: tuple[str, ...]

    @property
    def contract_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class DesignLifecycleStage:
    stage_id: LifecycleKind
    predecessor_ids: tuple[LifecycleKind, ...]
    permitted_artifact_intents: tuple[ArtifactIntent, ...]
    permitted_role_actions: tuple[str, ...]
    procedural_rule_claims: Literal[False] = False

    @property
    def contract_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class DesignOnlyLitigationDomainPack:
    pack_id: str
    revision: str
    contract_revision: str
    case_family_id: str
    case_family_manifest_hash: str
    status: DesignStatus
    activation_gate: Literal[
        "human_case_family_activation_and_domain_fixture_qualification"
    ]
    artifact_families: tuple[DesignArtifactFamily, ...]
    expert_disciplines: tuple[DesignExpertDiscipline, ...]
    persona_roles: tuple[DesignPersonaRole, ...]
    organization_contexts: tuple[DesignOrganizationContext, ...]
    lifecycle_stages: tuple[DesignLifecycleStage, ...]
    validator_ids: tuple[str, ...]
    source_admission_state: Literal["no_sources_admitted"]
    learning_state: LearningState
    forbidden_source_classes: tuple[str, ...]
    runtime_execution: Literal[False] = False
    synthetic_only: Literal[True] = True
    external_source_access: Literal[False] = False
    canonical_truth_write: Literal[False] = False

    @property
    def pack_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class DomainPackDesignFinding:
    code: str
    subject: str
    message: str


@dataclass(frozen=True)
class DomainPackDesignValidationReport:
    passed: bool
    findings: tuple[DomainPackDesignFinding, ...]
    pack_hashes: tuple[str, ...]
    validator_revision: str = DOMAIN_PACK_DESIGN_REVISION
