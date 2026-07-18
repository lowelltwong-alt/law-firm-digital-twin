from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from .hashio import digest


Readiness = Literal["active_g2", "design_only", "suspended"]
CapabilityKind = Literal["planner", "generator", "renderer", "checker", "auditor"]
CapabilityClass = Literal["portable_core", "runtime_adapter", "provider_probe"]


@dataclass(frozen=True)
class WeightedBucket:
    bucket_id: str
    weight: int
    description: str
    sealed_label: str


@dataclass(frozen=True)
class PopulationAxis:
    axis_id: str
    purpose: str
    buckets: tuple[WeightedBucket, ...]
    operating_visibility: Literal["commitment_only"] = "commitment_only"

    @property
    def commitment_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class CaseFamilyManifest:
    family_id: str
    revision: str
    label: str
    readiness: Readiness
    fidelity_level: Literal["G0", "G1", "G2"]
    synthetic_only: bool
    fact_domains: tuple[str, ...]
    required_roles: tuple[str, ...]
    required_evidence_capabilities: tuple[str, ...]
    supported_resolution_tracks: tuple[str, ...]
    expert_domains: tuple[str, ...]
    prohibited_capabilities: tuple[str, ...]
    max_roles: int
    max_relationship_edges: int
    max_artifacts: int
    max_versions_per_artifact: int
    activation_gate: str

    @property
    def manifest_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class EvidenceFamilyCapability:
    capability_id: str
    revision: str
    family_id: str
    channel_kind: str
    schema_id: str
    required_fields: tuple[str, ...]
    allowed_native_formats: tuple[str, ...]
    allowed_author_roles: tuple[str, ...]
    recipient_policy_id: str
    custody_policy_id: str
    versioning_policy_id: str
    validator_ids: tuple[str, ...]
    max_per_matter: int
    requires_sender: bool
    requires_recipients: bool
    requires_contract_lineage: bool
    fidelity_level: Literal["G2"]
    prohibited_shortcuts: tuple[str, ...]
    protected_fixture_id: str
    escalation_capability_id: str
    readiness: Readiness


@dataclass(frozen=True)
class PersonaDimensionContract:
    dimension_id: str
    description: str
    allowed_value_kind: str
    time_varying: bool
    operating_visibility: str
    causal_policy: str
    prohibited_uses: tuple[str, ...]


@dataclass(frozen=True)
class SpecialistCapability:
    capability_id: str
    revision: str
    kind: CapabilityKind
    classification: CapabilityClass
    objective: str
    typed_inputs: tuple[str, ...]
    prohibited_inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    errors: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    privacy_class: str
    effect_scope: str
    canonical_truth_write: bool
    dependencies: tuple[str, ...]
    validator_ids: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    qualification_fixture_id: str
    qualification_expiry_triggers: tuple[str, ...]


@dataclass(frozen=True)
class SealedDesignLabel:
    label_id: str
    kind: Literal[
        "designed_conflict",
        "memory_limit",
        "intentional_omission",
        "version_drift",
        "procedural_defect",
        "evidence_direction",
    ]
    protected_fact_ids: tuple[str, ...]
    purpose: str
    evaluator_visibility: Literal["sealed_only"] = "sealed_only"


@dataclass(frozen=True)
class CaseDesignBlueprint:
    design_id: str
    seed: str
    ordinal: int
    case_family_id: str
    sealed_axis_labels: tuple[tuple[str, str], ...]
    design_labels: tuple[SealedDesignLabel, ...]

    @property
    def sealed_commitment_hash(self) -> str:
        return digest(self)

    def operating_view(self) -> dict[str, Any]:
        return {
            "design_id": self.design_id,
            "case_family_id": self.case_family_id,
            "sealed_commitment_hash": self.sealed_commitment_hash,
            "synthetic": True,
        }



def build_case_family_manifests() -> tuple[CaseFamilyManifest, ...]:
    prohibited = (
        "external_retrieval",
        "real_person_or_client_identity",
        "jurisdiction_compliance_claim",
        "g3_native_rendering",
        "oracle_access_by_operating_actor",
    )
    common_tracks = (
        "early_settlement",
        "mediation",
        "dispositive_motion",
        "trial_and_appeal",
        "arbitration_design_only",
    )
    definitions = (
        (
            "employment_defense_g2", "Labor and employment defense", "active_g2",
            ("employment_action", "policy", "attendance", "protected_activity", "damages"),
            ("intake", "conflicts", "lawyer", "paralegal", "docketing", "carrier", "billing", "witness", "expert"),
            ("employment_email", "employment_hr_record", "employment_policy", "employment_payroll", "employment_calendar", "employment_litigation", "employment_expert", "employment_noise"),
            ("organizational_practices", "workplace_investigation"),
        ),
        (
            "medical_malpractice_design", "Medical malpractice defense", "design_only",
            ("standard_of_care", "causation", "clinical_timeline", "damages", "consent"),
            ("lawyer", "paralegal", "carrier", "patient_witness", "provider_witness", "medical_expert", "billing"),
            ("medical_record", "imaging", "lab", "medical_billing", "provider_message", "medical_expert", "litigation", "noise"),
            ("clinical_specialty", "life_care", "medical_billing"),
        ),
        (
            "construction_defect_design", "Construction defect defense", "design_only",
            ("scope", "schedule", "defect", "causation", "allocation", "damages"),
            ("lawyer", "paralegal", "carrier", "owner", "contractor", "subcontractor", "design_professional", "construction_expert"),
            ("contract", "drawing", "rfi", "submittal", "change_order", "inspection", "schedule_log", "construction_expert", "noise"),
            ("architecture", "engineering", "cost", "schedule"),
        ),
        (
            "premises_liability_design", "Premises and slip-fall defense", "design_only",
            ("condition", "notice", "inspection", "causation", "comparative_fault", "damages"),
            ("lawyer", "paralegal", "carrier", "claimant_witness", "employee_witness", "maintenance_vendor", "premises_expert"),
            ("incident_report", "maintenance_log", "inspection_log", "weather", "photo_video", "medical_summary", "premises_expert", "noise"),
            ("safety", "human_factors", "weather"),
        ),
        (
            "motor_vehicle_design", "Motor-vehicle liability defense", "design_only",
            ("collision", "fault", "roadway", "vehicle_condition", "injury", "damages"),
            ("lawyer", "paralegal", "carrier", "driver", "passenger", "dispatcher", "reconstruction_expert"),
            ("crash_report", "dispatch", "telematics", "maintenance", "roadway", "photo_video", "medical_summary", "reconstruction_expert", "noise"),
            ("accident_reconstruction", "biomechanics", "vehicle_systems"),
        ),
        (
            "trucking_transportation_design", "Trucking and transportation defense", "design_only",
            ("collision", "driver_conduct", "dispatch", "hours_of_service", "vehicle_condition", "cargo", "agency", "injury", "damages"),
            ("lawyer", "paralegal", "carrier", "driver", "dispatcher", "fleet_manager", "safety_manager", "cargo_witness", "trucking_expert"),
            ("loss_notice", "crash_report", "driver_statement", "driver_qualification", "eld_telematics", "dispatch", "maintenance", "cargo", "photo_video", "medical_summary", "trucking_expert", "noise"),
            ("accident_reconstruction", "human_factors", "telematics", "vehicle_systems", "trucking_practices"),
        ),
        (
            "products_liability_design", "Products-liability defense", "design_only",
            ("product_identity", "design", "manufacture", "warnings", "distribution", "failure", "causation", "injury", "damages"),
            ("lawyer", "paralegal", "carrier", "product_engineer", "quality_manager", "manufacturer_witness", "distributor_witness", "products_expert"),
            ("product_identity", "label_instructions", "design_specification", "change_control", "manufacturing_batch", "quality_control", "incident_complaint", "field_action", "service_record", "exemplar_custody", "products_expert", "noise"),
            ("mechanical_electrical_materials", "human_factors_warnings", "manufacturing_quality", "failure_analysis", "regulatory_framework"),
        ),
        (
            "insurance_coverage_bad_faith_design", "Insurance coverage and extra-contractual defense", "design_only",
            ("policy_identity", "coverage_terms", "notice", "claim_handling", "investigation", "payment", "delay", "damages"),
            ("lawyer", "paralegal", "carrier", "adjuster", "claims_supervisor", "coverage_counsel", "insured_witness", "broker_witness", "coverage_expert"),
            ("declarations", "policy_endorsement", "claim_notice", "reservation_rights", "coverage_analysis", "claim_diary", "adjuster_correspondence", "proof_of_loss", "investigation_assignment", "payment_record", "coverage_litigation", "coverage_expert", "noise"),
            ("coverage_language", "claims_handling_practices", "insurance_accounting", "operations_timeline", "digital_records"),
        ),
        (
            "software_professional_liability_design", "Software and professional-liability defense", "design_only",
            ("contract_scope", "system_behavior", "integration", "change_control", "security", "damages"),
            ("lawyer", "paralegal", "carrier", "product_owner", "engineer", "customer", "software_expert"),
            ("contract", "architecture", "api", "ticket", "deployment", "access_log", "audit_log", "software_expert", "noise"),
            ("software_architecture", "systems_integration", "security"),
        ),
    )
    manifests: list[CaseFamilyManifest] = []
    for family_id, label, readiness, fact_domains, roles, evidence, experts in definitions:
        manifests.append(
            CaseFamilyManifest(
                family_id=family_id,
                revision="1",
                label=label,
                readiness=readiness,  # type: ignore[arg-type]
                fidelity_level="G2",
                synthetic_only=True,
                fact_domains=fact_domains,
                required_roles=roles,
                required_evidence_capabilities=evidence,
                supported_resolution_tracks=common_tracks,
                expert_domains=experts,
                prohibited_capabilities=prohibited,
                max_roles=24,
                max_relationship_edges=72,
                max_artifacts=250,
                max_versions_per_artifact=5,
                activation_gate=(
                    "existing_g2_compatibility"
                    if readiness == "active_g2"
                    else "human_case_family_activation_and_domain_fixture_qualification"
                ),
            )
        )
    return tuple(manifests)


def build_evidence_capabilities() -> tuple[EvidenceFamilyCapability, ...]:
    definitions = (
        ("employment_email", "email", ("author_id", "recipient_ids", "subject", "body", "sent_at"), True, True, False),
        ("employment_hr_record", "hris_record", ("employee_id", "record_type", "effective_at", "content"), True, False, False),
        ("employment_policy", "policy_document", ("policy_id", "version_id", "effective_at", "content"), True, False, True),
        ("employment_payroll", "structured_table", ("employee_id", "period", "amount_or_hours", "source_system"), False, False, False),
        ("employment_calendar", "calendar", ("organizer_id", "invitees", "starts_at", "attendance_status"), True, True, False),
        ("employment_litigation", "litigation_record", ("document_type", "author_id", "created_at", "fact_claim_ids"), True, True, False),
        ("employment_expert", "expert_record", ("expert_id", "materials_considered", "method", "limitations", "opinion"), True, True, False),
        ("employment_noise", "irrelevant_record", ("author_id", "created_at", "content", "nonresponsive_basis"), True, False, False),
    )
    capabilities: list[EvidenceFamilyCapability] = []
    author_roles = {
        "employment_email": ("manager", "witness"),
        "employment_hr_record": ("manager", "witness"),
        "employment_policy": ("manager", "witness"),
        "employment_payroll": ("billing",),
        "employment_calendar": ("manager", "witness"),
        "employment_litigation": ("intake",),
        "employment_expert": ("expert",),
        "employment_noise": ("manager", "witness"),
    }
    for family_id, channel, required, sender, recipients, lineage in definitions:
        capabilities.append(
            EvidenceFamilyCapability(
                capability_id=f"evidence.{family_id}.v1",
                revision="1",
                family_id=family_id,
                channel_kind=channel,
                schema_id=f"schema.{family_id}.v1",
                required_fields=required,
                allowed_native_formats=("text/plain", "application/json", "text/csv"),
                allowed_author_roles=author_roles[family_id],
                recipient_policy_id="case_scoped_relationship_grant.v1",
                custody_policy_id="custody.synthetic_hash_stable.v1",
                versioning_policy_id=(
                    "version.parent_required.v1" if lineage else "version.optional_supersession.v1"
                ),
                validator_ids=(
                    "validate_fact_allowlist",
                    "validate_knowledge_frontier",
                    "validate_timeline_and_version_graph",
                    "validate_custody_and_hashes",
                    "validate_nonplaceholder",
                ),
                max_per_matter=80 if family_id == "employment_email" else 30,
                requires_sender=sender,
                requires_recipients=recipients,
                requires_contract_lineage=lineage,
                fidelity_level="G2",
                prohibited_shortcuts=(
                    "oracle_paraphrase",
                    "random_typo_only_variation",
                    "placeholder_body",
                    "same_voice_for_all_authors",
                    "untracked_copy_from_public_or_private_source",
                ),
                protected_fixture_id=f"fixture.{family_id}.g2.v1",
                escalation_capability_id="specialist.domain_plausibility_checker.v1",
                readiness="active_g2",
            )
        )
    return tuple(capabilities)


def build_population_axes() -> tuple[PopulationAxis, ...]:
    def axis(axis_id: str, purpose: str, values: tuple[tuple[str, int, str], ...]) -> PopulationAxis:
        return PopulationAxis(
            axis_id=axis_id,
            purpose=purpose,
            buckets=tuple(
                WeightedBucket(bucket_id, weight, description, f"sealed:{axis_id}:{bucket_id}")
                for bucket_id, weight, description in values
            ),
        )

    return (
        axis("merits_posture", "Vary legal/factual strength without making every defense case favorable.", (
            ("defense_favorable", 30, "Record materially favors the defense."),
            ("claimant_favorable", 30, "Record materially favors the claimant."),
            ("balanced", 30, "Reasonable fact-finders could divide."),
            ("deeply_ambiguous", 10, "Key proof is incomplete or credibility dependent."),
        )),
        axis("evidence_shape", "Control direction, noise, missingness, and conflict density.", (
            ("directional_defense", 15, "Evidence points mostly toward the defense."),
            ("directional_claimant", 15, "Evidence points mostly toward the claimant."),
            ("mixed_conflicting", 40, "Material evidence conflicts across sources."),
            ("noisy_redundant", 20, "Large irrelevant and duplicate volume surrounds useful proof."),
            ("sparse_or_corrupted", 10, "Important evidence is missing, damaged, or uncertain."),
        )),
        axis("procedural_quality", "Include uncommon but real procedural defects without dominating the corpus.", (
            ("merits_progressing", 82, "Case proceeds on ordinary merits track."),
            ("curable_defect", 6, "A correctable pleading or service defect exists."),
            ("dismissal_without_prejudice", 4, "A defect supports dismissal without prejudice."),
            ("dismissal_with_prejudice", 3, "A rare terminal defect is intentionally designed."),
            ("technical_dispute", 5, "A technical procedural dispute changes cost or timing."),
        )),
        axis("representation_quality", "Vary client and counsel execution rather than assuming perfect defense work.", (
            ("well_handled", 55, "The defense team and client generally perform well."),
            ("uneven", 25, "Ordinary mistakes and delays complicate the defense."),
            ("material_error", 15, "A client or legal-team error creates an uphill problem."),
            ("systemic_failure", 5, "Multiple failures substantially impair the defense."),
        )),
        axis("resolution_track", "Exercise settlement, ADR, motions, trial, and appeal paths.", (
            ("settlement", 28, "Negotiated settlement."),
            ("mediation", 20, "Mediation resolves or reaches impasse."),
            ("dispositive_motion", 18, "A dispositive motion materially resolves the matter."),
            ("trial", 17, "The matter reaches trial."),
            ("trial_and_appeal", 7, "Judgment is followed by appeal."),
            ("arbitration", 10, "A design-only arbitration track requiring activation."),
        )),
    )

@dataclass(frozen=True)
class CapabilityRegistry:
    revision: str
    case_families: tuple[CaseFamilyManifest, ...]
    evidence_capabilities: tuple[EvidenceFamilyCapability, ...]
    persona_dimensions: tuple[PersonaDimensionContract, ...]
    specialist_capabilities: tuple[SpecialistCapability, ...]
    population_axes: tuple[PopulationAxis, ...]

    @property
    def registry_hash(self) -> str:
        return digest(asdict(self))


def build_persona_dimension_contracts() -> tuple[PersonaDimensionContract, ...]:
    definitions = (
        ("synthetic_background", "Non-identifying life and work context.", "bounded_text", False),
        ("education_and_training", "Education, credentials, and on-the-job learning.", "typed_history", True),
        ("profession_and_seniority", "Role, profession, tenure, and decision scope.", "typed_history", True),
        ("economic_and_social_constraints", "Workload, schedule, resources, and non-protected constraints.", "bounded_state", True),
        ("language_and_code_switching", "Languages, registers, and audience-specific switching.", "bounded_profile", True),
        ("goals_fears_loyalties", "Competing incentives and loyalties at a point in time.", "weighted_state", True),
        ("relationships_and_power_distance", "Directed relationship, trust, conflict, and authority edges.", "graph_edges", True),
        ("attention_and_detail", "Attention allocation, planning, and detail orientation.", "bounded_state", True),
        ("memory_process", "Perception, encoding, interference, retrieval, confidence, and disclosure.", "staged_process", True),
        ("risk_directness_and_revision", "Risk tolerance, directness, hedging, and revision habits.", "bounded_profile", True),
        ("stress_fatigue_and_workload", "Time-local pressure affecting but not determining behavior.", "time_series", True),
        ("channel_and_tool_habits", "Channel choice, device, latency, attachments, and correction habits.", "bounded_profile", True),
        ("accessibility_needs", "Synthetic accessibility constraints relevant to channels and artifacts.", "bounded_profile", True),
        ("knowledge_frontier", "Facts perceived or learned by the actor at each time.", "temporal_fact_set", True),
        ("change_over_time", "Revisioned state transitions rather than a fixed personality label.", "event_series", True),
    )
    return tuple(
        PersonaDimensionContract(
            dimension_id=dimension_id,
            description=description,
            allowed_value_kind=value_kind,
            time_varying=time_varying,
            operating_visibility="actor_projection_only",
            causal_policy=(
                "probabilistic_contextual_influence_only; never a deterministic proxy for intelligence, "
                "credibility, grammar, competence, protected class, liability, or outcome"
            ),
            prohibited_uses=(
                "mbti_as_validated_cause",
                "left_right_brain_claim",
                "protected_attribute_outcome_rule",
                "education_equals_intelligence",
                "class_determines_grammar",
                "profession_determines_voice",
                "diagnosis_without_authority",
            ),
        )
        for dimension_id, description, value_kind, time_varying in definitions
    )


def build_specialist_capabilities() -> tuple[SpecialistCapability, ...]:
    prohibited = (
        "oracle_truth",
        "hidden_design_labels",
        "cross_case_artifacts",
        "private_source_rows",
        "unadmitted_legal_rules",
        "credentials_or_secrets",
    )
    errors = (
        "stale_snapshot",
        "prohibited_input",
        "unsupported_domain",
        "schema_invalid",
        "deterministic_gate_failure",
        "qualification_missing",
        "authority_boundary",
    )
    stops = (
        "truth_boundary",
        "privacy_boundary",
        "source_not_admitted",
        "qualification_expired",
        "repeated_failure",
        "validation_inconclusive",
    )
    expiry = (
        "core_contract_change",
        "runtime_adapter_change",
        "schema_change",
        "persona_or_organization_pack_change",
        "validator_change",
        "privacy_or_authority_change",
    )

    def capability(
        capability_id: str,
        kind: CapabilityKind,
        classification: CapabilityClass,
        objective: str,
        inputs: tuple[str, ...],
        outputs: tuple[str, ...],
        validators: tuple[str, ...],
        *,
        effect_scope: str = "proposal_only",
        dependencies: tuple[str, ...] = (),
    ) -> SpecialistCapability:
        return SpecialistCapability(
            capability_id=capability_id,
            revision="1",
            kind=kind,
            classification=classification,
            objective=objective,
            typed_inputs=(
                "case_snapshot_hash",
                "knowledge_frontier_id",
                "authority_frontier_id",
                "seed_stream_id",
                *inputs,
            ),
            prohibited_inputs=prohibited,
            outputs=outputs,
            errors=errors,
            allowed_tools=("repository_read", "typed_manifest_io", "deterministic_validator"),
            privacy_class="synthetic_only",
            effect_scope=effect_scope,
            canonical_truth_write=False,
            dependencies=dependencies,
            validator_ids=validators,
            stop_conditions=stops,
            qualification_fixture_id=f"fixture.{capability_id}.v1",
            qualification_expiry_triggers=expiry,
        )

    return (
        capability("specialist.world_causality_architect.v1", "planner", "portable_core", "Propose a sealed causal world for kernel admission.", ("case_family_manifest_hash", "population_blueprint_commitment"), ("staged_world_proposal", "lineage_receipt"), ("validate_world_schema", "validate_no_oracle_projection")),
        capability("specialist.case_type_evidence_architect.v1", "planner", "portable_core", "Declare why each evidence artifact exists and what projection may generate it.", ("case_family_manifest_hash", "evidence_capability_ids"), ("evidence_plan", "discoverability_plan"), ("validate_capability_coverage", "validate_complexity_budget")),
        capability("specialist.persona_relationship_architect.v1", "planner", "portable_core", "Build time-varying persona and relationship proposals without stereotypes.", ("persona_dimension_contract_ids", "organization_state_id"), ("persona_state_proposals", "relationship_graph"), ("validate_persona_dimensions", "validate_stereotype_boundary")),
        capability("specialist.organization_culture_modeler.v1", "planner", "portable_core", "Model formal policies, practiced norms, systems, incentives, silos, and subcultures.", ("organization_profile_id",), ("organization_state", "culture_constraints"), ("validate_organization_state",)),
        capability("specialist.employment_intake_record_writer.v1", "generator", "portable_core", "Stage synthetic employment-defense intake and litigation records from a bounded artifact projection.", ("artifact_contract_id", "renderer_persona_view_commitment", "allowed_assertion_ids"), ("staged_litigation_record_proposal", "assertion_set"), ("validate_fact_allowlist", "validate_family_schema", "validate_nonplaceholder")),
        capability("specialist.employment_business_record_writer.v1", "generator", "portable_core", "Stage synthetic employment emails, HRIS records, payroll summaries, calendars, and nonresponsive business records from bounded projections.", ("artifact_contract_id", "renderer_persona_view_commitment", "allowed_assertion_ids"), ("staged_business_record_proposal", "assertion_set"), ("validate_fact_allowlist", "validate_family_schema", "validate_native_metadata", "validate_nonplaceholder")),
        capability("specialist.channel_native_planner.v1", "planner", "portable_core", "Plan channel structure and G2 native metadata.", ("channel_contract_id", "persona_state_ids"), ("channel_plan", "native_metadata_plan"), ("validate_channel_permissions", "validate_native_metadata")),
        capability("specialist.contract_policy_specialist.v1", "generator", "portable_core", "Stage synthetic agreements, amendments, policies, and version lineage.", ("artifact_contract_id", "allowed_fact_ids"), ("staged_contract_record", "assertion_set", "lineage_receipt"), ("validate_contract_lineage", "validate_fact_allowlist")),
        capability("specialist.expert_witness_builder.v1", "generator", "portable_core", "Stage source-bounded expert methods, materials, limitations, and opinions.", ("expert_domain_id", "authorized_artifact_ids"), ("staged_expert_record", "source_boundary_receipt"), ("validate_expert_source_boundary", "validate_expert_independence")),
        capability("specialist.billing_lifecycle_architect.v1", "planner", "portable_core", "Plan time, invoice, reduction, appeal, payment, and write-off events.", ("guideline_contract_id", "work_event_ids"), ("billing_event_plan", "finance_invariant_plan"), ("validate_finance_invariants",)),
        capability("specialist.noise_imperfection_planner.v1", "planner", "portable_core", "Plan causal irrelevant, duplicate, missing, stale, corrected, or corrupted material.", ("evidence_shape_label_commitment", "evidence_plan_id"), ("noise_plan", "imperfection_lineage"), ("validate_noise_nonleakage", "validate_noise_ratio")),
        capability("specialist.declared_conflict_controller.v1", "planner", "portable_core", "Seed evaluation-only conflicts without exposing their labels to writers.", ("protected_fact_ids", "conflict_kind"), ("sealed_conflict_commitment", "projection_allowlists"), ("validate_design_label_nonleakage",)),
        capability("adapter.artifact_renderer.v1", "renderer", "runtime_adapter", "Render one staged artifact from a bounded projection without changing facts.", ("artifact_contract_id", "persona_state_ids", "channel_contract_id"), ("staged_artifact", "assertion_set", "native_metadata", "lineage_receipt"), ("validate_fact_allowlist", "validate_nonplaceholder", "validate_native_metadata"), dependencies=("specialist.case_type_evidence_architect.v1",)),
        capability("specialist.continuity_custody_checker.v1", "checker", "portable_core", "Check chronology, versions, lineage, references, hashes, and custody.", ("staged_artifact_ids",), ("continuity_findings", "custody_findings"), ("validate_timeline_and_version_graph", "validate_custody_and_hashes"), effect_scope="evaluation_only"),
        capability("specialist.domain_plausibility_checker.v1", "checker", "portable_core", "Check bounded domain plausibility without issuing legal or medical conclusions.", ("domain_pack_id", "staged_artifact_ids"), ("plausibility_findings", "abstentions"), ("validate_domain_scope",), effect_scope="evaluation_only"),
        capability("specialist.voice_representation_checker.v1", "checker", "portable_core", "Detect voice collapse, template concentration, caricature, and stereotype risk.", ("persona_state_ids", "staged_artifact_ids"), ("voice_findings", "representation_findings"), ("validate_voice_corpus", "validate_stereotype_boundary"), effect_scope="evaluation_only"),
        capability("specialist.document_fidelity_checker.v1", "checker", "portable_core", "Check schema, metadata, substantive density, and non-placeholder fidelity at G2.", ("evidence_capability_id", "staged_artifact_ids"), ("fidelity_findings",), ("validate_nonplaceholder", "validate_family_schema"), effect_scope="evaluation_only"),
        capability("specialist.whole_case_auditor.v1", "auditor", "portable_core", "Run Berean-style whole-case conflict, boundary, and continuity audit.", ("operating_projection_hash", "evaluation_projection_hash"), ("whole_case_audit",), ("validate_projection_separation", "validate_cross_artifact_consistency"), effect_scope="evaluation_only"),
        capability("specialist.population_designer.v1", "planner", "portable_core", "Allocate bounded varied case-design labels deterministically.", ("population_axis_commitments", "matter_count"), ("sealed_population_blueprints", "distribution_receipt"), ("validate_population_bounds", "validate_cross_matter_isolation")),
        capability("probe.runtime_qualification.v1", "checker", "provider_probe", "Qualify a runtime adapter against revision-bound protected fixtures.", ("core_revision", "adapter_revision", "fixture_ids"), ("qualification_receipt", "failure_receipts"), ("validate_qualification_receipt",), effect_scope="evaluation_only"),
    )


def _allocate_axis(axis: PopulationAxis, seed: str, count: int) -> tuple[str, ...]:
    if count < 1:
        raise ValueError("population count must be positive")
    if sum(bucket.weight for bucket in axis.buckets) != 100:
        raise ValueError(f"population axis {axis.axis_id} must total 100")
    allocations = {bucket.bucket_id: count * bucket.weight // 100 for bucket in axis.buckets}
    remaining = count - sum(allocations.values())
    remainder_order = sorted(
        axis.buckets,
        key=lambda bucket: (
            -(count * bucket.weight % 100),
            digest({"seed": seed, "axis": axis.axis_id, "bucket": bucket.bucket_id}),
        ),
    )
    for bucket in remainder_order[:remaining]:
        allocations[bucket.bucket_id] += 1
    tokens: list[tuple[str, str]] = []
    for bucket in axis.buckets:
        for index in range(allocations[bucket.bucket_id]):
            token_hash = digest(
                {
                    "seed": seed,
                    "axis": axis.axis_id,
                    "bucket": bucket.bucket_id,
                    "occurrence": index,
                }
            )
            tokens.append((token_hash, bucket.bucket_id))
    return tuple(bucket_id for _, bucket_id in sorted(tokens))


def build_population_blueprints(
    seed: str,
    count: int,
    *,
    case_family_id: str = "employment_defense_g2",
) -> tuple[CaseDesignBlueprint, ...]:
    families = {item.family_id: item for item in build_case_family_manifests()}
    family = families.get(case_family_id)
    if family is None:
        raise ValueError(f"unknown case family: {case_family_id}")
    if family.readiness != "active_g2":
        raise ValueError(
            f"case family is design-only and cannot generate blueprints: {case_family_id}"
        )

    axes = build_population_axes()
    assignments = {axis.axis_id: _allocate_axis(axis, seed, count) for axis in axes}
    blueprints: list[CaseDesignBlueprint] = []
    for ordinal in range(count):
        axis_labels = tuple((axis.axis_id, assignments[axis.axis_id][ordinal]) for axis in axes)
        labels: list[SealedDesignLabel] = []
        selected = dict(axis_labels)
        labels.append(
            SealedDesignLabel(
                label_id=f"LBL-{ordinal:06d}-MERITS",
                kind="evidence_direction",
                protected_fact_ids=("case_merits_posture",),
                purpose=f"Authorial target for {selected['merits_posture']} evidence balance.",
            )
        )
        if selected["evidence_shape"] == "mixed_conflicting":
            labels.append(SealedDesignLabel(f"LBL-{ordinal:06d}-CONFLICT", "designed_conflict", ("material_conflict",), "Require independently detectable incompatible evidence."))
        if selected["evidence_shape"] == "sparse_or_corrupted":
            labels.append(SealedDesignLabel(f"LBL-{ordinal:06d}-OMISSION", "intentional_omission", ("missing_evidence",), "Require bounded missing or corrupted evidence with lineage."))
        if selected["procedural_quality"] != "merits_progressing":
            labels.append(SealedDesignLabel(f"LBL-{ordinal:06d}-PROCEDURE", "procedural_defect", ("procedural_posture",), "Exercise an uncommon procedural issue without dominating the corpus."))
        blueprints.append(
            CaseDesignBlueprint(
                design_id=f"DESIGN-{digest({'seed': seed, 'ordinal': ordinal})[:16]}",
                seed=seed,
                ordinal=ordinal,
                case_family_id=case_family_id,
                sealed_axis_labels=axis_labels,
                design_labels=tuple(labels),
            )
        )
    return tuple(blueprints)


def build_capability_registry() -> CapabilityRegistry:
    return CapabilityRegistry(
        revision="law-firm-digital-twin-capability-registry-v1",
        case_families=build_case_family_manifests(),
        evidence_capabilities=build_evidence_capabilities(),
        persona_dimensions=build_persona_dimension_contracts(),
        specialist_capabilities=build_specialist_capabilities(),
        population_axes=build_population_axes(),
    )

