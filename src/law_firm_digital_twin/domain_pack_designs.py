from __future__ import annotations

from collections import Counter

from .case_manifest import CapabilityRegistry, CaseFamilyManifest, build_capability_registry
from .domain_pack_design_contracts import (
    DOMAIN_PACK_DESIGN_REVISION,
    ArtifactIntent,
    DesignArtifactFamily,
    DesignExpertDiscipline,
    DesignLifecycleStage,
    DesignOnlyLitigationDomainPack,
    DesignOrganizationContext,
    DesignPersonaRole,
    LifecycleKind,
)


COMMON_PROHIBITED_PERSONA_USES = (
    "mbti_as_validated_cause",
    "left_right_brain_claim",
    "protected_attribute_outcome_rule",
    "education_equals_intelligence",
    "class_determines_grammar",
    "profession_determines_voice",
    "diagnosis_without_authority",
    "role_determines_credibility",
)
COMMON_PROHIBITED_CONTENT = (
    "real_identity_or_credential",
    "real_client_or_patient_data",
    "unadmitted_legal_or_regulatory_rule",
    "oracle_or_design_label",
    "privileged_body_without_projection_grant",
    "unsupported_diagnosis_or_causation",
    "court_or_native_fidelity_claim",
)
COMMON_FORBIDDEN_SOURCES = (
    "private_source_rows",
    "real_client_files",
    "raw_email_or_message_corpus",
    "purchased_pacer_material",
    "unreceipted_repository_asset",
    "credentials_or_secrets",
    "live_external_service",
)
DESIGN_SAFE_SYNTHETIC_SOURCE_CLASSES = (
    "kernel_generated_business_process",
    "kernel_generated_system_event",
    "admitted_synthetic_case_fact_projection",
)
SAFE_EXPERT_METHOD_CATEGORIES = frozenset(
    {
        "source_bounded_chronology",
        "stated_domain_method",
        "alternative_cause_accounting",
        "event_sequence_reconstruction",
        "clock_and_measurement_normalization",
        "alternative_scenario_analysis",
        "specification_and_observation_comparison",
        "test_or_inspection_method",
        "alternative_cause_analysis",
        "artifact_graph_trace",
        "system_timeline_analysis",
        "gap_and_uncertainty_accounting",
        "synthetic_term_or_workflow_mapping",
        "timeline_reconciliation",
        "abstention_on_unadmitted_authority",
        "source_bounded_review",
        "stated_method",
        "alternative_explanation_accounting",
    }
)
SAFE_EXPERT_LIMITATION_CATEGORIES = (
    "missing_or_unavailable_material",
    "assumption_and_measurement_limits",
    "discipline_scope_boundary",
    "no_legal_or_credibility_conclusion",
)
REQUIRED_EXPERT_FORBIDDEN_CONCLUSIONS = (
    "diagnosis",
    "causation_conclusion",
    "standard_of_care_conclusion",
    "damages_conclusion",
    "credibility_determination",
    "legal_conclusion",
    "compliance_conclusion",
    "outcome_prediction",
    "real_world_prediction",
)
SAFE_MEMORY_PROCESS_IDS = (
    "observation_opportunity",
    "encoding_conditions",
    "elapsed_time",
    "intervening_information",
    "retrieval_confidence",
    "revision_or_correction_history",
)
SAFE_COMMUNICATION_CONTEXT_IDS = (
    "audience_and_purpose",
    "channel_and_thread_context",
    "review_and_approval_process",
    "time_and_attachment_constraints",
)
SAFE_ORGANIZATION_INTERFACE_MECHANISMS = (
    "formal_policy_vs_observed_workflow",
    "handoff_and_escalation_path",
)
SAFE_REVIEW_ESCALATION_PATHS = (
    "role_bounded_review",
    "separate_authority_approval",
    "abstain_and_escalate_outside_domain",
)
SAFE_RETENTION_VERSIONING_PATTERNS = (
    "effective_dated_versions",
    "ordinary_course_retention_variation",
    "correction_without_silent_overwrite",
)
SAFE_AUTHORITY_CATEGORIES = (
    "litigation_workflow_proposal",
    "claim_workflow_proposal",
    "source_bounded_expert_proposal",
    "ordinary_course_record_creation",
)
SAFE_RESOURCE_PRESSURES = (
    "workload_and_staffing",
    "competing_priorities",
    "record_access_and_approval_constraints",
)
SAFE_EXPERT_INDEPENDENCE_CHECK_IDS = (
    "retention_and_compensation_disclosure",
    "conflict_check",
    "materials_list_reconciliation",
    "writer_checker_independence",
)
SAFE_EXPERT_ESCALATION_IDS = ("outside_discipline", "insufficient_source_material")
CANONICAL_DOMAIN_PACK_VALIDATOR_IDS = (
    "validate_design_only_status",
    "validate_design_cross_references",
    "validate_no_active_family_bypass",
    "validate_artifact_lifecycle_dag",
    "validate_role_mechanism_boundary",
    "validate_organization_nonstereotype_boundary",
    "validate_expert_scope_boundary",
    "validate_source_boundary",
    "validate_public_projection",
)


FAMILY_PRESSURES: dict[str, tuple[str, ...]] = {
    "medical_malpractice_design": (
        "patient_care_priority",
        "shift_handoff",
        "charting_delay",
        "multi_system_clinical_timestamps",
        "longitudinal_record_volume",
    ),
    "construction_defect_design": (
        "multi_party_scope_boundaries",
        "long_project_duration",
        "drawing_and_submittal_revision_churn",
        "field_office_information_gap",
        "schedule_and_cost_pressure",
    ),
    "premises_liability_design": (
        "routine_inspection_workload",
        "short_media_retention_window",
        "vendor_handoff",
        "scheduled_versus_completed_ambiguity",
        "scene_change_after_event",
    ),
    "motor_vehicle_design": (
        "rapid_scene_change",
        "multi_device_clock_drift",
        "third_party_record_delay",
        "memory_contamination_after_event",
        "medical_record_lag",
    ),
    "trucking_transportation_design": (
        "dispatch_driver_information_gap",
        "time_zone_and_device_clock_normalization",
        "fleet_record_retention",
        "cargo_and_route_document_duplication",
        "operational_rule_source_not_admitted",
    ),
    "products_liability_design": (
        "model_lot_serial_identity_resolution",
        "design_and_label_revision_churn",
        "batch_sampling_gaps",
        "exemplar_preservation",
        "destructive_test_authority_boundary",
    ),
    "insurance_coverage_bad_faith_design": (
        "coverage_claim_litigation_compartmentation",
        "privilege_and_work_product_partition",
        "authority_tiers",
        "draft_final_correspondence_lineage",
        "jurisdiction_standard_not_admitted",
    ),
    "software_professional_liability_design": (
        "multi_system_clock_normalization",
        "ticket_commit_build_deployment_linkage",
        "restricted_security_records",
        "scope_and_acceptance_change_control",
        "partial_log_retention",
    ),
}


ARTIFACT_OVERRIDES: dict[str, dict[str, tuple[str, ...]]] = {
    "medical_record": {
        "custody": ("late_signature", "late_entry", "partial_export"),
        "version": ("addendum", "corrected_note", "duplicate_printout"),
        "metadata": ("author_id", "encounter_at", "signed_at", "entry_kind", "version_id"),
    },
    "imaging": {
        "custody": ("report_without_study", "accession_mismatch"),
        "version": ("preliminary_final", "addendum"),
        "metadata": ("accession_id", "performed_at", "reported_at", "status", "version_id"),
    },
    "lab": {
        "custody": ("collection_result_interface_delay", "specimen_link_gap"),
        "version": ("preliminary_final", "corrected_result"),
        "metadata": ("order_at", "collected_at", "resulted_at", "status", "version_id"),
    },
    "drawing": {
        "custody": ("sheet_set_gap", "model_render_mismatch"),
        "version": ("issue_register", "revision_cloud", "superseded_sheet"),
        "metadata": ("sheet_id", "discipline", "issued_at", "revision", "status"),
    },
    "rfi": {
        "custody": ("missing_attachment", "unanswered_question"),
        "version": ("response_revision", "reopened_rfi"),
        "metadata": ("rfi_id", "asked_at", "answered_at", "status", "revision"),
    },
    "inspection_log": {
        "custody": ("scheduled_not_completed", "backfill_risk"),
        "version": ("correction", "duplicate_route_export"),
        "metadata": ("area_id", "scheduled_at", "completed_at", "actor_id", "status"),
    },
    "photo_video": {
        "custody": ("clock_offset", "retention_gap", "coverage_gap", "duplicate_angle"),
        "version": ("clip_extraction", "caption_correction"),
        "metadata": ("media_id", "captured_at", "device_id", "location_confidence", "content_hash"),
    },
    "telematics": {
        "custody": ("sensor_clock_drift", "retention_gap", "vehicle_link_mismatch"),
        "version": ("export_version", "normalized_timestamp_revision"),
        "metadata": ("device_id", "vehicle_id", "event_at", "timezone", "export_version"),
    },
    "eld_telematics": {
        "custody": ("device_clock_drift", "missing_interval", "driver_vehicle_link_gap"),
        "version": ("export_version", "annotation_revision"),
        "metadata": ("device_id", "driver_id", "vehicle_id", "event_at", "timezone", "export_version"),
    },
    "exemplar_custody": {
        "custody": ("identity_gap", "pretest_state_gap", "destructive_test_without_authority"),
        "version": ("pretest_posttest_manifest", "custody_transfer"),
        "metadata": ("exemplar_id", "lot_id", "custodian_id", "transfer_at", "state_hash"),
    },
    "policy_endorsement": {
        "custody": ("form_bundle_gap", "delivery_uncertainty"),
        "version": ("endorsement_precedence", "effective_date_conflict"),
        "metadata": ("policy_id", "form_id", "endorsement_id", "effective_at", "version_id"),
    },
    "claim_diary": {
        "custody": ("restricted_body", "concurrent_entry_order"),
        "version": ("correction_flag", "draft_final_entry"),
        "metadata": ("entry_id", "author_id", "created_at", "effective_at", "restriction_class"),
    },
    "deployment": {
        "custody": ("environment_identity_gap", "partial_log_retention", "clock_drift"),
        "version": ("build_deployment_link", "rollback_revision"),
        "metadata": ("environment_id", "build_id", "deployed_at", "status", "log_source"),
    },
    "access_log": {
        "custody": ("clock_source_unknown", "retention_gap", "identity_resolution_gap"),
        "version": ("normalized_export", "parser_revision"),
        "metadata": ("event_id", "actor_ref", "event_at", "timezone", "source_system"),
    },
}


def _intent(key: str) -> ArtifactIntent:
    if key in {"noise"}:
        return "causal_noise"
    if "expert" in key:
        return "expert_scope_record"
    if any(token in key for token in ("contract", "policy", "endorsement", "declarations", "rights")):
        return "contract_record"
    if any(token in key for token in ("litigation", "demand", "proof_of_loss", "coverage_analysis")):
        return "litigation_process_record"
    if any(token in key for token in ("log", "telematics", "dispatch", "deployment", "api", "ticket", "diary", "payment")):
        return "system_record"
    if any(token in key for token in ("drawing", "imaging", "lab", "architecture", "roadway", "specification", "quality", "exemplar")):
        return "technical_record"
    if any(token in key for token in ("incident", "crash", "statement", "photo", "medical_record", "medical_summary")):
        return "event_record"
    return "business_record"


def _channel(key: str, intent: ArtifactIntent) -> str:
    if "photo_video" in key:
        return "media_index"
    if key in {"drawing", "architecture", "imaging"}:
        return "technical_file_index"
    if any(token in key for token in ("log", "telematics", "dispatch", "payment", "schedule", "quality", "batch")):
        return "structured_table"
    if any(token in key for token in ("message", "correspondence", "rfi")):
        return "threaded_message"
    if intent == "contract_record":
        return "versioned_document"
    if intent == "expert_scope_record":
        return "expert_scope_index"
    return "structured_record"


def _lifecycle(key: str, intent: ArtifactIntent) -> tuple[LifecycleKind, LifecycleKind]:
    if intent in {"contract_record", "technical_record"} and not any(
        token in key for token in ("medical_summary", "expert", "photo")
    ):
        return "preincident", "discovery"
    if intent == "event_record":
        return "incident_or_service", "discovery"
    if intent == "expert_scope_record":
        return "discovery", "trial_preparation"
    if intent == "litigation_process_record":
        return "claim_or_pleading", "resolution"
    if intent == "causal_noise":
        return "preincident", "closeout"
    return "incident_or_service", "discovery"


def _role_match(roles: tuple[str, ...], key: str) -> tuple[str, ...]:
    hints = {
        "medical": ("provider", "billing", "patient"),
        "imaging": ("provider", "medical"),
        "lab": ("provider", "medical"),
        "construction": ("contractor", "design", "owner"),
        "drawing": ("design",),
        "rfi": ("contractor", "design"),
        "inspection": ("manager", "vendor", "contractor", "employee"),
        "maintenance": ("manager", "vendor", "fleet", "employee"),
        "weather": ("expert", "employee"),
        "crash": ("driver", "passenger"),
        "dispatch": ("dispatcher", "fleet"),
        "telematics": ("dispatcher", "fleet", "expert"),
        "driver": ("driver", "safety"),
        "cargo": ("cargo", "dispatcher"),
        "product": ("engineer", "manufacturer"),
        "quality": ("quality",),
        "manufacturing": ("quality", "manufacturer"),
        "label": ("engineer", "manufacturer"),
        "policy": ("coverage", "adjuster", "carrier", "broker"),
        "claim": ("adjuster", "carrier", "insured"),
        "payment": ("adjuster", "carrier"),
        "software": ("engineer", "product"),
        "architecture": ("engineer", "software"),
        "api": ("engineer",),
        "ticket": ("engineer", "product", "customer"),
        "deployment": ("engineer",),
        "expert": ("expert",),
        "litigation": ("lawyer", "paralegal"),
        "noise": ("witness", "employee", "manager", "engineer"),
    }
    wanted = tuple(
        role
        for role in roles
        if any(hint in role for token, values in hints.items() if token in key for hint in values)
    )
    if wanted:
        return wanted[:3]
    operational = tuple(role for role in roles if role not in {"lawyer", "paralegal", "carrier"})
    return (operational or roles)[:2]


def _artifact_domains(family: CaseFamilyManifest, key: str) -> tuple[str, ...]:
    matched = tuple(domain for domain in family.fact_domains if any(part in key for part in domain.split("_")))
    return matched or family.fact_domains[: min(3, len(family.fact_domains))]


def _build_artifact(family: CaseFamilyManifest, key: str) -> DesignArtifactFamily:
    intent = _intent(key)
    lifecycle_from, lifecycle_to = _lifecycle(key, intent)
    override = ARTIFACT_OVERRIDES.get(key, {})
    metadata = override.get(
        "metadata",
        ("record_id", "created_at", "author_or_system_id", "version_id", "source_system"),
    )
    custody = override.get(
        "custody",
        ("partial_export", "source_identity_gap", "duplicate_record"),
    )
    versions = override.get(
        "version",
        ("draft_final", "correction", "supersession"),
    )
    roles = _role_match(family.required_roles, key)
    return DesignArtifactFamily(
        artifact_family_id=key,
        label=key.replace("_", " ").title(),
        intent=intent,
        channel_kind=_channel(key, intent),
        author_role_ids=roles,
        recipient_role_ids=("lawyer", "paralegal"),
        fact_domain_ids=_artifact_domains(family, key),
        lifecycle_from=lifecycle_from,
        lifecycle_to=lifecycle_to,
        expected_metadata_keys=tuple(metadata),
        lineage_policy_id="design.version_and_custody_lineage.v1",
        custody_risk_ids=tuple(custody),
        version_risk_ids=tuple(versions),
        causal_noise_sibling_ids=("duplicate", "irrelevant_neighbor", "stale_or_superseded"),
        allowed_synthetic_source_classes=DESIGN_SAFE_SYNTHETIC_SOURCE_CLASSES,
        prohibited_content_classes=COMMON_PROHIBITED_CONTENT,
    )


def _expert_methods(discipline: str) -> tuple[str, ...]:
    if any(token in discipline for token in ("clinical", "medical", "life_care")):
        return ("source_bounded_chronology", "stated_domain_method", "alternative_cause_accounting")
    if any(token in discipline for token in ("reconstruction", "vehicle", "biomechanics", "telematics")):
        return ("event_sequence_reconstruction", "clock_and_measurement_normalization", "alternative_scenario_analysis")
    if any(token in discipline for token in ("architecture", "engineering", "materials", "failure")):
        return ("specification_and_observation_comparison", "test_or_inspection_method", "alternative_cause_analysis")
    if any(token in discipline for token in ("software", "integration", "security", "digital")):
        return ("artifact_graph_trace", "system_timeline_analysis", "gap_and_uncertainty_accounting")
    if any(token in discipline for token in ("coverage", "claims_handling", "insurance")):
        return ("synthetic_term_or_workflow_mapping", "timeline_reconciliation", "abstention_on_unadmitted_authority")
    return ("source_bounded_review", "stated_method", "alternative_explanation_accounting")


def _build_expert(
    family: CaseFamilyManifest,
    discipline: str,
    material_ids: tuple[str, ...],
) -> DesignExpertDiscipline:
    return DesignExpertDiscipline(
        discipline_id=discipline,
        label=discipline.replace("_", " ").title(),
        material_family_ids=material_ids[: max(2, min(6, len(material_ids)))],
        method_categories=_expert_methods(discipline),
        limitation_categories=SAFE_EXPERT_LIMITATION_CATEGORIES,
        independence_check_ids=SAFE_EXPERT_INDEPENDENCE_CHECK_IDS,
        cross_domain_escalation_ids=SAFE_EXPERT_ESCALATION_IDS,
        forbidden_conclusion_ids=REQUIRED_EXPERT_FORBIDDEN_CONCLUSIONS,
        qualification_fixture_id=f"fixture.design-expert.{family.family_id}.{discipline}.v1",
    )


def _role_side(role: str) -> str:
    if role in {"lawyer", "paralegal"}:
        return "defense_firm"
    if role in {"carrier", "adjuster", "claims_supervisor", "coverage_counsel"}:
        return "carrier_claim_organization"
    if "expert" in role:
        return "independent_expert_organization"
    if any(token in role for token in ("patient", "claimant", "passenger", "customer", "insured")):
        return "claimant_or_customer_side"
    return "insured_or_service_organization"


def _build_persona(
    family: CaseFamilyManifest,
    role: str,
    artifacts: tuple[DesignArtifactFamily, ...],
) -> DesignPersonaRole:
    authored = tuple(item.artifact_family_id for item in artifacts if role in item.author_role_ids)
    if role in {"lawyer", "paralegal", "carrier", "adjuster", "claims_supervisor"}:
        knowledge = tuple(item.artifact_family_id for item in artifacts)
    elif "expert" in role:
        knowledge = tuple(
            item.artifact_family_id
            for item in artifacts
            if item.intent not in {"causal_noise", "expert_scope_record"}
        )
    else:
        knowledge = authored or tuple(item.artifact_family_id for item in artifacts[:3])
    authority = (
        "litigation_workflow_proposal"
        if role in {"lawyer", "paralegal"}
        else "claim_workflow_proposal"
        if role in {"carrier", "adjuster", "claims_supervisor"}
        else "source_bounded_expert_proposal"
        if "expert" in role
        else "ordinary_course_record_creation"
    )
    return DesignPersonaRole(
        role_id=role,
        organization_side=_role_side(role),
        authority_categories=(authority,),
        knowledge_artifact_family_ids=knowledge,
        communication_context_ids=SAFE_COMMUNICATION_CONTEXT_IDS,
        memory_process_ids=SAFE_MEMORY_PROCESS_IDS,
        pressure_factor_ids=FAMILY_PRESSURES[family.family_id],
        organization_interface_ids=(
            _role_side(role),
            *SAFE_ORGANIZATION_INTERFACE_MECHANISMS,
        ),
        prohibited_causal_uses=COMMON_PROHIBITED_PERSONA_USES,
    )


def _build_organizations(
    family: CaseFamilyManifest,
    roles: tuple[DesignPersonaRole, ...],
) -> tuple[DesignOrganizationContext, ...]:
    contexts: list[DesignOrganizationContext] = []
    by_side: dict[str, list[str]] = {}
    for role in roles:
        by_side.setdefault(role.organization_side, []).append(role.role_id)
    for side, role_ids in sorted(by_side.items()):
        contexts.append(
            DesignOrganizationContext(
                context_id=side,
                role_ids=tuple(sorted(role_ids)),
                systems_and_records=(
                    f"synthetic_{family.family_id}_record_system",
                    "synthetic_message_and_task_system",
                ),
                workflow_constraints=FAMILY_PRESSURES[family.family_id],
                review_and_escalation_paths=SAFE_REVIEW_ESCALATION_PATHS,
                retention_and_versioning_patterns=SAFE_RETENTION_VERSIONING_PATTERNS,
                incentive_or_resource_pressures=SAFE_RESOURCE_PRESSURES,
                prohibited_person_inferences=COMMON_PROHIBITED_PERSONA_USES,
            )
        )
    return tuple(contexts)


def _lifecycle_stages() -> tuple[DesignLifecycleStage, ...]:
    order: tuple[LifecycleKind, ...] = (
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
    intents: tuple[ArtifactIntent, ...] = (
        "business_record",
        "system_record",
        "contract_record",
        "event_record",
        "technical_record",
        "expert_scope_record",
        "litigation_process_record",
        "causal_noise",
    )
    return tuple(
        DesignLifecycleStage(
            stage_id=stage,
            predecessor_ids=() if index == 0 else (order[index - 1],),
            permitted_artifact_intents=intents,
            permitted_role_actions=(
                "create_bounded_proposal",
                "receive_if_knowledge_granted",
                "review_if_authority_granted",
                "preserve_lineage",
            ),
        )
        for index, stage in enumerate(order)
    )


def build_design_only_domain_pack(
    family: CaseFamilyManifest,
) -> DesignOnlyLitigationDomainPack:
    if family.readiness != "design_only":
        raise ValueError("active_family_cannot_build_design_only_pack")
    if family.family_id not in FAMILY_PRESSURES:
        raise ValueError(f"domain_design_not_defined:{family.family_id}")
    artifacts = tuple(
        _build_artifact(family, key)
        for key in family.required_evidence_capabilities
    )
    material_ids = tuple(
        item.artifact_family_id
        for item in artifacts
        if item.intent not in {"causal_noise", "expert_scope_record"}
    )
    experts = tuple(
        _build_expert(family, discipline, material_ids)
        for discipline in family.expert_domains
    )
    personas = tuple(
        _build_persona(family, role, artifacts)
        for role in family.required_roles
    )
    return DesignOnlyLitigationDomainPack(
        pack_id=f"design-domain-pack.{family.family_id}.v1",
        revision="1",
        contract_revision=DOMAIN_PACK_DESIGN_REVISION,
        case_family_id=family.family_id,
        case_family_manifest_hash=family.manifest_hash,
        status="design_only",
        activation_gate="human_case_family_activation_and_domain_fixture_qualification",
        artifact_families=artifacts,
        expert_disciplines=experts,
        persona_roles=personas,
        organization_contexts=_build_organizations(family, personas),
        lifecycle_stages=_lifecycle_stages(),
        validator_ids=CANONICAL_DOMAIN_PACK_VALIDATOR_IDS,
        source_admission_state="no_sources_admitted",
        learning_state="not_eligible",
        forbidden_source_classes=COMMON_FORBIDDEN_SOURCES,
    )


def build_design_only_domain_packs(
    registry: CapabilityRegistry | None = None,
) -> tuple[DesignOnlyLitigationDomainPack, ...]:
    registry = registry or build_capability_registry()
    return tuple(
        build_design_only_domain_pack(family)
        for family in registry.case_families
        if family.readiness == "design_only"
    )


def domain_pack_design_counts(
    packs: tuple[DesignOnlyLitigationDomainPack, ...],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for pack in packs:
        counts["packs"] += 1
        counts["artifact_families"] += len(pack.artifact_families)
        counts["expert_disciplines"] += len(pack.expert_disciplines)
        counts["persona_roles"] += len(pack.persona_roles)
        counts["organization_contexts"] += len(pack.organization_contexts)
        counts["lifecycle_stages"] += len(pack.lifecycle_stages)
    return dict(sorted(counts.items()))
