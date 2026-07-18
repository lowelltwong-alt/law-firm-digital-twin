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
from law_firm_digital_twin.composition_contracts import (
    build_channel_composition_contracts,
    derive_writing_disposition,
)
from law_firm_digital_twin.persona_channel_renderer import (
    build_composition_plan,
    render_unqualified_persona_channel_g2_fixture as render_persona_channel_g2_fixture,
    validate_unqualified_persona_channel_bundle as validate_persona_channel_bundle,
    validate_text_composition_candidate,
)
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack


def _compiled(seed: str = "persona-channel"):
    registry = build_capability_registry()
    return compile_case_design(
        CompileRequest(
            blueprint=build_population_blueprints(seed, 1)[0],
            registry=registry,
            rule_pack=placeholder_data_first_rule_pack(),
        )
    )


def test_all_active_g2_channels_render_with_exact_assertion_trace() -> None:
    compilation = _compiled("all-channel-render")
    channels = set()
    for projection in compilation.renderer_projections:
        bundle = render_persona_channel_g2_fixture(projection)
        channels.add(projection.channel_kind)
        assert validate_persona_channel_bundle(projection, bundle) == ()
        observed = [
            assertion_id
            for segment in bundle.candidate.segments
            if segment.function == "assertion"
            for assertion_id in segment.assertion_ids
        ]
        assert sorted(observed) == sorted(
            item.assertion_id for item in projection.allowed_assertions
        )
        assert bundle.candidate.rendered_media_type == "text/plain"
        assert bundle.candidate.simulated_target_native_format == (
            projection.simulated_target_native_format
        )
        assert bundle.render_receipt.composition_validated is True
        assert bundle.render_receipt.factual_authority_validated is False
        assert bundle.render_receipt.lineage_graph_validated is False
        assert bundle.render_receipt.canonical_admission is False
    assert channels == {
        "email",
        "hris_record",
        "policy_document",
        "structured_table",
        "calendar",
        "litigation_record",
        "expert_record",
        "irrelevant_record",
    }


def test_renderer_replay_is_deterministic_and_channel_specific() -> None:
    compilation = _compiled("render-replay")
    first = tuple(
        render_persona_channel_g2_fixture(item)
        for item in compilation.renderer_projections
    )
    second = tuple(
        render_persona_channel_g2_fixture(item)
        for item in compilation.renderer_projections
    )
    assert first == second
    by_channel = {
        projection.channel_kind: bundle.contract.required_sections
        for projection, bundle in zip(
            compilation.renderer_projections,
            first,
            strict=True,
        )
    }
    assert by_channel["email"] != by_channel["expert_record"]
    assert by_channel["structured_table"] != by_channel["calendar"]


def test_raw_background_training_and_goals_cannot_change_rendered_body() -> None:
    projection = next(
        item
        for item in _compiled("proxy-metamorphic").renderer_projections
        if item.allowed_assertions
    )
    base = render_persona_channel_g2_fixture(projection)
    altered_view = replace(
        projection.persona_view,
        synthetic_context="FORBIDDEN PROXY CONTEXT",
        training_context="FORBIDDEN EDUCATION PROXY",
        active_goals=("FORBIDDEN OUTCOME TARGET",),
    )
    altered_projection = replace(projection, persona_view=altered_view)
    altered = render_persona_channel_g2_fixture(altered_projection)
    assert altered.candidate.body == base.candidate.body
    rendered = altered.candidate.body.lower()
    assert "forbidden proxy" not in rendered
    assert "education proxy" not in rendered
    assert "outcome target" not in rendered


def test_tampered_candidate_and_wrong_contract_fail_closed() -> None:
    compilation = _compiled("candidate-tamper")
    projection = next(
        item for item in compilation.renderer_projections if item.allowed_assertions
    )
    bundle = render_persona_channel_g2_fixture(projection)
    tampered = replace(bundle.candidate, body=bundle.candidate.body + "\nInvented fact.")
    report = validate_text_composition_candidate(
        projection,
        bundle.contract,
        bundle.disposition,
        bundle.plan,
        tampered,
    )
    assert report.passed is False
    assert {
        item.code for item in report.findings
    }.issuperset({"noncanonical_composition_candidate", "body_segment_mismatch"})

    contracts = build_channel_composition_contracts()
    wrong_contract = next(
        contract
        for contract in contracts.values()
        if contract.channel_kind != projection.channel_kind
    )
    disposition = derive_writing_disposition(projection)
    with pytest.raises(ValueError, match="composition_capability_mismatch"):
        build_composition_plan(projection, wrong_contract, disposition)


def test_forbidden_oracle_and_stereotype_terms_are_rejected() -> None:
    projection = next(
        item
        for item in _compiled("forbidden-language").renderer_projections
        if item.allowed_assertions
    )
    bundle = render_persona_channel_g2_fixture(projection)
    poisoned_segment = replace(
        bundle.candidate.segments[-1],
        rendered_text="MBTI oracle says the target posture wins.",
    )
    poisoned = replace(
        bundle.candidate,
        segments=(*bundle.candidate.segments[:-1], poisoned_segment),
        body="\n".join(
            item.rendered_text
            for item in (*bundle.candidate.segments[:-1], poisoned_segment)
        ),
    )
    report = validate_text_composition_candidate(
        projection,
        bundle.contract,
        bundle.disposition,
        bundle.plan,
        poisoned,
    )
    assert report.passed is False
    assert "forbidden_context_leak" in {
        item.code for item in report.findings
    }

