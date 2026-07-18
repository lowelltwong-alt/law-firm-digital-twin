from __future__ import annotations

from dataclasses import replace

import pytest

from law_firm_digital_twin.case_compiler import (
    CompileRequest,
    compile_case_design,
    compile_population_fixture,
    validate_case_compilation,
)
from law_firm_digital_twin.case_manifest import (
    build_capability_registry,
    build_population_blueprints,
)
from law_firm_digital_twin.communication_culture import (
    COMMUNICATION_CAUSAL_POLICY,
    derive_actor_identity_commitment,
    derive_organization_identity_commitment,
    derive_individual_style,
    derive_organization_culture,
)
from law_firm_digital_twin.persona_channel_renderer import (
    render_unqualified_persona_channel_g2_fixture,
)
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack


def _compilations(seed: str, count: int = 1):
    return compile_population_fixture(
        seed=seed,
        count=count,
        rule_pack=placeholder_data_first_rule_pack(),
    )


def test_culture_and_individual_style_are_deterministic_and_scoped() -> None:
    compilation = _compilations("culture-replay")[0]
    projection = compilation.renderer_projections[0]
    scope = compilation.presentation_scope_commitment
    first_culture = derive_organization_culture(projection, scope)
    second_culture = derive_organization_culture(projection, scope)
    first_style = derive_individual_style(projection, first_culture, scope)
    second_style = derive_individual_style(projection, second_culture, scope)
    assert first_culture == second_culture
    assert first_style == second_style
    assert first_culture.organization_identity_commitment == (
        derive_organization_identity_commitment(projection, scope)
    )
    assert first_style.source_persona_state_hash == (
        projection.persona_view.persona_state_hash
    )
    assert first_culture.causal_policy == COMMUNICATION_CAUSAL_POLICY


def test_same_synthetic_organization_shares_matter_culture() -> None:
    compilation = _compilations("culture-coherence")[0]
    insured = [
        projection
        for projection in compilation.renderer_projections
        if projection.persona_view.organization == "synthetic_insured"
    ]
    assert len(insured) >= 2
    cultures = [
        derive_organization_culture(item, compilation.presentation_scope_commitment)
        for item in insured
    ]
    assert len({item.culture_hash for item in cultures}) == 1


def test_raw_background_training_goals_and_role_do_not_select_style() -> None:
    compilation = _compilations("culture-proxy")[0]
    projection = next(
        item
        for item in compilation.renderer_projections
        if item.allowed_assertions
    )
    scope = compilation.presentation_scope_commitment
    culture = derive_organization_culture(projection, scope)
    base_style = derive_individual_style(projection, culture, scope)
    altered_view = replace(
        projection.persona_view,
        synthetic_context="CLASS EDUCATION ACCENT PROTECTED PROXY",
        training_context="PROFESSION-AS-VOICE PROXY",
        active_goals=("MAKE ONE SIDE WIN",),
        role_id="forged_role_label_only",
    )
    altered_projection = replace(projection, persona_view=altered_view)
    altered_culture = derive_organization_culture(altered_projection, scope)
    altered_style = derive_individual_style(
        altered_projection,
        altered_culture,
        scope,
    )
    assert altered_culture == culture
    assert altered_style == base_style
    assert (
        render_unqualified_persona_channel_g2_fixture(
            altered_projection
        ).candidate.body
        == render_unqualified_persona_channel_g2_fixture(
            projection
        ).candidate.body
    )


def test_forged_culture_projection_is_rejected() -> None:
    compilation = _compilations("culture-forgery")[0]
    projection = compilation.renderer_projections[0]
    culture = derive_organization_culture(projection, compilation.presentation_scope_commitment)
    forged = replace(
        culture,
        review_protocol_id="culture_determines_credibility",
    )
    with pytest.raises(ValueError, match="noncanonical_culture_projection"):
        derive_individual_style(
            projection,
            forged,
            compilation.presentation_scope_commitment,


        )
def test_merits_only_change_cannot_change_presentation_scope_or_style() -> None:
    blueprint = build_population_blueprints("merits-style-firewall", 1)[0]
    labels = dict(blueprint.sealed_axis_labels)
    labels["merits_posture"] = (
        "claimant_favorable"
        if labels["merits_posture"] != "claimant_favorable"
        else "defense_favorable"
    )
    altered = replace(
        blueprint,
        sealed_axis_labels=tuple(
            (axis_id, labels[axis_id])
            for axis_id, _ in blueprint.sealed_axis_labels
        ),
    )
    registry = build_capability_registry()
    rule_pack = placeholder_data_first_rule_pack()
    first = compile_case_design(CompileRequest(blueprint, registry, rule_pack))
    second = compile_case_design(CompileRequest(altered, registry, rule_pack))
    assert first.sealed.world_namespace != second.sealed.world_namespace
    assert (
        first.presentation_scope_commitment == second.presentation_scope_commitment
    )
    for left, right in zip(
        first.renderer_projections,
        second.renderer_projections,
        strict=True,
    ):
        left_culture = derive_organization_culture(
            left, first.presentation_scope_commitment
        )
        right_culture = derive_organization_culture(
            right, second.presentation_scope_commitment
        )
        assert left_culture == right_culture
        left_style = derive_individual_style(
            left, left_culture, first.presentation_scope_commitment
        )
        right_style = derive_individual_style(
            right, right_culture, second.presentation_scope_commitment
        )
        assert left_style.selected_operation_ids == right_style.selected_operation_ids
        assert left_style.effective_voice_signature == right_style.effective_voice_signature
        assert left_style.effective_geometry_signature == right_style.effective_geometry_signature



def test_persistent_firm_identity_is_stable_while_insured_identity_is_local() -> None:
    compilations = _compilations("identity-continuity", 3)
    firm_actor_commitments = set()
    firm_organization_commitments = set()
    insured_actor_commitments = set()
    firm_voice_signatures = set()
    firm_geometry_signatures = set()
    for compilation in compilations:
        scope = compilation.presentation_scope_commitment
        for projection in compilation.renderer_projections:
            if projection.persona_view.organization == "defense_firm":
                firm_actor_commitments.add(
                    derive_actor_identity_commitment(projection, scope)
                )
                firm_organization_commitments.add(
                    derive_organization_identity_commitment(projection, scope)
                )
                if projection.channel_kind == "litigation_record":
                    culture = derive_organization_culture(projection, scope)
                    style = derive_individual_style(projection, culture, scope)
                    firm_voice_signatures.add(style.effective_voice_signature)
                    firm_geometry_signatures.add(
                        style.effective_geometry_signature
                    )
            elif projection.author_id == "manager_witness":
                insured_actor_commitments.add(
                    derive_actor_identity_commitment(projection, scope)
                )
    assert len(firm_organization_commitments) == 1
    assert 1 < len(firm_actor_commitments) < 10
    assert len(insured_actor_commitments) == 3
    assert len(firm_voice_signatures) == 1
    assert len(firm_geometry_signatures) >= 2


def test_presentation_scope_tamper_fails_source_derivation_validation() -> None:
    compilation = _compilations("scope-tamper")[0]
    tampered = replace(
        compilation,
        presentation_scope_commitment="0" * 64,
    )
    report = validate_case_compilation(tampered)
    assert report.passed is False
    assert "CMP-046" in {item.code for item in report.findings}



def test_matter_population_has_bounded_style_family_diversity() -> None:
    compilations = _compilations("g2-scale-v1-ten", 10)
    by_channel: dict[str, list[tuple[str, str]]] = {}
    for compilation in compilations:
        for projection in compilation.renderer_projections:
            scope = compilation.presentation_scope_commitment
            culture = derive_organization_culture(projection, scope)
            style = derive_individual_style(projection, culture, scope)
            by_channel.setdefault(projection.channel_kind, []).append(
                (
                    style.effective_voice_signature,
                    style.effective_geometry_signature,
                )
            )
    for channel, families in by_channel.items():
        if len(families) >= 10:
            assert len(set(families)) >= 3, channel
            largest = max(families.count(item) for item in set(families))
            assert largest / len(families) <= 0.70, channel

