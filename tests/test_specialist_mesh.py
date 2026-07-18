from __future__ import annotations

from pathlib import Path
from dataclasses import replace

import pytest

from law_firm_digital_twin.case_compiler import (
    compile_population_fixture,
    qualify_case_compilation,
    validate_case_qualification_receipt,
    validate_case_compilation,
)
from law_firm_digital_twin.case_manifest import build_capability_registry
from law_firm_digital_twin.evidence_contracts import (
    render_deterministic_g2_fixture,
)
from law_firm_digital_twin.hashio import canonical_json, digest
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack
from law_firm_digital_twin.specialist_mesh import (
    build_artifact_production_manifest,
    build_domain_pack,
)
from law_firm_digital_twin.specialist_mesh_validator import (
    QualifiedSpecialistMeshInput,
    evaluate_specialist_mesh_corpus,
)


def corpus(seed: str, count: int = 2):
    return compile_population_fixture(
        seed=seed,
        count=count,
        rule_pack=placeholder_data_first_rule_pack(),
    )


def mesh_codes(compilation) -> set[str]:
    return {
        finding.code
        for finding in validate_case_compilation(compilation).findings
        if "MESH" in finding.code
    }


def test_mesh_is_deterministic_exhaustive_and_independently_checked() -> None:
    first = corpus("specialist-mesh-coverage", 10)
    replay = corpus("specialist-mesh-coverage", 10)
    assert first == replay
    assert sum(len(item.artifact_production_manifests) for item in first) == 90
    assert all(len(item.artifact_production_manifests) == 9 for item in first)
    assert all(len(item.artifact_mesh_receipts) == 9 for item in first)
    assert {
        manifest.evidence_capability_id
        for compilation in first
        for manifest in compilation.artifact_production_manifests
    } == {
        "evidence.employment_email.v1",
        "evidence.employment_hr_record.v1",
        "evidence.employment_policy.v1",
        "evidence.employment_payroll.v1",
        "evidence.employment_calendar.v1",
        "evidence.employment_litigation.v1",
        "evidence.employment_expert.v1",
        "evidence.employment_noise.v1",
    }
    for compilation in first:
        for manifest in compilation.artifact_production_manifests:
            writers = {
                item.specialist_capability_id
                for item in manifest.assignments
                if item.phase == "writer"
            }
            checkers = {
                item.specialist_capability_id
                for item in manifest.assignments
                if item.phase == "checker"
            }
            assert writers.isdisjoint(checkers)
            assert len(checkers) == 4
            assert all(item.runtime_executed is False for item in manifest.assignments)


def test_tampered_manifest_and_self_check_claim_fail_full_qualification() -> None:
    compilation = corpus("specialist-mesh-tamper", 1)[0]
    manifest = compilation.artifact_production_manifests[0]
    writer = next(item for item in manifest.assignments if item.phase == "writer")
    checker_index = next(
        index for index, item in enumerate(manifest.assignments) if item.phase == "checker"
    )
    assignments = list(manifest.assignments)
    assignments[checker_index] = replace(
        assignments[checker_index],
        specialist_capability_id=writer.specialist_capability_id,
        specialist_revision=writer.specialist_revision,
        capability_classification=writer.capability_classification,
    )
    forged_manifest = replace(manifest, assignments=tuple(assignments))
    forged = replace(
        compilation,
        artifact_production_manifests=(
            forged_manifest,
            *compilation.artifact_production_manifests[1:],
        ),
    )
    assert "CMP-MESH-009" in mesh_codes(forged)
    with pytest.raises(ValueError, match="case_compilation_validation_failed"):
        qualify_case_compilation(forged)



def test_projection_cannot_add_assertions_outside_its_bound_plan() -> None:
    compilation = corpus("specialist-mesh-projection-injection", 1)[0]
    registry = build_capability_registry()
    plan_index = next(
        index
        for index, item in enumerate(compilation.artifact_plans)
        if item.allowed_assertions
    )
    plan = compilation.artifact_plans[plan_index]
    projection = compilation.renderer_projections[plan_index]
    state = next(
        item for item in compilation.persona_states if item.state_id == plan.persona_state_id
    )
    extra_assertion = replace(
        plan.allowed_assertions[0],
        fact_id="forged_extra_fact",
        value="forged_extra_value",
        source_id="forged_extra_source",
    )
    forged_projection = replace(
        projection,
        allowed_assertions=(*projection.allowed_assertions, extra_assertion),
    )
    with pytest.raises(ValueError, match="renderer_fact_mutation"):
        render_deterministic_g2_fixture(forged_projection)
    forged = replace(
        compilation,
        renderer_projections=(
            *compilation.renderer_projections[:plan_index],
            forged_projection,
            *compilation.renderer_projections[plan_index + 1 :],
        ),
    )
    assert "CMP-048" in {
        item.code for item in validate_case_compilation(forged, registry).findings
    }
    family = next(
        item for item in registry.case_families
        if item.family_id == compilation.operating.case_family_id
    )
    evidence = next(
        item for item in registry.evidence_capabilities if item.capability_id == plan.capability_id
    )
    with pytest.raises(ValueError, match="noncanonical_renderer_projection"):
        build_artifact_production_manifest(
            family=family,
            domain_pack=build_domain_pack(family, registry),
            evidence_capability=evidence,
            plan=plan,
            projection=forged_projection,
            persona_state=state,
            registry=registry,
        )


def test_full_specialist_policy_contract_is_revision_bound() -> None:
    registry = build_capability_registry()
    compilation = compile_population_fixture(
        seed="specialist-mesh-policy-binding",
        count=1,
        rule_pack=placeholder_data_first_rule_pack(),
        registry=registry,
    )[0]
    receipt = qualify_case_compilation(compilation, registry)
    target = next(
        item
        for item in registry.specialist_capabilities
        if item.capability_id == "specialist.employment_business_record_writer.v1"
    )
    mutations = (
        ("stop_conditions", (*target.stop_conditions, "new_stop")),
        ("prohibited_inputs", (*target.prohibited_inputs, "new_prohibited_input")),
        ("privacy_class", "changed_privacy_class"),
        ("qualification_fixture_id", "fixture.changed.v1"),
        ("qualification_expiry_triggers", (*target.qualification_expiry_triggers, "new_expiry")),
        ("dependencies", (*target.dependencies, "new_dependency")),
        ("validator_ids", (*target.validator_ids, "new_validator")),
    )
    for field_name, field_value in mutations:
        changed_target = replace(target, **{field_name: field_value})
        changed_registry = replace(
            registry,
            specialist_capabilities=tuple(
                changed_target if item.capability_id == target.capability_id else item
                for item in registry.specialist_capabilities
            ),
        )
        assert validate_case_qualification_receipt(
            receipt,
            compilation,
            changed_registry,
        ) is False

def test_cross_case_manifest_and_overclaiming_receipt_fail_closed() -> None:
    first, second = corpus("specialist-mesh-cross-case", 2)
    crossed = replace(
        first,
        artifact_production_manifests=(
            second.artifact_production_manifests[0],
            *first.artifact_production_manifests[1:],
        ),
    )
    assert mesh_codes(crossed) & {"CMP-MESH-006", "CMP-MESH-009"}

    overclaim = replace(
        first.artifact_mesh_receipts[0],
        runtime_specialists_executed=True,
        fact_authority_validated=True,
        canonical_admission=True,
    )
    forged = replace(
        first,
        artifact_mesh_receipts=(overclaim, *first.artifact_mesh_receipts[1:]),
    )
    assert "CMP-MESH-014" in mesh_codes(forged)


def test_design_only_domain_pack_cannot_generate_artifact_manifest() -> None:
    compilation = corpus("specialist-mesh-design-only", 1)[0]
    registry = build_capability_registry()
    family = next(
        item for item in registry.case_families if item.family_id == "employment_defense_g2"
    )
    plan = compilation.artifact_plans[0]
    projection = compilation.renderer_projections[0]
    state = next(
        item for item in compilation.persona_states if item.state_id == plan.persona_state_id
    )
    evidence = next(
        item for item in registry.evidence_capabilities if item.capability_id == plan.capability_id
    )
    with pytest.raises(ValueError, match="domain_pack_not_active_g2"):
        build_artifact_production_manifest(
            family=replace(family, readiness="design_only"),
            domain_pack=replace(build_domain_pack(family, registry), readiness="design_only"),
            evidence_capability=evidence,
            plan=plan,
            projection=projection,
            persona_state=state,
            registry=registry,
        )


def test_expert_and_policy_routes_include_domain_specific_gates() -> None:
    compilation = corpus("specialist-mesh-special-routes", 1)[0]
    expert = next(
        item for item in compilation.artifact_production_manifests
        if item.artifact_family_id == "employment_expert"
    )
    policy = next(
        item for item in compilation.artifact_production_manifests
        if item.artifact_family_id == "employment_policy"
    )
    assert "validate_expert_source_boundary" in expert.required_validator_ids
    assert "validate_expert_independence" in expert.required_validator_ids
    assert "validate_contract_lineage" in policy.required_validator_ids


def test_public_mesh_report_is_aggregate_qualified_and_provider_neutral() -> None:
    compilations = corpus("specialist-mesh-public", 10)
    report = evaluate_specialist_mesh_corpus(
        tuple(
            QualifiedSpecialistMeshInput(
                compilation=item,
                qualification_receipt=qualify_case_compilation(item),
            )
            for item in compilations
        )
    )
    assert report.case_count == 10
    assert report.artifact_count == 90
    assert report.local_contract_receipt_count == 90
    assert report.runtime_specialist_execution_count == 0
    text = canonical_json(report.public_summary()).lower()
    for forbidden in (
        "world_namespace",
        "matter_namespace",
        "author_id",
        "recipient_ids",
        "persona_state",
        "allowed_assertions",
        "design_labels",
        "sealed_case_state",
        "openai",
        "anthropic",
        "composer",
    ):
        assert forbidden not in text


def test_checked_in_specialist_mesh_fixture_matches_builder() -> None:
    seed = "g2-specialist-mesh-v1-ten"
    compilations = corpus(seed, 10)
    report = evaluate_specialist_mesh_corpus(
        tuple(
            QualifiedSpecialistMeshInput(
                compilation=item,
                qualification_receipt=qualify_case_compilation(item),
            )
            for item in compilations
        )
    )
    payload = {
        "fixture_revision": "g2-specialist-mesh-fixture-v1",
        "seed_commitment": digest(
            {
                "fixture_revision": "g2-specialist-mesh-fixture-v1",
                "seed": seed,
            }
        ),
        **report.public_summary(),
    }
    path = (
        Path(__file__).resolve().parents[1]
        / "generated"
        / "g2-specialist-mesh-v1"
        / "mesh-report.json"
    )
    assert path.read_text(encoding="utf-8") == canonical_json(payload) + "\n"


def test_unqualified_corpus_input_is_rejected() -> None:
    compilation = corpus("specialist-mesh-unqualified", 1)[0]
    receipt = qualify_case_compilation(compilation)
    with pytest.raises(ValueError, match="unqualified_specialist_mesh_compilation"):
        evaluate_specialist_mesh_corpus(
            (
                QualifiedSpecialistMeshInput(
                    compilation=compilation,
                    qualification_receipt=replace(receipt, compilation_hash="0" * 64),
                ),
            )
        )
