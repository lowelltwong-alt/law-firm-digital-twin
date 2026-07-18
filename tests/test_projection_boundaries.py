from __future__ import annotations

from dataclasses import replace

import pytest

from law_firm_digital_twin.case_compiler import (
    CompileRequest,
    FORBIDDEN_OPERATING_FIELDS,
    build_public_corpus_manifest,
    compile_case_design,
    validate_case_compilation,
)
from law_firm_digital_twin.case_manifest import (
    build_capability_registry,
    build_population_blueprints,
)
from law_firm_digital_twin.hashio import canonical_json
from law_firm_digital_twin.models import Arm, Route
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack
from law_firm_digital_twin.simulation import run_walking_skeleton


def compile_one(seed: str):
    registry = build_capability_registry()
    blueprint = build_population_blueprints(seed, 1)[0]
    return compile_case_design(
        CompileRequest(
            blueprint=blueprint,
            registry=registry,
            rule_pack=placeholder_data_first_rule_pack(),
        )
    )


def codes(report) -> set[str]:
    return {item.code for item in report.findings}


def test_compilation_is_deterministic_and_all_pipeline_stages_compose() -> None:
    first = compile_one("projection-replay")
    replay = compile_one("projection-replay")
    assert first == replay
    assert first.compilation_hash == replay.compilation_hash
    assert validate_case_compilation(first).passed is True
    assert len(first.artifact_plans) == len(first.persona_states)
    assert len(first.artifact_plans) == len(first.renderer_views)
    assert len(first.artifact_plans) == len(first.staged_artifacts)


def test_operating_projection_contains_no_sealed_or_evaluation_fields() -> None:
    compilation = compile_one("projection-leakage")
    operating = canonical_json(compilation.operating_export()).lower()
    assert all(term not in operating for term in FORBIDDEN_OPERATING_FIELDS)
    for _, value in compilation.sealed.axis_labels:
        assert f'"{value.lower()}"' not in operating
    assert compilation.evaluation.evaluator_case_id.lower() not in operating
    assert compilation.source_blueprint_commitment.lower() not in operating
    assert compilation.sealed.world_namespace.lower() not in operating
    assert compilation.sealed.matter_namespace.lower() not in operating


def test_evaluation_projection_is_separate_and_synthetic_only() -> None:
    compilation = compile_one("evaluation-plane")
    evaluation = compilation.evaluation
    operating = canonical_json(compilation.operating)
    assert evaluation.axis_labels == compilation.sealed.axis_labels
    assert evaluation.design_labels == compilation.sealed.design_labels
    assert evaluation.synthetic_only is True
    assert evaluation.real_world_prediction is False
    assert evaluation.evaluator_case_id not in operating


def test_design_only_case_family_cannot_reach_compiler() -> None:
    registry = build_capability_registry()
    blueprint = build_population_blueprints("family-forgery", 1)[0]
    forged = replace(
        blueprint,
        case_family_id="medical_malpractice_design",
    )
    with pytest.raises(ValueError, match="case_family_not_active"):
        compile_case_design(
            CompileRequest(
                blueprint=forged,
                registry=registry,
                rule_pack=placeholder_data_first_rule_pack(),
            )
        )


def test_unknown_axis_bucket_and_missing_axis_fail_closed() -> None:
    registry = build_capability_registry()
    blueprint = build_population_blueprints("axis-forgery", 1)[0]
    labels = dict(blueprint.sealed_axis_labels)
    labels["merits_posture"] = "invented_merits"
    forged = replace(blueprint, sealed_axis_labels=tuple(labels.items()))
    with pytest.raises(ValueError, match="unknown_population_bucket"):
        compile_case_design(
            CompileRequest(
                blueprint=forged,
                registry=registry,
                rule_pack=placeholder_data_first_rule_pack(),
            )
        )
    missing = replace(
        blueprint,
        sealed_axis_labels=blueprint.sealed_axis_labels[:-1],
    )
    with pytest.raises(ValueError, match="population_axis_set_mismatch"):
        compile_case_design(
            CompileRequest(
                blueprint=missing,
                registry=registry,
                rule_pack=placeholder_data_first_rule_pack(),
            )
        )


def test_cross_world_plan_and_staged_identity_collision_are_detected() -> None:
    compilation = compile_one("cross-world-tamper")
    first_plan = replace(
        compilation.artifact_plans[0],
        world_namespace="WNS-foreign",
    )
    forged_plans = (first_plan, *compilation.artifact_plans[1:])
    report = validate_case_compilation(
        replace(compilation, artifact_plans=forged_plans)
    )
    assert "CMP-015" in codes(report)
    assert "CMP-027" in codes(report)

    duplicate_staged = (
        compilation.staged_artifacts[0],
        compilation.staged_artifacts[0],
        *compilation.staged_artifacts[2:],
    )
    duplicate_report = validate_case_compilation(
        replace(compilation, staged_artifacts=duplicate_staged)
    )
    assert "CMP-012" in codes(duplicate_report)


def test_compilation_commitment_detects_projection_and_staged_tampering() -> None:
    compilation = compile_one("compilation-tamper")
    forged_operating = replace(
        compilation.operating,
        planned_artifact_count=999,
    )
    report = validate_case_compilation(
        replace(compilation, operating=forged_operating)
    )
    assert report.passed is False
    assert "CMP-027" in codes(report)

    first = replace(
        compilation.staged_artifacts[0],
        body=compilation.staged_artifacts[0].body + "\nForged.",
    )
    staged_report = validate_case_compilation(
        replace(
            compilation,
            staged_artifacts=(first, *compilation.staged_artifacts[1:]),
        )
    )
    assert any(code.startswith("CMP-ART-content_hash_mismatch") for code in codes(staged_report))
    assert "CMP-027" in codes(staged_report)


def test_different_blueprints_have_isolated_namespaces_and_ids() -> None:
    left = compile_one("namespace-left")
    right = compile_one("namespace-right")
    assert left.sealed.world_namespace != right.sealed.world_namespace
    assert left.sealed.matter_namespace != right.sealed.matter_namespace
    assert {item.plan_id for item in left.artifact_plans}.isdisjoint(
        item.plan_id for item in right.artifact_plans
    )
    assert {item.staged_artifact_id for item in left.staged_artifacts}.isdisjoint(
        item.staged_artifact_id for item in right.staged_artifacts
    )
    assert {item.state_id for item in left.persona_states}.isdisjoint(
        item.state_id for item in right.persona_states
    )


def test_public_corpus_manifest_is_aggregate_and_commitment_safe() -> None:
    compilations = (compile_one("public-left"), compile_one("public-right"))
    manifest = build_public_corpus_manifest(compilations)
    serialized = canonical_json(manifest).lower()
    assert manifest["case_count"] == 2
    assert manifest["case_families"] == ["employment_defense_g2"]
    assert manifest["synthetic_only"] is True
    assert manifest["non_predictive"] is True
    for forbidden in (
        *FORBIDDEN_OPERATING_FIELDS,
        "source_blueprint_commitment",
        "axis_labels",
        "fact_commitment",
        "persona_state",
        "renderer_projection",
        "decision_status",
        "protected_activity",
    ):
        assert forbidden not in serialized


def test_existing_g2_world_and_berean_path_remain_unchanged() -> None:
    before = run_walking_skeleton(
        "compiler-additive-parity",
        Arm.AI_FIRST,
        Route.TRIAL_APPEAL,
    )
    compile_one("unrelated-compiled-case")
    after = run_walking_skeleton(
        "compiler-additive-parity",
        Arm.AI_FIRST,
        Route.TRIAL_APPEAL,
    )
    assert before["event_hash"] == after["event_hash"]
    assert before["projection_hash"] == after["projection_hash"]
    assert before["cassette_hash"] == after["cassette_hash"]
    assert before["berean_audit"]["passed"] is True

