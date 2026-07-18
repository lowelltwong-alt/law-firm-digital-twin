from __future__ import annotations

from dataclasses import replace

import pytest

from law_firm_digital_twin.case_compiler import (
    CompileRequest,
    compile_case_design,
)
from law_firm_digital_twin.case_manifest import (
    build_capability_registry,
    build_population_blueprints,
)
from law_firm_digital_twin.evidence_contracts import (
    FactAssertion,
    ArtifactVersionLineage,
    build_artifact_plan,
    build_renderer_projection,
    detect_staged_conflicts,
    issue_local_shape_receipt,
    stage_artifact,
    validate_staged_artifact,
    validate_version_lineage,
)
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack


def compiled_case(seed: str = "evidence-contract"):
    registry = build_capability_registry()
    blueprint = build_population_blueprints(seed, 1)[0]
    return compile_case_design(
        CompileRequest(
            blueprint=blueprint,
            registry=registry,
            rule_pack=placeholder_data_first_rule_pack(),
        )
    )


def mixed_conflict_case():
    registry = build_capability_registry()
    blueprints = build_population_blueprints("mixed-conflict-cases", 100)
    blueprint = next(
        item
        for item in blueprints
        if dict(item.sealed_axis_labels)["evidence_shape"] == "mixed_conflicting"
    )
    return compile_case_design(
        CompileRequest(
            blueprint=blueprint,
            registry=registry,
            rule_pack=placeholder_data_first_rule_pack(),
        )
    )


def finding_codes(report) -> set[str]:
    return {item.code for item in report.findings}


def test_compiler_produces_valid_noncanonical_artifact_candidates() -> None:
    compilation = compiled_case()
    assert len(compilation.artifact_plans) == 9
    assert len(compilation.staged_artifacts) == 9
    for staged, projection, receipt in zip(
        compilation.staged_artifacts,
        compilation.renderer_projections,
        compilation.local_shape_receipts,
        strict=True,
    ):
        report = validate_staged_artifact(staged, projection)
        assert report.passed is True
        assert receipt.canonical_admission is False
        assert staged.canonical_status == "proposal_only"
        assert staged.claimed_content_hash
        assert staged.custody_origin_hash


def test_body_metadata_and_custody_tampering_fail_closed() -> None:
    compilation = compiled_case("tamper-content")
    staged = compilation.staged_artifacts[0]
    projection = compilation.renderer_projections[0]

    body_tamper = replace(staged, body=staged.body + "\nUncommitted change.")
    assert "content_hash_mismatch" in finding_codes(
        validate_staged_artifact(body_tamper, projection)
    )

    metadata_tamper = replace(
        staged,
        metadata=tuple(
            (key, "forged") if key == "created_day" else (key, value)
            for key, value in staged.metadata
        ),
    )
    assert "content_hash_mismatch" in finding_codes(
        validate_staged_artifact(metadata_tamper, projection)
    )

    custody_tamper = replace(staged, custody_origin_hash="0" * 64)
    assert "custody_hash_mismatch" in finding_codes(
        validate_staged_artifact(custody_tamper, projection)
    )


def test_renderer_cannot_invent_mutate_or_omit_assertions() -> None:
    compilation = compiled_case("renderer-invention")
    index = next(
        index
        for index, item in enumerate(compilation.staged_artifacts)
        if item.assertions
    )
    staged = compilation.staged_artifacts[index]
    projection = compilation.renderer_projections[index]
    invented = FactAssertion(
        world_namespace=staged.world_namespace,
        matter_namespace=staged.matter_namespace,
        author_id=staged.author_id,
        fact_id="oracle_outcome",
        value="defense_wins",
        source_kind="invented",
        source_id="forged",
        learned_day=staged.created_day,
    )
    report = validate_staged_artifact(
        replace(staged, assertions=(*staged.assertions, invented)),
        projection,
    )
    assert "renderer_fact_invention" in finding_codes(report)
    assert "content_hash_mismatch" in finding_codes(report)

    omitted = replace(staged, assertions=staged.assertions[:-1])
    assert "required_assertion_omitted" in finding_codes(
        validate_staged_artifact(omitted, projection)
    )


def test_future_knowledge_and_cross_world_persona_fail_before_staging() -> None:
    compilation = compiled_case("knowledge-time")
    plan = compilation.artifact_plans[0]
    state = compilation.persona_states[0]
    capability = next(
        item
        for item in build_capability_registry().evidence_capabilities
        if item.capability_id == plan.capability_id
    )
    future = FactAssertion(
        world_namespace=plan.world_namespace,
        matter_namespace=plan.matter_namespace,
        author_id=state.actor_id,
        fact_id=state.knowledge_fact_ids[0],
        value="future_value",
        source_kind="forged",
        source_id="future",
        learned_day=plan.created_day + 1,
    )
    with pytest.raises(ValueError, match="future_knowledge_violation"):
        build_artifact_plan(
            world_namespace=plan.world_namespace,
            matter_namespace=plan.matter_namespace,
            capability=capability,
            author_id=state.actor_id,
            recipient_ids=plan.recipient_ids,
            created_day=plan.created_day,
            allowed_assertions=(future,),
            persona_state=state,
            logical_artifact_id="ART-FUTURE",
        )

    foreign_state = replace(state, world_namespace="WNS-foreign")
    with pytest.raises(ValueError, match="cross_world_persona_state"):
        build_artifact_plan(
            world_namespace=plan.world_namespace,
            matter_namespace=plan.matter_namespace,
            capability=capability,
            author_id=state.actor_id,
            recipient_ids=plan.recipient_ids,
            created_day=plan.created_day,
            allowed_assertions=(),
            persona_state=foreign_state,
            logical_artifact_id="ART-FOREIGN",
        )


def test_version_lineage_requires_parent_and_supersession_reason() -> None:
    invalid = ArtifactVersionLineage(
        logical_artifact_id="ART-1",
        version_id="ART-1-V2",
        revision=2,
        parent_version_id=None,
        parent_content_hash=None,
        supersession_reason=None,
    )
    assert "parent_version_required" in validate_version_lineage(invalid)
    assert "supersession_reason_required" in validate_version_lineage(invalid)

    self_parent = replace(
        invalid,
        parent_version_id="ART-1-V2",
        parent_content_hash="abc",
        supersession_reason="correction",
    )
    assert "lineage_self_parent" in validate_version_lineage(self_parent)


def test_worker_cannot_claim_admission_and_receipt_is_idempotent() -> None:
    compilation = compiled_case("admission-boundary")
    staged = compilation.staged_artifacts[0]
    projection = compilation.renderer_projections[0]
    forged = replace(staged, canonical_status="admitted")
    assert "worker_admission_forbidden" in finding_codes(
        validate_staged_artifact(forged, projection)
    )
    first = issue_local_shape_receipt(staged, projection)
    replay = issue_local_shape_receipt(staged, projection)
    assert first == replay
    assert first.canonical_admission is False


def test_conflicts_are_derived_without_sealed_design_explanation() -> None:
    compilation = mixed_conflict_case()
    detected = detect_staged_conflicts(compilation.staged_artifacts)
    assert "decision_status" in detected
    assert len(detected["decision_status"]) >= 2
    assert "test independent detection" not in repr(detected).lower()


def test_conflict_scanner_rejects_cross_case_join() -> None:
    left = compiled_case("left-world")
    right = compiled_case("right-world")
    with pytest.raises(ValueError, match="cross_world_conflict_scan"):
        detect_staged_conflicts(
            (left.staged_artifacts[0], right.staged_artifacts[0])
        )


def test_renderer_boundary_rejects_whole_case_or_sealed_object() -> None:
    compilation = compiled_case("wrong-object")
    view = compilation.renderer_views[0]
    with pytest.raises(ValueError, match="invalid_artifact_plan_type"):
        build_renderer_projection(compilation.sealed, view, compilation.persona_states[0])
    with pytest.raises(ValueError, match="invalid_renderer_projection_type"):
        stage_artifact(
            compilation.sealed,
            body="This body is long enough but the projection type is forbidden.",
            assertions=(),
            metadata=(),
            renderer_revision="forged",
        )

