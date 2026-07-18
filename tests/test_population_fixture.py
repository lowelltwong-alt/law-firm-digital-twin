from __future__ import annotations

from collections import Counter
from pathlib import Path

from law_firm_digital_twin.case_compiler import (
    build_public_corpus_manifest,
    build_public_blueprint_receipts,
    compile_population_fixture,
    validate_case_compilation,
)
from law_firm_digital_twin.case_manifest import build_population_blueprints
from law_firm_digital_twin.hashio import canonical_json
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack


def test_ten_case_fixture_is_deterministic_varied_and_isolated() -> None:
    pack = placeholder_data_first_rule_pack()
    first = compile_population_fixture(
        seed="g2-scale-v1-ten",
        count=10,
        rule_pack=pack,
    )
    replay = compile_population_fixture(
        seed="g2-scale-v1-ten",
        count=10,
        rule_pack=pack,
    )
    assert first == replay
    assert len(first) == 10
    assert len({item.compilation_id for item in first}) == 10
    assert len({item.sealed.world_namespace for item in first}) == 10
    assert len({item.sealed.matter_namespace for item in first}) == 10
    assert all(validate_case_compilation(item).passed for item in first)
    assert all(item.operating.case_family_id == "employment_defense_g2" for item in first)
    assert all(len(item.artifact_plans) == 9 for item in first)


def test_ten_case_fixture_covers_multiple_case_strengths_and_shapes() -> None:
    blueprints = build_population_blueprints("g2-scale-v1-ten", 10)
    by_axis = {
        axis_id: Counter(dict(item.sealed_axis_labels)[axis_id] for item in blueprints)
        for axis_id in (
            "merits_posture",
            "evidence_shape",
            "procedural_quality",
            "representation_quality",
            "resolution_track",
        )
    }
    assert len(by_axis["merits_posture"]) >= 3
    assert len(by_axis["evidence_shape"]) >= 4
    assert len(by_axis["procedural_quality"]) >= 2
    assert len(by_axis["representation_quality"]) >= 3
    assert len(by_axis["resolution_track"]) >= 4
    assert sum(by_axis["merits_posture"].values()) == 10


def test_public_ten_case_manifest_contains_no_sealed_training_labels() -> None:
    compilations = compile_population_fixture(
        seed="g2-scale-v1-public",
        count=10,
        rule_pack=placeholder_data_first_rule_pack(),
    )
    manifest = build_public_corpus_manifest(compilations)
    text = canonical_json(manifest).lower()
    assert manifest["case_count"] == 10
    assert len(manifest["cases"]) == 10
    assert len({item["public_case_id"] for item in manifest["cases"]}) == 10
    for forbidden in (
        "merits_posture",
        "evidence_shape",
        "procedural_quality",
        "representation_quality",
        "resolution_track",
        "defense_favorable",
        "claimant_favorable",
        "balanced",
        "design_labels",
        "conflict_specs",
        "fact_commitments",
        "source_blueprint_commitment",
    ):
        assert forbidden not in text


def test_no_plan_persona_or_staged_id_crosses_ten_case_namespaces() -> None:
    compilations = compile_population_fixture(
        seed="g2-scale-v1-isolation",
        count=10,
        rule_pack=placeholder_data_first_rule_pack(),
    )
    plan_ids: set[str] = set()
    persona_ids: set[str] = set()
    staged_ids: set[str] = set()
    for compilation in compilations:
        current_plans = {item.plan_id for item in compilation.artifact_plans}
        current_personas = {item.state_id for item in compilation.persona_states}
        current_staged = {
            item.staged_artifact_id for item in compilation.staged_artifacts
        }
        assert plan_ids.isdisjoint(current_plans)
        assert persona_ids.isdisjoint(current_personas)
        assert staged_ids.isdisjoint(current_staged)
        plan_ids.update(current_plans)
        persona_ids.update(current_personas)
        staged_ids.update(current_staged)



def test_checked_in_fixture_matches_deterministic_builder() -> None:
    seed = "g2-scale-v1-ten"
    blueprints = build_population_blueprints(seed, 10)
    compilations = compile_population_fixture(
        seed=seed,
        count=10,
        rule_pack=placeholder_data_first_rule_pack(),
    )
    root = Path(__file__).resolve().parents[1] / "generated" / "g2-scale-v1"
    assert (root / "blueprints.json").read_text(encoding="utf-8") == (
        canonical_json(build_public_blueprint_receipts(blueprints)) + "\n"
    )
    assert (root / "corpus-manifest.json").read_text(encoding="utf-8") == (
        canonical_json(build_public_corpus_manifest(compilations)) + "\n"
    )


