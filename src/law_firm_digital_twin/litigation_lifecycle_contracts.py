from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .hashio import digest


LIFECYCLE_CONTRACT_REVISION = "employment-lifecycle-contracts-g2-v1"

BranchScope = Literal[
    "universal",
    "motion",
    "settlement",
    "mediation",
    "administrative_agency_design_only",
    "arbitration_design_only",
    "trial",
    "appeal",
]
ActivationState = Literal["planning_only", "inactive_pending_kernel_event"]


@dataclass(frozen=True)
class LifecycleStageContract:
    stage_id: str
    ordinal: int
    label: str
    branch_scope: BranchScope
    entry_event_ids: tuple[str, ...]
    exit_event_ids: tuple[str, ...]
    runtime_execution: Literal[False] = False


@dataclass(frozen=True)
class LifecycleDocumentType:
    document_type_id: str
    stage_id: str
    label: str
    record_kind: str
    responsible_role_ids: tuple[str, ...]
    recipient_role_ids: tuple[str, ...]
    prerequisite_type_ids: tuple[str, ...]
    activation_event_ids: tuple[str, ...]
    branch_scope: BranchScope
    confidentiality_class: str
    target_shape: str
    required_metadata_keys: tuple[str, ...]
    fact_domain_dependencies: tuple[str, ...]
    custody_policy_id: str
    versioning_policy_id: str
    source_class: Literal["synthetic_design_specification"]
    rule_admission_state: Literal["no_rules_admitted"]
    filing_intent: Literal[
        "not_a_filing",
        "simulated_filing_intent_only",
    ]
    billing_task_category: str
    body_included: Literal[False] = False
    runtime_execution: Literal[False] = False
    legal_compliance_claimed: Literal[False] = False
    native_fidelity_claimed: Literal[False] = False


@dataclass(frozen=True)
class EmploymentLifecycleDocumentCatalog:
    catalog_id: str
    case_family_id: Literal["employment_defense_g2"]
    stages: tuple[LifecycleStageContract, ...]
    document_types: tuple[LifecycleDocumentType, ...]
    source_admission_state: Literal["no_sources_admitted"]
    external_access: Literal[False]
    runtime_execution: Literal[False]
    learning_eligible: Literal[False]
    canonical_truth_write: Literal[False]
    activation_gate: Literal[
        "human_document_family_activation_and_fixture_qualification"
    ]
    revision: str = LIFECYCLE_CONTRACT_REVISION

    @property
    def catalog_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class DossierDocumentNode:
    node_id: str
    public_document_type_id: str
    stage_id: str
    branch_scope: BranchScope
    activation_state: ActivationState
    prerequisite_node_ids: tuple[str, ...]
    activation_event_ids: tuple[str, ...]
    responsible_role_ids: tuple[str, ...]
    confidentiality_class: str
    filing_intent: str
    billing_task_category: str
    body_included: Literal[False] = False
    runtime_execution: Literal[False] = False


@dataclass(frozen=True)
class QualifiedMatterDossierBlueprint:
    blueprint_id: str
    case_family_id: Literal["employment_defense_g2"]
    operating_projection_hash: str
    qualification_receipt_hash: str
    catalog_hash: str
    graph_hash: str
    nodes: tuple[DossierDocumentNode, ...]
    rule_admission_state: Literal["no_rules_admitted"]
    source_admission_state: Literal["no_sources_admitted"]
    branch_activation_authority: Literal["future_kernel_event_adapter_required"]
    future_branches_active: Literal[False]
    legal_compliance_claimed: Literal[False]
    native_fidelity_claimed: Literal[False]
    canonical_admission: Literal[False]
    bodies_included: Literal[False]
    runtime_execution: Literal[False]
    revision: str = LIFECYCLE_CONTRACT_REVISION

    @property
    def blueprint_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class DossierValidationFinding:
    code: str
    subject: str
    message: str


@dataclass(frozen=True)
class DossierValidationReport:
    passed: bool
    findings: tuple[DossierValidationFinding, ...]
    subject_hash: str
    validator_revision: str = LIFECYCLE_CONTRACT_REVISION


@dataclass(frozen=True)
class PublicDossierCatalogSummary:
    release_id: str
    case_family_id: Literal["employment_defense_g2"]
    lifecycle_stage_count: int
    document_type_count: int
    branch_scope_counts: tuple[tuple[str, int], ...]
    confidentiality_class_counts: tuple[tuple[str, int], ...]
    billing_task_category_counts: tuple[tuple[str, int], ...]
    planning_blueprint_count: int
    catalog_hash: str
    aggregate_blueprint_commitment: str
    source_admission_state: Literal["no_sources_admitted"]
    legal_compliance_claimed: Literal[False]
    native_fidelity_claimed: Literal[False]
    runtime_execution: Literal[False]

