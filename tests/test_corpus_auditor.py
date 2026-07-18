from __future__ import annotations

from dataclasses import replace

from law_firm_digital_twin.case_compiler import (
    compile_population_fixture,
    qualify_case_compilation,
)
from law_firm_digital_twin.corpus_auditor import (
    audit_persona_channel_corpus,
    build_corpus_audit_artifacts,
)
from law_firm_digital_twin.hashio import canonical_json, digest
from law_firm_digital_twin.persona_channel_renderer import (
    render_persona_channel_batch,
)
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack


def _audit_rows(seed: str, count: int):
    compilations = compile_population_fixture(
        seed=seed,
        count=count,
        rule_pack=placeholder_data_first_rule_pack(),
    )
    receipts = tuple(
        qualify_case_compilation(compilation)
        for compilation in compilations
    )
    return tuple(
        audit_artifact
        for compilation, receipt in zip(
            compilations,
            receipts,
            strict=True,
        )
        for audit_artifact in build_corpus_audit_artifacts(
            compilation,
            receipt,
            render_persona_channel_batch(
                compilation,
                receipt,
            ),
        )
    )


def test_ten_case_persona_channel_corpus_is_unique_replayable_and_safe() -> None:
    first_rows = _audit_rows("g2-scale-v1-ten", 10)
    report = audit_persona_channel_corpus(first_rows)
    assert report == audit_persona_channel_corpus(first_rows)
    assert report.passed is True
    assert report.artifact_count == 90
    assert report.unique_body_count == 90
    assert report.unique_candidate_count == 90
    assert {item.channel_kind for item in report.channel_metrics} == {
        "email",
        "hris_record",
        "policy_document",
        "structured_table",
        "calendar",
        "litigation_record",
        "expert_record",
        "irrelevant_record",
    }
    assert not any(item.severity == "error" for item in report.findings)


def test_corpus_auditor_rejects_exact_body_clones() -> None:
    original = _audit_rows("clone-attack", 1)[0]
    clone = replace(
        original,
        artifact_commitment="CAUDIT-" + digest("clone")[:18],
        projection_hash=digest("clone-projection"),
        bundle_hash=digest("clone-bundle"),
        logical_artifact_commitment=digest("clone-logical"),
        version_id="VERSION-CLONE",
        plan_hash=digest("clone-plan"),
        candidate_hash=digest("clone-candidate"),
    )
    report = audit_persona_channel_corpus((original, clone))
    assert report.passed is False
    assert "exact_body_clone" in {item.code for item in report.findings}


def test_public_audit_summary_contains_no_body_or_actor_identity() -> None:
    rows = _audit_rows("public-audit", 2)
    report = audit_persona_channel_corpus(rows)
    summary_text = canonical_json(report.public_summary()).lower()
    assert '"body":' not in summary_text
    assert "author_commitment" not in summary_text
    assert "matter_commitment" not in summary_text
    assert "assertion_trace" not in summary_text
    assert "bodies_included" in summary_text
    for row in rows:
        assert row.author_commitment.lower() not in summary_text
        assert row.matter_commitment.lower() not in summary_text


def test_structure_and_voice_concentration_repairs_are_measured() -> None:
    report = audit_persona_channel_corpus(_audit_rows("concentration-report", 10))
    assert report.passed is True
    warning_codes = {
        item.code for item in report.findings if item.severity == "warning"
    }
    assert "structure_concentration" not in warning_codes
    assert "voice_signature_concentration" in warning_codes
    assert all(
        item.unique_structure_count >= 3
        for item in report.channel_metrics
    )
    assert any(
        item.unique_voice_signature_count >= 3
        for item in report.channel_metrics
    )



def test_corpus_auditor_rejects_wrong_parent_content_commitment() -> None:
    parent = _audit_rows("parent-content-attack", 1)[0]
    child = replace(
        parent,
        artifact_commitment="CAUDIT-" + digest("child")[:18],
        version_id="VERSION-CHILD",
        revision=2,
        parent_version_id=parent.version_id,
        parent_content_hash="0" * 64,
        claimed_content_hash=digest("child-content"),
        projection_hash=digest("child-projection"),
        bundle_hash=digest("child-bundle"),
        plan_hash=digest("child-plan"),
        candidate_hash=digest("child-candidate"),
        body_hash=digest("child-body"),
    )
    report = audit_persona_channel_corpus((parent, child))
    assert report.passed is False
    assert "lineage_parent_content_hash_mismatch" in {
        item.code for item in report.findings
    }

