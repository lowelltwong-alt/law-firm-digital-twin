from __future__ import annotations

from collections import Counter
from dataclasses import replace

import pytest

from law_firm_digital_twin.case_manifest import (
    PopulationAxis,
    WeightedBucket,
    build_capability_registry,
    build_population_blueprints,
)
from law_firm_digital_twin.hashio import canonical_json, digest
from law_firm_digital_twin.validators import (
    validate_capability_registry,
    validate_population_blueprints,
)


def axis_counts(blueprints: tuple[object, ...], axis_id: str) -> Counter[str]:
    return Counter(dict(item.sealed_axis_labels)[axis_id] for item in blueprints)


def test_capability_registry_passes_its_deterministic_contract() -> None:
    registry = build_capability_registry()
    report = validate_capability_registry(registry)
    assert report.passed is True
    assert report.issues == ()
    assert report.report_hash


def test_case_family_registry_is_broad_but_only_employment_is_active() -> None:
    registry = build_capability_registry()
    families = {item.family_id: item for item in registry.case_families}
    assert set(families) == {
        "employment_defense_g2",
        "medical_malpractice_design",
        "construction_defect_design",
        "premises_liability_design",
        "motor_vehicle_design",
        "trucking_transportation_design",
        "products_liability_design",
        "insurance_coverage_bad_faith_design",
        "software_professional_liability_design",
    }
    assert [item.family_id for item in registry.case_families if item.readiness == "active_g2"] == ["employment_defense_g2"]
    assert all(item.synthetic_only for item in registry.case_families)
    assert all(item.fidelity_level == "G2" for item in registry.case_families)
    assert all(
        "human_case_family_activation" in item.activation_gate
        for item in registry.case_families
        if item.readiness == "design_only"
    )


def test_evidence_matrix_has_typed_gates_and_prohibits_shortcuts() -> None:
    registry = build_capability_registry()
    families = {item.family_id for item in registry.evidence_capabilities}
    employment = next(item for item in registry.case_families if item.family_id == "employment_defense_g2")
    assert set(employment.required_evidence_capabilities) == families
    for capability in registry.evidence_capabilities:
        assert capability.required_fields
        assert capability.validator_ids
        assert capability.protected_fixture_id
        assert capability.escalation_capability_id
        assert "oracle_paraphrase" in capability.prohibited_shortcuts
        assert "random_typo_only_variation" in capability.prohibited_shortcuts
        assert "placeholder_body" in capability.prohibited_shortcuts


def test_persona_contracts_model_context_and_forbid_popular_psychology_as_cause() -> None:
    registry = build_capability_registry()
    dimension_ids = {item.dimension_id for item in registry.persona_dimensions}
    assert {
        "relationships_and_power_distance",
        "memory_process",
        "stress_fatigue_and_workload",
        "knowledge_frontier",
        "change_over_time",
    }.issubset(dimension_ids)
    for dimension in registry.persona_dimensions:
        assert "probabilistic_contextual_influence_only" in dimension.causal_policy
        assert "mbti_as_validated_cause" in dimension.prohibited_uses
        assert "left_right_brain_claim" in dimension.prohibited_uses
        assert "protected_attribute_outcome_rule" in dimension.prohibited_uses


def test_specialist_mesh_is_provider_neutral_and_cannot_write_truth() -> None:
    registry = build_capability_registry()
    classifications = {item.classification for item in registry.specialist_capabilities}
    assert classifications == {"portable_core", "runtime_adapter", "provider_probe"}
    assert all(item.canonical_truth_write is False for item in registry.specialist_capabilities)
    assert all(item.validator_ids for item in registry.specialist_capabilities)
    serialized = canonical_json(registry.specialist_capabilities).lower()
    for forbidden in ("openai", "anthropic", "gpt-", "claude", "cursor", "composer"):
        assert forbidden not in serialized
    assert "private_source_rows" in serialized
    assert "oracle_truth" in serialized


def test_population_of_one_thousand_matches_declared_case_distribution_exactly() -> None:
    blueprints = build_population_blueprints("population-v1", 1000)
    assert axis_counts(blueprints, "merits_posture") == Counter(
        {"defense_favorable": 300, "claimant_favorable": 300, "balanced": 300, "deeply_ambiguous": 100}
    )
    assert axis_counts(blueprints, "procedural_quality") == Counter(
        {
            "merits_progressing": 820,
            "curable_defect": 60,
            "dismissal_without_prejudice": 40,
            "dismissal_with_prejudice": 30,
            "technical_dispute": 50,
        }
    )
    assert axis_counts(blueprints, "representation_quality") == Counter(
        {"well_handled": 550, "uneven": 250, "material_error": 150, "systemic_failure": 50}
    )
    assert validate_population_blueprints(blueprints).passed is True


def test_population_replays_by_seed_and_varies_across_seeds() -> None:
    first = build_population_blueprints("alpha-population", 100)
    replay = build_population_blueprints("alpha-population", 100)
    alternate = build_population_blueprints("bravo-population", 100)
    assert digest(first) == digest(replay)
    assert digest(first) != digest(alternate)
    assert [item.design_id for item in first] == [item.design_id for item in replay]


def test_operating_blueprint_exposes_commitment_not_design_labels() -> None:
    blueprint = build_population_blueprints("sealed-labels", 1)[0]
    operating = canonical_json(blueprint.operating_view()).lower()
    assert blueprint.sealed_commitment_hash in operating
    assert "sealed_axis_labels" not in operating
    assert "design_labels" not in operating
    assert "evidence_direction" not in operating
    assert "authorial target" not in operating


def test_registry_validator_rejects_bad_population_weights() -> None:
    registry = build_capability_registry()
    first_axis = registry.population_axes[0]
    broken_axis = PopulationAxis(
        axis_id=first_axis.axis_id,
        purpose=first_axis.purpose,
        buckets=(
            WeightedBucket("defense_favorable", 99, "bad", "sealed:bad"),
            WeightedBucket("claimant_favorable", 99, "bad", "sealed:bad2"),
        ),
    )
    broken = replace(registry, population_axes=(broken_axis, *registry.population_axes[1:]))
    report = validate_capability_registry(broken)
    assert report.passed is False
    assert any(issue.code == "REG-002" for issue in report.issues)


def test_population_validator_detects_distribution_tampering() -> None:
    blueprints = list(build_population_blueprints("tamper-population", 100))
    first = blueprints[0]
    labels = dict(first.sealed_axis_labels)
    labels["merits_posture"] = "invented_bucket"
    blueprints[0] = replace(first, sealed_axis_labels=tuple(labels.items()))
    report = validate_population_blueprints(tuple(blueprints))
    assert report.passed is False
    assert any(issue.code == "POP-005" for issue in report.issues)


def test_design_only_family_cannot_generate_blueprints() -> None:
    with pytest.raises(ValueError, match="design-only"):
        build_population_blueprints(
            "forbidden-family",
            10,
            case_family_id="medical_malpractice_design",
        )


def test_validator_rejects_a_forged_design_only_family_population() -> None:
    blueprints = list(build_population_blueprints("forged-family", 10))
    blueprints[0] = replace(
        blueprints[0],
        case_family_id="medical_malpractice_design",
    )
    report = validate_population_blueprints(tuple(blueprints))
    assert report.passed is False
    assert any(issue.code == "POP-008" for issue in report.issues)

