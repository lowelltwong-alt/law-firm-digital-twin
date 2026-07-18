from __future__ import annotations

from collections import Counter
from typing import Sequence

from .case_manifest import CapabilityRegistry, build_capability_registry
from .domain_pack_design_contracts import (
    DOMAIN_PACK_DESIGN_REVISION,
    DesignOnlyLitigationDomainPack,
    DomainPackDesignFinding,
    DomainPackDesignValidationReport,
)
from .domain_pack_designs import (
    COMMON_FORBIDDEN_SOURCES,
    COMMON_PROHIBITED_CONTENT,
    COMMON_PROHIBITED_PERSONA_USES,
    CANONICAL_DOMAIN_PACK_VALIDATOR_IDS,
    DESIGN_SAFE_SYNTHETIC_SOURCE_CLASSES,
    FAMILY_PRESSURES,
    REQUIRED_EXPERT_FORBIDDEN_CONCLUSIONS,
    SAFE_AUTHORITY_CATEGORIES,
    SAFE_COMMUNICATION_CONTEXT_IDS,
    SAFE_EXPERT_ESCALATION_IDS,
    SAFE_EXPERT_INDEPENDENCE_CHECK_IDS,
    SAFE_EXPERT_LIMITATION_CATEGORIES,
    SAFE_EXPERT_METHOD_CATEGORIES,
    SAFE_MEMORY_PROCESS_IDS,
    SAFE_ORGANIZATION_INTERFACE_MECHANISMS,
    SAFE_RESOURCE_PRESSURES,
    SAFE_RETENTION_VERSIONING_PATTERNS,
    SAFE_REVIEW_ESCALATION_PATHS,
)
from .hashio import canonical_json, digest


LIFECYCLE_ORDER = (
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
)
FORBIDDEN_DESIGN_TEXT = (
    "http://",
    "https://",
    "file://",
    "openai",
    "anthropic",
    "composer",
    "cursor_runtime",
    "activation_receipt",
    "canonical_admission\":true",
    "runtime_execution\":true",
    "external_source_access\":true",
    "source_admission_state\":\"admitted",
)


def validate_design_only_domain_packs(
    packs: Sequence[DesignOnlyLitigationDomainPack],
    registry: CapabilityRegistry | None = None,
) -> DomainPackDesignValidationReport:
    registry = registry or build_capability_registry()
    findings: list[DomainPackDesignFinding] = []

    def add(code: str, subject: str, message: str) -> None:
        findings.append(DomainPackDesignFinding(code, subject, message))

    if not packs:
        add("DPD-001", "catalog", "design-only domain-pack catalog is empty")
    families = {item.family_id: item for item in registry.case_families}
    pack_ids = [item.pack_id for item in packs]
    family_ids = [item.case_family_id for item in packs]
    if len(pack_ids) != len(set(pack_ids)):
        add("DPD-002", "catalog", "duplicate design-pack id")
    if len(family_ids) != len(set(family_ids)):
        add("DPD-003", "catalog", "duplicate case-family design pack")
    expected_families = {
        item.family_id for item in registry.case_families if item.readiness == "design_only"
    }
    if set(family_ids) != expected_families:
        add("DPD-004", "catalog", "design-pack family coverage mismatch")

    for pack in packs:
        family = families.get(pack.case_family_id)
        if family is None:
            add("DPD-005", pack.pack_id, "unknown case family")
            continue
        if family.readiness != "design_only":
            add("DPD-006", pack.pack_id, "active family entered design-only catalog")
        if pack.case_family_manifest_hash != family.manifest_hash:
            add("DPD-007", pack.pack_id, "stale case-family manifest hash")
        if pack.contract_revision != DOMAIN_PACK_DESIGN_REVISION:
            add("DPD-008", pack.pack_id, "design contract revision mismatch")
        if (
            pack.status != "design_only"
            or pack.activation_gate
            != "human_case_family_activation_and_domain_fixture_qualification"
            or pack.source_admission_state != "no_sources_admitted"
            or pack.learning_state != "not_eligible"
            or pack.runtime_execution is not False
            or pack.external_source_access is not False
            or pack.canonical_truth_write is not False
            or pack.synthetic_only is not True
        ):
            add("DPD-009", pack.pack_id, "design-only authority boundary invalid")
        if pack.forbidden_source_classes != COMMON_FORBIDDEN_SOURCES:
            add("DPD-045", pack.pack_id, "forbidden source boundary is not canonical")
        if pack.validator_ids != CANONICAL_DOMAIN_PACK_VALIDATOR_IDS:
            add("DPD-057", pack.pack_id, "validator contract is not canonical")

        artifacts = {item.artifact_family_id: item for item in pack.artifact_families}
        experts = {item.discipline_id: item for item in pack.expert_disciplines}
        personas = {item.role_id: item for item in pack.persona_roles}
        organizations = {item.context_id: item for item in pack.organization_contexts}
        stages = {item.stage_id: item for item in pack.lifecycle_stages}
        if len(artifacts) != len(pack.artifact_families):
            add("DPD-010", pack.pack_id, "duplicate artifact-family id")
        if len(experts) != len(pack.expert_disciplines):
            add("DPD-011", pack.pack_id, "duplicate expert-discipline id")
        if len(personas) != len(pack.persona_roles):
            add("DPD-012", pack.pack_id, "duplicate persona-role id")
        if len(organizations) != len(pack.organization_contexts):
            add("DPD-013", pack.pack_id, "duplicate organization-context id")
        if len(stages) != len(pack.lifecycle_stages):
            add("DPD-014", pack.pack_id, "duplicate lifecycle-stage id")
        if set(artifacts) != set(family.required_evidence_capabilities):
            add("DPD-015", pack.pack_id, "artifact-family coverage does not match manifest")
        if set(experts) != set(family.expert_domains):
            add("DPD-016", pack.pack_id, "expert-discipline coverage does not match manifest")
        if not set(family.required_roles).issubset(personas):
            add("DPD-017", pack.pack_id, "required persona role missing")
        if set(stages) != set(LIFECYCLE_ORDER):
            add("DPD-018", pack.pack_id, "lifecycle stage coverage mismatch")

        stage_positions = {stage: index for index, stage in enumerate(LIFECYCLE_ORDER)}
        for stage in pack.lifecycle_stages:
            if any(predecessor not in stages for predecessor in stage.predecessor_ids):
                add("DPD-019", stage.stage_id, "unknown lifecycle predecessor")
            if any(
                stage_positions[predecessor] >= stage_positions[stage.stage_id]
                for predecessor in stage.predecessor_ids
                if predecessor in stage_positions
            ):
                add("DPD-020", stage.stage_id, "lifecycle graph is cyclic or reversed")
            if stage.procedural_rule_claims is not False:
                add("DPD-021", stage.stage_id, "design stage claimed procedural authority")

        for artifact in pack.artifact_families:
            if not set(artifact.author_role_ids).issubset(personas):
                add("DPD-022", artifact.artifact_family_id, "artifact author role unresolved")
            if not set(artifact.recipient_role_ids).issubset(personas):
                add("DPD-023", artifact.artifact_family_id, "artifact recipient role unresolved")
            if not set(artifact.fact_domain_ids).issubset(family.fact_domains):
                add("DPD-024", artifact.artifact_family_id, "artifact fact domain unresolved")
            if artifact.lifecycle_from not in stages or artifact.lifecycle_to not in stages:
                add("DPD-025", artifact.artifact_family_id, "artifact lifecycle stage unresolved")
            elif stage_positions[artifact.lifecycle_from] > stage_positions[artifact.lifecycle_to]:
                add("DPD-026", artifact.artifact_family_id, "artifact lifecycle is reversed")
            if len(artifact.expected_metadata_keys) < 4:
                add("DPD-027", artifact.artifact_family_id, "artifact metadata contract is under-specified")
            if not artifact.custody_risk_ids or not artifact.version_risk_ids:
                add("DPD-028", artifact.artifact_family_id, "custody or version risks missing")
            if artifact.allowed_synthetic_source_classes != DESIGN_SAFE_SYNTHETIC_SOURCE_CLASSES:
                add("DPD-029", artifact.artifact_family_id, "synthetic source boundary is not canonical")
            if set(artifact.allowed_synthetic_source_classes) & set(pack.forbidden_source_classes):
                add("DPD-046", artifact.artifact_family_id, "allowed and forbidden sources intersect")
            if artifact.prohibited_content_classes != COMMON_PROHIBITED_CONTENT:
                add("DPD-030", artifact.artifact_family_id, "prohibited content boundary is not canonical")

        for expert in pack.expert_disciplines:
            if not set(expert.material_family_ids).issubset(artifacts):
                add("DPD-031", expert.discipline_id, "expert material family unresolved")
            if len(expert.material_family_ids) < 2:
                add("DPD-032", expert.discipline_id, "expert source scope is under-specified")
            if (
                expert.permitted_output_boundary != "scope_method_limitations_only"
                or expert.runtime_execution is not False
                or expert.legal_or_medical_truth_claims is not False
                or expert.credential_verification is not False
            ):
                add("DPD-033", expert.discipline_id, "expert authority boundary invalid")
            if not expert.method_categories or not set(expert.method_categories).issubset(
                SAFE_EXPERT_METHOD_CATEGORIES
            ):
                add("DPD-034", expert.discipline_id, "expert method is outside safe vocabulary")
            if expert.limitation_categories != SAFE_EXPERT_LIMITATION_CATEGORIES:
                add("DPD-047", expert.discipline_id, "expert limitation boundary is not canonical")
            if expert.forbidden_conclusion_ids != REQUIRED_EXPERT_FORBIDDEN_CONCLUSIONS:
                add("DPD-048", expert.discipline_id, "expert forbidden conclusions are incomplete")
            if expert.independence_check_ids != SAFE_EXPERT_INDEPENDENCE_CHECK_IDS:
                add("DPD-035", expert.discipline_id, "expert independence contract is not canonical")
            if expert.cross_domain_escalation_ids != SAFE_EXPERT_ESCALATION_IDS:
                add("DPD-058", expert.discipline_id, "expert escalation contract is not canonical")
            expected_fixture = (
                f"fixture.design-expert.{family.family_id}.{expert.discipline_id}.v1"
            )
            if expert.qualification_fixture_id != expected_fixture:
                add("DPD-059", expert.discipline_id, "expert qualification fixture is not canonical")

        for persona in pack.persona_roles:
            if not set(persona.knowledge_artifact_family_ids).issubset(artifacts):
                add("DPD-036", persona.role_id, "persona knowledge artifact unresolved")
            if not persona.organization_interface_ids or persona.organization_interface_ids[0] not in organizations:
                add("DPD-037", persona.role_id, "persona organization interface unresolved")
            if persona.prohibited_causal_uses != COMMON_PROHIBITED_PERSONA_USES:
                add("DPD-038", persona.role_id, "persona stereotype boundary incomplete")
            if persona.memory_process_ids != SAFE_MEMORY_PROCESS_IDS:
                add("DPD-039", persona.role_id, "memory mechanism is outside safe vocabulary")
            if persona.communication_context_ids != SAFE_COMMUNICATION_CONTEXT_IDS:
                add("DPD-049", persona.role_id, "communication mechanism is outside safe vocabulary")
            if persona.pressure_factor_ids != FAMILY_PRESSURES[pack.case_family_id]:
                add("DPD-050", persona.role_id, "pressure mechanism is outside family vocabulary")
            if persona.organization_interface_ids != (
                persona.organization_side,
                *SAFE_ORGANIZATION_INTERFACE_MECHANISMS,
            ):
                add("DPD-051", persona.role_id, "organization interface is outside safe vocabulary")
            if not persona.authority_categories or not set(persona.authority_categories).issubset(
                SAFE_AUTHORITY_CATEGORIES
            ):
                add("DPD-052", persona.role_id, "authority category is outside safe vocabulary")
            if persona.time_varying is not True:
                add("DPD-040", persona.role_id, "persona role is not time-varying")

        for organization in pack.organization_contexts:
            if not set(organization.role_ids).issubset(personas):
                add("DPD-041", organization.context_id, "organization role unresolved")
            expected_systems = (
                f"synthetic_{family.family_id}_record_system",
                "synthetic_message_and_task_system",
            )
            if organization.systems_and_records != expected_systems:
                add("DPD-042", organization.context_id, "organization system vocabulary invalid")
            if organization.workflow_constraints != FAMILY_PRESSURES[pack.case_family_id]:
                add("DPD-053", organization.context_id, "organization workflow vocabulary invalid")
            if organization.review_and_escalation_paths != SAFE_REVIEW_ESCALATION_PATHS:
                add("DPD-054", organization.context_id, "organization review vocabulary invalid")
            if organization.retention_and_versioning_patterns != SAFE_RETENTION_VERSIONING_PATTERNS:
                add("DPD-055", organization.context_id, "organization retention vocabulary invalid")
            if organization.incentive_or_resource_pressures != SAFE_RESOURCE_PRESSURES:
                add("DPD-056", organization.context_id, "organization pressure vocabulary invalid")
            if organization.prohibited_person_inferences != COMMON_PROHIBITED_PERSONA_USES:
                add("DPD-043", organization.context_id, "organization stereotype boundary incomplete")

        design_text = canonical_json(pack).lower()
        for forbidden in FORBIDDEN_DESIGN_TEXT:
            if forbidden in design_text:
                add("DPD-044", pack.pack_id, f"forbidden design text: {forbidden}")

    return DomainPackDesignValidationReport(
        passed=not findings,
        findings=tuple(findings),
        pack_hashes=tuple(item.pack_hash for item in packs),
    )


def build_public_domain_pack_design_catalog(
    packs: Sequence[DesignOnlyLitigationDomainPack],
    registry: CapabilityRegistry | None = None,
) -> dict[str, object]:
    report = validate_design_only_domain_packs(packs, registry)
    if not report.passed:
        raise ValueError("domain_pack_design_validation_failed")
    rows: list[dict[str, object]] = []
    for pack in packs:
        intent_counts = Counter(item.intent for item in pack.artifact_families)
        rows.append(
            {
                "pack_id": pack.pack_id,
                "revision": pack.revision,
                "case_family_id": pack.case_family_id,
                "status": "design_only",
                "artifact_family_count": len(pack.artifact_families),
                "artifact_intent_counts": dict(sorted(intent_counts.items())),
                "expert_discipline_count": len(pack.expert_disciplines),
                "persona_role_count": len(pack.persona_roles),
                "organization_context_count": len(pack.organization_contexts),
                "lifecycle_stage_count": len(pack.lifecycle_stages),
                "source_admission_state": "no_sources_admitted",
                "learning_state": "not_eligible",
                "runtime_execution": False,
                "synthetic_only": True,
            }
        )
    payload = {
        "contract_revision": DOMAIN_PACK_DESIGN_REVISION,
        "design_pack_contract_commitment": digest(tuple(item.pack_hash for item in packs)),
        "pack_count": len(packs),
        "packs": tuple(rows),
        "runtime_execution_count": 0,
        "active_family_count": 0,
        "source_admitted_pack_count": 0,
        "learning_eligible_pack_count": 0,
        "artifact_bodies_included": False,
        "persona_states_included": False,
        "source_rows_included": False,
        "synthetic_only": True,
        "scope_statement": (
            "Design-only litigation-domain blueprints; not executable evidence packs, "
            "not source admission, and not authority to activate a case family."
        ),
    }
    return {
        "catalog_id": f"DOMAIN-DESIGN-{digest(payload)[:18]}",
        **payload,
    }
