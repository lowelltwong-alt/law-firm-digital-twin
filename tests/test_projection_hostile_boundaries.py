from __future__ import annotations

from dataclasses import replace

import pytest

from law_firm_digital_twin.case_compiler import (
    CompileRequest,
    build_public_corpus_manifest,
    compile_case_design,
    qualify_case_compilation,
    validate_case_qualification_receipt,
    validate_case_compilation,
)
from law_firm_digital_twin.case_manifest import (
    build_capability_registry,
    build_population_blueprints,
)
from law_firm_digital_twin.evidence_contracts import (
    build_artifact_plan,
    build_renderer_projection,
    issue_local_shape_receipt,
    render_deterministic_g2_fixture,
)
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack
from law_firm_digital_twin.persona_state import project_persona_for_renderer


def compiled_case(seed: str = "hostile-boundaries"):
    registry = build_capability_registry()
    return compile_case_design(
        CompileRequest(
            blueprint=build_population_blueprints(seed, 1)[0],
            registry=registry,
            rule_pack=placeholder_data_first_rule_pack(),
        )
    )


def finding_codes(compilation) -> set[str]:
    return {item.code for item in validate_case_compilation(compilation).findings}


def test_known_fact_id_cannot_carry_forged_value_or_source() -> None:
    compilation = compiled_case("forged-assertion")
    plan = next(item for item in compilation.artifact_plans if item.allowed_assertions)
    state = next(item for item in compilation.persona_states if item.state_id == plan.persona_state_id)
    capability = next(
        item
        for item in build_capability_registry().evidence_capabilities
        if item.capability_id == plan.capability_id
    )
    forged = replace(
        plan.allowed_assertions[0],
        value="FORGED_UNGROUNDED_VALUE",
        source_id="not-a-sealed-claim",
    )
    with pytest.raises(ValueError, match="assertion_grant_violation"):
        build_artifact_plan(
            world_namespace=plan.world_namespace,
            matter_namespace=plan.matter_namespace,
            capability=capability,
            author_id=plan.author_id,
            recipient_ids=plan.recipient_ids,
            created_day=plan.created_day,
            allowed_assertions=(forged,),
            persona_state=state,
            logical_artifact_id="ART-FORGED",
        )



def test_local_shape_receipt_cannot_masquerade_as_fact_authority() -> None:
    compilation = compiled_case("local-receipt-boundary")
    plan_index = next(
        index
        for index, item in enumerate(compilation.artifact_plans)
        if item.allowed_assertions
    )
    plan = compilation.artifact_plans[plan_index]
    state_index = next(
        index
        for index, item in enumerate(compilation.persona_states)
        if item.state_id == plan.persona_state_id
    )
    state = compilation.persona_states[state_index]
    capability = next(
        item
        for item in build_capability_registry().evidence_capabilities
        if item.capability_id == plan.capability_id
    )
    forged = replace(
        plan.allowed_assertions[0],
        value="FORGED_UNGROUNDED_VALUE",
        source_id="not-a-sealed-claim",
    )
    forged_state = replace(
        state,
        knowledge_assertion_ids=(forged.assertion_id,),
    )
    forged_view = project_persona_for_renderer(
        forged_state,
        allowed_fact_ids=(forged.fact_id,),
        allowed_assertion_ids=(forged.assertion_id,),
    )
    forged_plan = build_artifact_plan(
        world_namespace=plan.world_namespace,
        matter_namespace=plan.matter_namespace,
        capability=capability,
        author_id=plan.author_id,
        recipient_ids=plan.recipient_ids,
        created_day=plan.created_day,
        allowed_assertions=(forged,),
        persona_state=forged_state,
        logical_artifact_id=plan.lineage.logical_artifact_id,
        simulated_target_native_format=plan.simulated_target_native_format,
    )
    forged_projection = build_renderer_projection(
        forged_plan,
        forged_view,
        forged_state,
    )
    forged_staged = render_deterministic_g2_fixture(forged_projection)
    local_receipt = issue_local_shape_receipt(forged_staged, forged_projection)
    assert local_receipt.decision == "local_shape_validated_only"
    assert local_receipt.authority_validated is False
    assert local_receipt.lineage_graph_validated is False

    def swapped(items, index, replacement):
        result = list(items)
        result[index] = replacement
        return tuple(result)

    forged_compilation = replace(
        compilation,
        persona_states=swapped(compilation.persona_states, state_index, forged_state),
        renderer_views=swapped(compilation.renderer_views, plan_index, forged_view),
        artifact_plans=swapped(compilation.artifact_plans, plan_index, forged_plan),
        renderer_projections=swapped(
            compilation.renderer_projections,
            plan_index,
            forged_projection,
        ),
        staged_artifacts=swapped(
            compilation.staged_artifacts,
            plan_index,
            forged_staged,
        ),
        local_shape_receipts=swapped(
            compilation.local_shape_receipts,
            plan_index,
            local_receipt,
        ),
    )
    assert "CMP-036" in finding_codes(forged_compilation)
    with pytest.raises(ValueError, match="case_compilation_validation_failed"):
        qualify_case_compilation(forged_compilation)


def test_case_qualification_receipt_binds_full_authority_validation() -> None:
    compilation = compiled_case("case-qualification")
    receipt = qualify_case_compilation(compilation)
    assert receipt.sealed_authority_validated is True
    assert receipt.lineage_graph_validated is True
    assert receipt.local_shape_receipts_validated is True
    assert receipt.canonical_admission is False
    assert validate_case_qualification_receipt(receipt, compilation) is True
    assert (
        validate_case_qualification_receipt(
            replace(receipt, compilation_hash="0" * 64),
            compilation,
        )
        is False
    )


def test_stale_persona_hash_and_revision_cannot_reach_renderer() -> None:
    compilation = compiled_case("stale-view")
    plan = compilation.artifact_plans[0]
    view = compilation.renderer_views[0]
    state = compilation.persona_states[0]
    with pytest.raises(ValueError, match="stale_persona_state"):
        build_renderer_projection(plan, replace(view, persona_state_hash="0" * 64), state)
    with pytest.raises(ValueError, match="stale_persona_revision"):
        build_renderer_projection(plan, replace(view, core_revision="obsolete-v0"), state)
    with pytest.raises(ValueError, match="noncanonical_persona_view"):
        build_renderer_projection(
            plan,
            replace(view, synthetic_context="FORGED PRIVATE CONTEXT"),
            state,
        )


def test_stale_capability_and_tampered_receipt_fail_compilation() -> None:
    compilation = compiled_case("revision-receipt")
    stale_plan = replace(compilation.artifact_plans[0], capability_revision="obsolete-v0")
    stale = replace(
        compilation,
        artifact_plans=(stale_plan, *compilation.artifact_plans[1:]),
    )
    assert "CMP-035" in finding_codes(stale)

    forged_receipt = replace(
        compilation.local_shape_receipts[0],
        receipt_id="FORGED",
        staged_artifact_hash="0" * 64,
        renderer_projection_hash="1" * 64,
    )
    tampered = replace(
        compilation,
        local_shape_receipts=(forged_receipt, *compilation.local_shape_receipts[1:]),
    )
    assert "CMP-RECEIPT" in finding_codes(tampered)


def test_duplicate_lineage_and_orphan_revision_fail_closed() -> None:
    compilation = compiled_case("lineage-graph")
    duplicate_plan = replace(
        compilation.artifact_plans[1],
        lineage=compilation.artifact_plans[0].lineage,
    )
    duplicate = replace(
        compilation,
        artifact_plans=(compilation.artifact_plans[0], duplicate_plan, *compilation.artifact_plans[2:]),
    )
    assert "CMP-LINEAGE" in finding_codes(duplicate)

    plan = next(item for item in compilation.artifact_plans if item.family_id == "employment_policy")
    state = next(item for item in compilation.persona_states if item.state_id == plan.persona_state_id)
    capability = next(
        item
        for item in build_capability_registry().evidence_capabilities
        if item.capability_id == plan.capability_id
    )
    with pytest.raises(ValueError, match="parent_artifact_required"):
        build_artifact_plan(
            world_namespace=plan.world_namespace,
            matter_namespace=plan.matter_namespace,
            capability=capability,
            author_id=plan.author_id,
            recipient_ids=plan.recipient_ids,
            created_day=plan.created_day,
            allowed_assertions=plan.allowed_assertions,
            persona_state=state,
            logical_artifact_id=plan.lineage.logical_artifact_id,
            revision=2,
            supersession_reason="synthetic correction",
        )
    parent_index = compilation.artifact_plans.index(plan)
    tampered_parent = replace(
        compilation.staged_artifacts[parent_index],
        claimed_content_hash="deadbeef",
    )
    with pytest.raises(ValueError, match="parent_artifact_validation_failed"):
        build_artifact_plan(
            world_namespace=plan.world_namespace,
            matter_namespace=plan.matter_namespace,
            capability=capability,
            author_id=plan.author_id,
            recipient_ids=plan.recipient_ids,
            created_day=plan.created_day,
            allowed_assertions=plan.allowed_assertions,
            persona_state=state,
            logical_artifact_id=plan.lineage.logical_artifact_id,
            revision=2,
            parent_artifact=tampered_parent,
            parent_projection=compilation.renderer_projections[parent_index],
            supersession_reason="synthetic correction",
        )



def test_capability_author_and_matter_scope_are_structural() -> None:
    compilation = compiled_case("scope-authority")
    litigation_plan = next(
        item for item in compilation.artifact_plans if item.family_id == "employment_litigation"
    )
    capability = next(
        item
        for item in build_capability_registry().evidence_capabilities
        if item.capability_id == litigation_plan.capability_id
    )
    expert_state = next(
        item for item in compilation.persona_states if item.actor_id == "independent_expert"
    )
    with pytest.raises(ValueError, match="capability_author_unauthorized"):
        build_artifact_plan(
            world_namespace=expert_state.world_namespace,
            matter_namespace=expert_state.matter_namespace,
            capability=capability,
            author_id=expert_state.actor_id,
            recipient_ids=("claim_handler",),
            created_day=expert_state.as_of_day,
            allowed_assertions=(),
            persona_state=expert_state,
            logical_artifact_id="ART-UNAUTHORIZED",
        )

    valid_plan = compilation.artifact_plans[0]
    valid_state = next(
        item for item in compilation.persona_states if item.state_id == valid_plan.persona_state_id
    )
    valid_capability = next(
        item
        for item in build_capability_registry().evidence_capabilities
        if item.capability_id == valid_plan.capability_id
    )
    with pytest.raises(ValueError, match="cross_matter_persona_state"):
        build_artifact_plan(
            world_namespace=valid_plan.world_namespace,
            matter_namespace=valid_plan.matter_namespace,
            capability=valid_capability,
            author_id=valid_plan.author_id,
            recipient_ids=valid_plan.recipient_ids,
            created_day=valid_plan.created_day,
            allowed_assertions=valid_plan.allowed_assertions,
            persona_state=replace(valid_state, matter_namespace="MNS-foreign"),
            logical_artifact_id="ART-FOREIGN-MATTER",
        )


def test_public_manifest_rejects_unvalidated_source_fact_leak() -> None:
    compilation = compiled_case("manifest-leak")
    forged_operating = replace(
        compilation.operating,
        case_family_id=(
            "employment_defense_g2;"
            "protected_activity=employee_reported_wage_and_safety_concerns"
        ),
    )
    forged = replace(compilation, operating=forged_operating)
    with pytest.raises(ValueError, match="invalid_compilation_for_public_manifest"):
        build_public_corpus_manifest((forged,))


def test_g2_fixture_declares_actual_text_bytes_separately_from_target_format() -> None:
    compilation = compiled_case("format-truth")
    for staged, projection in zip(
        compilation.staged_artifacts,
        compilation.renderer_projections,
        strict=True,
    ):
        assert staged.rendered_media_type == "text/plain"
        assert staged.simulated_target_native_format == projection.simulated_target_native_format

