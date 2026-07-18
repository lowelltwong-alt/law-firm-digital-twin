from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from .hashio import canonical_json, digest


TECHNOLOGY_ADOPTION_REVISION = "technology-adoption-g2-v2"
AdoptionState = Literal[
    "bounded_adapter_active_g2",
    "approved_reference_mapping",
    "approved_later_local_adapter",
    "approved_later_orchestration_adapter",
    "approved_later_domain_foundation",
    "provider_neutral_component_requirement",
]


@dataclass(frozen=True)
class TechnologyAdoptionContract:
    technology_id: str
    category: str
    official_reference: str
    adoption_state: AdoptionState
    integration_contract_id: str
    intended_uses: tuple[str, ...]
    prohibited_uses: tuple[str, ...]
    qualification_gate_ids: tuple[str, ...]
    activation_gate: str
    dependency_installed: bool = False
    source_code_admitted: bool = False
    source_rows_admitted: Literal[False] = False
    external_access: Literal[False] = False
    runtime_execution: bool = False
    qualified_version: str = ""
    distribution_sha256: str = ""
    license_id: str = ""
    canonical_truth_write: Literal[False] = False
    legal_authority_claimed: Literal[False] = False


@dataclass(frozen=True)
class TechnologyAdoptionCatalog:
    catalog_id: str
    entries: tuple[TechnologyAdoptionContract, ...]
    human_approved_scope: Literal[
        "approved_technology_family_with_only_simpy_bounded_runtime_active"
    ]
    revision: str = TECHNOLOGY_ADOPTION_REVISION

    @property
    def catalog_hash(self) -> str:
        return digest(self)


OFFICIAL_ENTRIES = (
    (
        "simpy",
        "discrete_event_simulation",
        "https://simpy.readthedocs.io/en/stable/index.html",
        "bounded_adapter_active_g2",
        "adapter.simulation_clock.simpy.v1",
        ("deterministic_process_scheduling", "resource_capacity_and_queue_modeling", "manual_event_stepping"),
        ("world_truth_ownership", "unseeded_randomness", "wall_clock_as_canonical_time"),
    ),
    (
        "temporal_python_sdk",
        "durable_orchestration",
        "https://github.com/temporalio/sdk-python",
        "approved_later_orchestration_adapter",
        "adapter.orchestration.temporal_python.v1",
        ("multi_day_campaign_recovery", "activity_heartbeat_and_retry", "durable_checkpoint_orchestration"),
        ("world_kernel_execution", "nondeterministic_workflow_io", "automatic_external_effect_authority"),
    ),
    (
        "edrm_model",
        "ediscovery_reference_model",
        "https://edrm.net/wiki/edrm-model/",
        "approved_reference_mapping",
        "mapping.ediscovery.edrm_conceptual.v1",
        ("iterative_ediscovery_stage_mapping", "coverage_and_gap_analysis", "workflow_taxonomy"),
        ("mandatory_waterfall_claim", "legal_compliance_claim", "case_outcome_authority"),
    ),
    (
        "apache_tika",
        "content_detection_and_extraction",
        "https://tika.apache.org/index.html",
        "approved_later_local_adapter",
        "adapter.extraction.tika.v1",
        ("synthetic_file_type_detection", "metadata_extraction", "text_extraction"),
        ("canonical_metadata_without_receipt", "live_private_ingestion", "silent_parser_fallback"),
    ),
    (
        "tesseract_ocr",
        "ocr",
        "https://github.com/tesseract-ocr/tesseract",
        "approved_later_local_adapter",
        "adapter.ocr.tesseract.v1",
        ("synthetic_scan_ocr", "ocr_confidence_capture", "layout_sidecar_generation"),
        ("ground_truth_substitution", "unqualified_low_confidence_text", "live_private_ingestion"),
    ),
    (
        "sali_lmss",
        "legal_matter_classification",
        "https://sali.org/explore-the-standard/",
        "approved_reference_mapping",
        "mapping.classification.sali_lmss.v1",
        ("matter_and_service_classification", "cross_system_semantic_mapping"),
        ("automatic_legal_conclusion", "unversioned_taxonomy_mapping", "license_assumption"),
    ),
    (
        "ledes_1998b",
        "legal_billing_exchange",
        "https://ledes.org/ledes-98b-format/",
        "approved_reference_mapping",
        "mapping.billing.ledes_1998b.v1",
        ("synthetic_invoice_export_contract", "field_level_round_trip_validation"),
        ("carrier_acceptance_claim", "real_invoice_submission", "lossy_silent_conversion"),
    ),
    (
        "utbms_litigation_codes",
        "legal_billing_taxonomy",
        "https://www.americanbar.org/groups/litigation/resources/uniform-task-based-management-system/",
        "approved_reference_mapping",
        "mapping.billing.utbms_litigation.v1",
        ("synthetic_task_and_activity_classification", "budget_and_invoice_analysis"),
        ("automatic_billing_approval", "legal_success_prediction", "unversioned_code_mapping"),
    ),
    (
        "synthea",
        "synthetic_health_record_generation",
        "https://github.com/synthetichealth/synthea",
        "approved_later_domain_foundation",
        "adapter.medical_generation.synthea.v1",
        ("synthetic_patient_lifecycle_seed", "synthetic_fhir_export", "medical_fixture_foundation"),
        ("real_patient_data", "medico_legal_causation_truth", "credential_or_standard_of_care_claim"),
    ),
    (
        "hl7_fhir_r4",
        "health_record_interchange",
        "https://hl7.org/fhir/R4/diagnosticreport.html",
        "approved_later_domain_foundation",
        "mapping.medical.fhir_r4.v1",
        ("synthetic_resource_graph", "diagnostic_report_and_observation_linkage", "document_reference_versioning"),
        ("clinical_validity_claim", "real_patient_interchange", "unqualified_profile_conformance"),
    ),
)


COMPONENT_REQUIREMENTS = (
    ("graph_reasoning_stack", "graph_reasoning", "internal:provider_neutral_graph_contract", ("artifact_and_fact_graphs", "lineage_and_reachability", "conflict_subgraph_analysis")),
    ("temporal_reasoning_stack", "temporal_reasoning", "internal:provider_neutral_temporal_contract", ("interval_and_event_order_reasoning", "conflicting_timeline_detection", "clock_and_timezone_uncertainty")),
    ("testing_validation_stack", "testing_and_validation", "internal:deterministic_validation_contract", ("property_and_metamorphic_testing", "schema_and_invariant_validation", "hostile_mutation_suites")),
    ("construction_domain_stack", "construction_specialty", "internal:future_construction_adapter_contract", ("schedule_and_change_graphs", "drawing_rfi_submittal_lineage", "allocation_analysis_requirements")),
    ("traffic_reconstruction_stack", "traffic_specialty", "internal:future_traffic_adapter_contract", ("telematics_and_collision_timeline", "roadway_and_vehicle_state", "reconstruction_uncertainty")),
    ("biomechanics_stack", "biomechanics_specialty", "internal:future_biomechanics_adapter_contract", ("bounded_force_and_motion_inputs", "method_and_limitations_records", "cross_domain_escalation")),
)


def build_technology_adoption_catalog() -> TechnologyAdoptionCatalog:
    shared_gates = (
        "license_and_terms_receipt",
        "version_pin_and_sbom",
        "provider_neutral_contract_tests",
        "deterministic_cassette_or_fixture",
        "privacy_and_authority_boundary_tests",
        "independent_validator_review",
        "rollback_and_expiry_triggers",
    )
    entries = [
        TechnologyAdoptionContract(
            technology_id=technology_id,
            category=category,
            official_reference=reference,
            adoption_state=state,  # type: ignore[arg-type]
            integration_contract_id=contract_id,
            intended_uses=intended,
            prohibited_uses=prohibited,
            qualification_gate_ids=shared_gates,
            activation_gate="human_dependency_admission_and_adapter_qualification",
        )
        for technology_id, category, reference, state, contract_id, intended, prohibited in OFFICIAL_ENTRIES
    ]
    entries = [
        replace(
            item,
            activation_gate="bounded_local_schedule_adapter_qualified",
            dependency_installed=True,
            source_code_admitted=True,
            runtime_execution=True,
            qualified_version="4.1.2",
            distribution_sha256="43071f84b6512c9b4fcb33ef057f240ccb1d1f3b263f9b4f9229d072e310b372",
            license_id="MIT",
        )
        if item.technology_id == "simpy"
        else item
        for item in entries
    ]
    entries.extend(
        TechnologyAdoptionContract(
            technology_id=technology_id,
            category=category,
            official_reference=reference,
            adoption_state="provider_neutral_component_requirement",
            integration_contract_id=f"requirement.{technology_id}.v1",
            intended_uses=intended,
            prohibited_uses=(
                "self_qualification",
                "canonical_truth_write",
                "domain_conclusion_without_qualified_adapter",
            ),
            qualification_gate_ids=shared_gates,
            activation_gate="human_component_selection_and_domain_fixture_qualification",
        )
        for technology_id, category, reference, intended in COMPONENT_REQUIREMENTS
    )
    return TechnologyAdoptionCatalog(
        catalog_id="catalog.law_firm_digital_twin.technology_adoption.v1",
        entries=tuple(entries),
        human_approved_scope="approved_technology_family_with_only_simpy_bounded_runtime_active",
    )


def validate_technology_adoption_catalog(
    catalog: TechnologyAdoptionCatalog,
) -> tuple[str, ...]:
    errors: list[str] = []
    expected = build_technology_adoption_catalog()
    if catalog != expected:
        errors.append("TECH-001:catalog_not_canonical")
    ids = tuple(item.technology_id for item in catalog.entries)
    if len(ids) != len(set(ids)):
        errors.append("TECH-002:duplicate_technology")
    if len(catalog.entries) != 16:
        errors.append("TECH-003:technology_coverage_incomplete")
    for item in catalog.entries:
        if item.technology_id == "simpy":
            if not (
                item.dependency_installed
                and item.source_code_admitted
                and item.runtime_execution
                and item.qualified_version == "4.1.2"
                and item.distribution_sha256
                == "43071f84b6512c9b4fcb33ef057f240ccb1d1f3b263f9b4f9229d072e310b372"
                and item.license_id == "MIT"
            ):
                errors.append("TECH-004:simpy:qualified_runtime_record_invalid")
        elif (
            item.dependency_installed
            or item.source_code_admitted
            or item.runtime_execution
            or item.qualified_version
            or item.distribution_sha256
            or item.license_id
        ):
            errors.append(f"TECH-004:{item.technology_id}:unapproved_runtime_activation")
        if (
            item.source_rows_admitted
            or item.external_access
            or item.canonical_truth_write
            or item.legal_authority_claimed
        ):
            errors.append(f"TECH-004:{item.technology_id}:authority_boundary_crossed")
        if len(item.qualification_gate_ids) != 7:
            errors.append(f"TECH-005:{item.technology_id}:qualification_incomplete")
        if not item.intended_uses or not item.prohibited_uses:
            errors.append(f"TECH-006:{item.technology_id}:scope_incomplete")
        text = canonical_json(item).lower()
        if "private_source_row" in text or "real_client_data" in text:
            errors.append(f"TECH-007:{item.technology_id}:private_data_scope")
    return tuple(errors)

