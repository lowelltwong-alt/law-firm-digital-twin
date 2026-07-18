from __future__ import annotations

from dataclasses import replace

import pytest

from law_firm_digital_twin.case_compiler import (
    compile_population_fixture,
    qualify_case_compilation,
)
from law_firm_digital_twin.corpus_diversity_evaluator import (
    QualifiedCorpusDiversityInput,
    _evaluate_corpus_diversity_artifacts,
    build_corpus_diversity_artifacts,
    evaluate_corpus_diversity,
)
from law_firm_digital_twin.hashio import canonical_json, digest
from law_firm_digital_twin.persona_channel_renderer import (
    render_persona_channel_batch,
)
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack


def _diversity_fixture(seed: str, count: int):
    compilations = compile_population_fixture(
        seed=seed,
        count=count,
        rule_pack=placeholder_data_first_rule_pack(),
    )
    inputs = []
    rows = []
    for compilation in compilations:
        receipt = qualify_case_compilation(compilation)
        bundles = render_persona_channel_batch(compilation, receipt)
        input_item = QualifiedCorpusDiversityInput(
            compilation=compilation,
            qualification_receipt=receipt,
            bundles=tuple(bundles),
        )
        inputs.append(input_item)
        rows.extend(
            build_corpus_diversity_artifacts(
                compilation,
                receipt,
                bundles,
            )
        )
    return tuple(inputs), tuple(rows)


def test_ten_case_diversity_report_passes_meaningful_g2_gates() -> None:
    inputs, _ = _diversity_fixture("g2-scale-v1-ten", 10)
    report = evaluate_corpus_diversity(inputs)
    assert report == evaluate_corpus_diversity(inputs)
    assert report.passed is True
    assert report.artifact_count == 90
    assert report.qualified_binding_rate == 1.0
    assert report.factual_trace_coverage == 1.0
    assert report.cross_channel_schema_separation == 1.0
    assert report.eligible_channel_count == 8
    assert all(
        item.effective_combined_family_count >= 3
        for item in report.channel_metrics
    )
    assert all(
        item.largest_effective_family_share <= 0.70
        for item in report.channel_metrics
    )
    assert all(
        item.meaningful_presentation_ratio >= 0.20
        for item in report.channel_metrics
    )


def test_fake_opener_only_diversity_fails_effective_family_gates() -> None:
    _, source_rows = _diversity_fixture("fake-diversity", 1)
    source = source_rows[0]
    rows = tuple(
        replace(
            source,
            artifact_commitment=f"CDIV-{digest({'copy': index})[:18]}",
            matter_commitment=digest({"matter": index}),
            author_commitment=digest({"author": index}),
            body_hash=digest({"body": index}),
            qualified_bundle_hash=digest({"bundle": index}),
            source_compilation_hash=digest({"compilation": index}),
            variant_id=f"V{index}",
        )
        for index in range(10)
    )
    report = _evaluate_corpus_diversity_artifacts(rows)
    codes = {item.code for item in report.findings}
    assert report.passed is False
    assert "effective_family_collapse" in codes
    assert "effective_family_concentration" in codes
    assert "meaningful_presentation_collapse" in codes
    assert "trivial_variant_dominance" in codes


def test_forged_qualified_bundle_cannot_enter_public_diversity_evaluator() -> None:
    inputs, _ = _diversity_fixture("forged-binding", 1)
    source = inputs[0]
    forged_bundle = replace(
        source.bundles[0],
        compilation_hash=digest("forged-compilation"),
    )
    forged_input = replace(
        source,
        bundles=(forged_bundle, *source.bundles[1:]),
    )
    with pytest.raises(ValueError, match="invalid_qualified_persona_channel_batch"):
        evaluate_corpus_diversity((forged_input,))


def test_underpowered_group_reports_insufficient_coverage_not_success_claim() -> None:
    inputs, _ = _diversity_fixture("small-diversity", 1)
    report = evaluate_corpus_diversity(inputs)
    assert report.passed is False
    assert report.eligible_channel_count == 0
    assert report.insufficient_channel_count >= 1
    assert "coverage_insufficient" in {
        item.code for item in report.findings
    }


def test_public_diversity_summary_excludes_process_local_features() -> None:
    inputs, _ = _diversity_fixture("public-diversity", 2)
    report = evaluate_corpus_diversity(inputs)
    text = canonical_json(report.public_summary()).lower()
    for forbidden in (
        "semantic_skeleton_tokens",
        "style_operation_ids",
        "nonassertive_block",
        "author_commitment",
        "organization_commitment",
        "matter_commitment",
        "qualified_bundle_hash",
        "source_compilation_hash",
        "body_hash",
        "assertion_positions",
        "effective_voice_signature",
        "effective_geometry_signature",
    ):
        assert forbidden not in text
    assert '"human_realism_validated":false' in text
    assert '"native_fidelity_validated":false' in text
    assert '"bodies_included":false' in text

