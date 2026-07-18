from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from law_firm_digital_twin.case_compiler import (
    compile_population_fixture,
    qualify_case_compilation,
)
from law_firm_digital_twin.employment_lifecycle_catalog import (
    build_employment_lifecycle_document_catalog,
)
from law_firm_digital_twin.hashio import canonical_json
from law_firm_digital_twin.litigation_lifecycle_validator import (
    validate_lifecycle_catalog,
    validate_public_dossier_catalog_summary,
    validate_qualified_matter_dossier_blueprint,
)
from law_firm_digital_twin.matter_dossier_planner import (
    QualifiedDossierSummaryInput,
    build_public_dossier_catalog_summary,
    build_qualified_matter_dossier_blueprint,
)
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack


@pytest.fixture(scope="module")
def qualified_population():
    compilations = compile_population_fixture(
        seed="employment-lifecycle-dossier-v1",
        count=5,
        rule_pack=placeholder_data_first_rule_pack(),
    )
    return tuple(
        (item, qualify_case_compilation(item)) for item in compilations
    )


def _codes(report) -> set[str]:
    return {item.code for item in report.findings}


def _summary_inputs(qualified_population):
    return tuple(
        QualifiedDossierSummaryInput(
            compilation=compilation,
            qualification_receipt=receipt,
            blueprint=build_qualified_matter_dossier_blueprint(
                compilation,
                receipt,
            ),
        )
        for compilation, receipt in qualified_population
    )


def test_catalog_is_comprehensive_deterministic_and_nonexecuting() -> None:
    first = build_employment_lifecycle_document_catalog()
    second = build_employment_lifecycle_document_catalog()
    report = validate_lifecycle_catalog(first)
    assert first == second
    assert first.catalog_hash == second.catalog_hash
    assert report.passed, report.findings
    assert len(first.stages) == 16
    assert len(first.document_types) == 176
    assert {item.branch_scope for item in first.document_types} == {
        "universal",
        "motion",
        "settlement",
        "mediation",
        "administrative_agency_design_only",
        "arbitration_design_only",
        "trial",
        "appeal",
    }
    assert all(not item.body_included for item in first.document_types)
    assert all(not item.runtime_execution for item in first.document_types)
    assert all(not item.legal_compliance_claimed for item in first.document_types)
    assert all(not item.native_fidelity_claimed for item in first.document_types)
    assert all(
        value.startswith("deferred.kernel_adapter_unimplemented.")
        for item in first.document_types
        for value in item.activation_event_ids
    )


def test_catalog_covers_experts_ediscovery_finance_and_all_resolution_branches() -> None:
    catalog = build_employment_lifecycle_document_catalog()
    ids = {item.document_type_id for item in catalog.document_types}
    assert {
        "custodian_map",
        "responsiveness_privilege_decision_log",
        "production_manifest",
        "deposition_transcript_surrogate",
        "testimony_conflict_update",
        "expert_method_and_limitations_record",
        "expert_independence_counsel_verification",
        "administrative_agency_position_response_surrogate",
        "leave_accommodation_record_surrogate",
        "expert_report_surrogate",
        "settlement_authority_record",
        "mediation_impasse_record",
        "arbitration_award_surrogate",
        "verdict_and_judgment_surrogate",
        "appellate_decision_surrogate",
        "billing_reduction_record",
        "billing_appeal",
        "billing_appeal_decision",
        "cash_application_record",
        "write_off_record",
        "finance_reconciliation",
    }.issubset(ids)


def test_qualified_blueprint_binds_case_but_contains_no_bodies_or_selected_route(
    qualified_population,
) -> None:
    compilation, receipt = qualified_population[0]
    blueprint = build_qualified_matter_dossier_blueprint(compilation, receipt)
    report = validate_qualified_matter_dossier_blueprint(
        blueprint,
        compilation,
        receipt,
    )
    assert report.passed, report.findings
    assert len(blueprint.nodes) == 176
    assert blueprint.future_branches_active is False
    assert blueprint.branch_activation_authority == "future_kernel_event_adapter_required"
    assert all(not item.body_included for item in blueprint.nodes)
    assert all(
        item.activation_state == "inactive_pending_kernel_event"
        for item in blueprint.nodes
        if item.branch_scope != "universal"
    )
    operating_text = canonical_json(blueprint).lower()
    for forbidden in (
        "resolution_track",
        "resolution_outcome",
        "target_posture",
        "evaluator_case_id",
        "world_namespace",
        "matter_namespace",
        "oracle",
    ):
        assert forbidden not in operating_text


def test_future_branch_activation_is_rejected(qualified_population) -> None:
    compilation, receipt = qualified_population[0]
    blueprint = build_qualified_matter_dossier_blueprint(compilation, receipt)
    index = next(
        index
        for index, item in enumerate(blueprint.nodes)
        if item.branch_scope == "trial"
    )
    attacked = replace(blueprint.nodes[index], activation_state="planning_only")
    nodes = list(blueprint.nodes)
    nodes[index] = attacked
    report = validate_qualified_matter_dossier_blueprint(
        replace(blueprint, nodes=tuple(nodes)),
        compilation,
        receipt,
    )
    assert "DLP-008" in _codes(report)
    assert not report.passed


def test_cycle_and_unknown_dependency_are_rejected(qualified_population) -> None:
    compilation, receipt = qualified_population[0]
    blueprint = build_qualified_matter_dossier_blueprint(compilation, receipt)
    first, second = blueprint.nodes[:2]
    attacked_first = replace(first, prerequisite_node_ids=(second.node_id,))
    nodes = (attacked_first, *blueprint.nodes[1:])
    cycle_report = validate_qualified_matter_dossier_blueprint(
        replace(blueprint, nodes=nodes),
        compilation,
        receipt,
    )
    assert "DLP-012" in _codes(cycle_report)

    attacked_second = replace(second, prerequisite_node_ids=("DNODE-UNKNOWN",))
    nodes = (first, attacked_second, *blueprint.nodes[2:])
    unknown_report = validate_qualified_matter_dossier_blueprint(
        replace(blueprint, nodes=nodes),
        compilation,
        receipt,
    )
    assert "DLP-012" in _codes(unknown_report)


def test_cross_case_receipt_and_graph_transplant_fail_closed(qualified_population) -> None:
    compilation_a, receipt_a = qualified_population[0]
    compilation_b, receipt_b = qualified_population[1]
    blueprint_a = build_qualified_matter_dossier_blueprint(compilation_a, receipt_a)
    with pytest.raises(ValueError, match="case_qualification_receipt_invalid"):
        build_qualified_matter_dossier_blueprint(compilation_a, receipt_b)
    report = validate_qualified_matter_dossier_blueprint(
        blueprint_a,
        compilation_b,
        receipt_b,
    )
    assert {"DLP-003", "DLP-015"}.issubset(_codes(report))


def test_sealed_route_tamper_cannot_cross_qualification_boundary(
    qualified_population,
) -> None:
    compilation, receipt = qualified_population[0]
    replacement = (
        "trial_and_appeal"
        if compilation.sealed.resolution_track != "trial_and_appeal"
        else "early_settlement"
    )
    attacked = replace(
        compilation,
        sealed=replace(compilation.sealed, resolution_track=replacement),
    )
    with pytest.raises(ValueError, match="case_qualification_receipt_invalid"):
        build_qualified_matter_dossier_blueprint(attacked, receipt)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("legal_compliance_claimed", True),
        ("native_fidelity_claimed", True),
        ("runtime_execution", True),
        ("bodies_included", True),
        ("future_branches_active", True),
        ("source_admission_state", "live_sources_admitted"),
        ("rule_admission_state", "court_rules_admitted"),
    ),
)
def test_authority_and_fidelity_claims_are_rejected(
    qualified_population,
    field,
    value,
) -> None:
    compilation, receipt = qualified_population[0]
    blueprint = build_qualified_matter_dossier_blueprint(compilation, receipt)
    attacked = replace(blueprint, **{field: value})
    report = validate_qualified_matter_dossier_blueprint(
        attacked,
        compilation,
        receipt,
    )
    assert "DLP-004" in _codes(report)


def test_catalog_rejects_unsafe_source_stereotype_and_self_activation() -> None:
    catalog = build_employment_lifecycle_document_catalog()
    first = catalog.document_types[0]
    attacks = (
        replace(first, source_class="enron_raw_email"),
        replace(first, label="MBTI determines credibility"),
        replace(first, activation_event_ids=("writer.self_approved",)),
    )
    expected_codes = ({"DLC-001", "DLC-017", "DLC-020"}, {"DLC-001", "DLC-020"}, {"DLC-001", "DLC-019"})
    for attacked, codes in zip(attacks, expected_codes):
        report = validate_lifecycle_catalog(
            replace(catalog, document_types=(attacked, *catalog.document_types[1:]))
        )
        assert codes.issubset(_codes(report))


def test_billing_chain_is_ordered_and_resolution_independent() -> None:
    catalog = build_employment_lifecycle_document_catalog()
    by_id = {item.document_type_id: item for item in catalog.document_types}
    chain = (
        "work_event_record",
        "time_entry",
        "expense_entry",
        "prebill_review_record",
        "invoice",
        "carrier_audit_notice",
        "billing_reduction_record",
        "billing_appeal_assessment",
        "billing_appeal",
        "billing_appeal_decision",
        "revised_invoice",
        "payment_advice",
        "cash_application_record",
        "write_off_record",
        "ar_aging_record",
        "finance_reconciliation",
        "final_invoice_record",
    )
    for previous, current in zip(chain, chain[1:]):
        assert by_id[current].prerequisite_type_ids == (previous,)
    assert all(by_id[item].branch_scope == "universal" for item in chain)
    assert by_id["settlement_evaluation"].prerequisite_type_ids == ("early_case_evaluation",)
    assert by_id["mediation_authority_request"].branch_scope == "mediation"
    assert by_id["motion_issue_assessment"].prerequisite_type_ids == ("expert_report_surrogate",)
    assert by_id["trial_witness_list"].branch_scope == "trial"
    assert by_id["administrative_agency_charge_or_notice_index"].branch_scope == "administrative_agency_design_only"


def test_public_summary_is_aggregate_only_and_has_small_cell_gate(
    qualified_population,
) -> None:
    qualified_inputs = _summary_inputs(qualified_population)
    with pytest.raises(ValueError, match="public_summary_small_cell_forbidden"):
        build_public_dossier_catalog_summary(qualified_inputs[:4])
    summary = build_public_dossier_catalog_summary(qualified_inputs)
    report = validate_public_dossier_catalog_summary(summary, qualified_inputs)
    assert report.passed, report.findings
    assert summary.planning_blueprint_count == 5
    assert summary.document_type_count == 176
    public_text = canonical_json(summary).lower()
    for forbidden in (
        "matter_namespace",
        "world_namespace",
        "evaluator_case_id",
        "resolution_track",
        "document_body",
        "actor_id",
        "persona",
    ):
        assert forbidden not in public_text



def test_checked_in_public_summary_matches_builder(qualified_population) -> None:
    qualified_inputs = _summary_inputs(qualified_population)
    expected = build_public_dossier_catalog_summary(qualified_inputs)
    path = (
        Path(__file__).resolve().parents[1]
        / "generated"
        / "g2-employment-dossier-plan-v1"
        / "catalog_summary.json"
    )
    observed = json.loads(path.read_text(encoding="utf-8"))
    assert observed["lifecycle_stage_count"] == expected.lifecycle_stage_count
    assert observed["document_type_count"] == expected.document_type_count
    assert observed["branch_scope_counts"] == [
        list(item) for item in expected.branch_scope_counts
    ]
    assert observed["confidentiality_class_counts"] == [
        list(item) for item in expected.confidentiality_class_counts
    ]
    assert observed["billing_task_category_counts"] == [
        list(item) for item in expected.billing_task_category_counts
    ]
    assert observed["catalog_hash"] == expected.catalog_hash
    assert observed["planning_blueprint_count"] == 5
    assert observed["source_admission_state"] == "no_sources_admitted"
    assert observed["legal_compliance_claimed"] is False
    assert observed["native_fidelity_claimed"] is False
    assert observed["runtime_execution"] is False

def test_public_summary_rejects_tampered_counts(qualified_population) -> None:
    qualified_inputs = _summary_inputs(qualified_population)
    summary = build_public_dossier_catalog_summary(qualified_inputs)
    report = validate_public_dossier_catalog_summary(
        replace(summary, document_type_count=175),
        qualified_inputs,
    )
    assert {"DPS-002", "DPS-005"}.issubset(_codes(report))

