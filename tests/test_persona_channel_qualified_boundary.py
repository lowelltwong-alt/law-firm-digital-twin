from __future__ import annotations

from dataclasses import replace

import pytest

from law_firm_digital_twin.case_compiler import (
    CompileRequest,
    compile_case_design,
    qualify_case_compilation,
)
from law_firm_digital_twin.case_manifest import (
    build_capability_registry,
    build_population_blueprints,
)
from law_firm_digital_twin.corpus_auditor import build_corpus_audit_artifact
from law_firm_digital_twin.evidence_contracts import FactAssertion
from law_firm_digital_twin.persona_channel_renderer import (
    render_persona_channel_g2_fixture,
    validate_persona_channel_bundle,
    render_unqualified_persona_channel_g2_fixture,
)
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack


def _qualified(seed: str):
    registry = build_capability_registry()
    compilation = compile_case_design(
        CompileRequest(
            blueprint=build_population_blueprints(seed, 1)[0],
            registry=registry,
            rule_pack=placeholder_data_first_rule_pack(),
        )
    )
    return compilation, qualify_case_compilation(compilation)


def test_qualified_renderer_reselects_projection_from_validated_case() -> None:
    compilation, receipt = _qualified("qualified-reselection")
    bundles = tuple(
        render_persona_channel_g2_fixture(compilation, receipt, index)
        for index in range(len(compilation.renderer_projections))
    )
    assert all(
        validate_persona_channel_bundle(
            compilation,
            receipt,
            bundle,
        )
        == ()
        for bundle in bundles
    )
    assert all(
        bundle.source_projection_hash
        == compilation.renderer_projections[index].projection_hash
        for index, bundle in enumerate(bundles)
    )


def test_forged_persona_projection_cannot_cross_qualified_boundary() -> None:
    compilation, receipt = _qualified("forged-persona-boundary")
    projection = compilation.renderer_projections[0]
    forged_view = replace(
        projection.persona_view,
        voice_constraints=(
            ("signature", "forged-signature"),
            ("register", "plain forged register"),
            ("directness", "very high"),
            ("organization", "bottom line"),
            ("sentence_style", "short fragments"),
            ("revision_habit", "none"),
        ),
    )
    forged_projection = replace(projection, persona_view=forged_view)
    forged_compilation = replace(
        compilation,
        renderer_projections=(
            forged_projection,
            *compilation.renderer_projections[1:],
        ),
    )
    with pytest.raises(ValueError, match="case_qualification_receipt_invalid"):
        render_persona_channel_g2_fixture(
            forged_compilation,
            receipt,
            0,
        )


def test_fabricated_assertion_cannot_cross_qualified_boundary() -> None:
    compilation, receipt = _qualified("forged-assertion-boundary")
    index = next(
        i
        for i, projection in enumerate(compilation.renderer_projections)
        if projection.allowed_assertions
    )
    projection = compilation.renderer_projections[index]
    forged_assertion = FactAssertion(
        world_namespace=projection.world_namespace,
        matter_namespace=projection.matter_namespace,
        author_id=projection.author_id,
        fact_id="fabricated_adverse_event",
        value="unrelated_secret_statement",
        source_kind="forged",
        source_id="untrusted",
        learned_day=projection.created_day,
    )
    forged_projection = replace(
        projection,
        allowed_assertions=(forged_assertion,),
    )
    projections = list(compilation.renderer_projections)
    projections[index] = forged_projection
    forged_compilation = replace(
        compilation,
        renderer_projections=tuple(projections),
    )
    with pytest.raises(ValueError, match="case_qualification_receipt_invalid"):
        render_persona_channel_g2_fixture(
            forged_compilation,
            receipt,
            index,
        )


def test_forged_qualified_bundle_cannot_enter_validator() -> None:
    compilation, receipt = _qualified("forged-qualified-bundle")
    bundle = render_persona_channel_g2_fixture(compilation, receipt, 0)
    forged = replace(
        bundle,
        source_projection_hash="0" * 64,
        qualification_receipt_hash="1" * 64,
    )
    errors = validate_persona_channel_bundle(
        compilation,
        receipt,
        forged,
    )
    assert "qualified_projection_hash_mismatch" in errors
    assert "qualified_receipt_hash_mismatch" in errors


def test_unqualified_bundle_cannot_enter_corpus_builder() -> None:
    compilation, receipt = _qualified("unqualified-corpus-boundary")
    projection = compilation.renderer_projections[0]
    unqualified = render_unqualified_persona_channel_g2_fixture(projection)
    with pytest.raises(
        ValueError,
        match="invalid_qualified_persona_channel_bundle:qualified_bundle_type_invalid",
    ):
        build_corpus_audit_artifact(
            compilation,
            receipt,
            unqualified,  # type: ignore[arg-type]
        )

