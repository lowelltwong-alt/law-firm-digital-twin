from __future__ import annotations

from dataclasses import replace

from law_firm_digital_twin.learning_loops import (
    build_learning_loop_registry,
    build_learning_techniques,
    default_split_contract,
    validate_learning_loop_registry,
)


def test_learning_loop_registry_passes_deterministic_contract() -> None:
    loops = build_learning_loop_registry()
    assert validate_learning_loop_registry(loops) == ()
    assert len(loops) == 6
    assert len(build_learning_techniques()) == 8
    assert all(loop.contract_hash for loop in loops)


def test_split_is_grouped_by_world_and_reserves_a_protected_holdout() -> None:
    split = default_split_contract()
    assert (
        split.train_percent
        + split.calibration_percent
        + split.test_percent
        + split.protected_holdout_percent
        == 100
    )
    assert split.split_unit == "sealed_world_id"
    assert split.protected_holdout_percent == 10
    assert {
        "case_family_id",
        "organization_id",
        "persona_namespace",
        "seed_lineage",
    }.issubset(split.grouping_keys)
    assert "test_or_holdout_feedback_into_generator" in split.leakage_prohibitions


def test_learning_uses_are_bounded_to_synthetic_evaluation() -> None:
    loops = {loop.loop_id: loop for loop in build_learning_loop_registry()}
    assert loops["mock_trial_design_recovery"].status == "design_only"
    assert loops["settlement_timing_and_value"].status == "design_only"
    assert loops["billing_reduction_and_appeal"].status == "design_only"
    assert loops["evidence_relevance_and_conflict"].status == "candidate_g2"
    assert loops["voice_document_and_representation"].status == "candidate_g2"
    assert loops["generator_curriculum_and_coverage"].status == "candidate_g2"
    for loop in loops.values():
        assert "real_world_prediction" in loop.prohibited_claims
        assert "legal_advice_or_compliance" in loop.prohibited_claims
        assert "automatic_production_promotion" in loop.prohibited_claims
        assert "unadmitted_real_or_private_source_use" in loop.prohibited_claims
        assert any("human" in gate for gate in loop.promotion_gates)


def test_requested_techniques_have_explicit_limits_and_qualification_gates() -> None:
    techniques = {item.technique_id: item for item in build_learning_techniques()}
    assert {
        "probabilistic_classification_and_calibration",
        "evidence_ranking_with_hard_negatives",
        "active_learning_from_checker_failures",
        "curriculum_and_adversarial_generation",
        "representation_clustering_and_drift",
        "uncertainty_and_conformal_sets",
        "offline_policy_evaluation_in_simulation",
        "deduplication_and_data_valuation",
    } == set(techniques)
    assert all(item.limitations for item in techniques.values())
    assert all(item.qualification_gates for item in techniques.values())
    assert "no_real_causal_claim" in techniques["offline_policy_evaluation_in_simulation"].limitations
    assert "embedding_is_not_truth" in techniques["representation_clustering_and_drift"].limitations


def test_split_leakage_and_percentage_tampering_are_rejected() -> None:
    loops = list(build_learning_loop_registry())
    split = replace(
        loops[0].split_contract,
        train_percent=71,
        grouping_keys=("case_family_id",),
        protected_holdout_percent=0,
        leakage_prohibitions=(),
    )
    loops[0] = replace(loops[0], split_contract=split)
    errors = validate_learning_loop_registry(tuple(loops))
    assert any("split does not total 100" in error for error in errors)
    assert any("grouped split keys incomplete" in error for error in errors)
    assert any("protected holdout missing" in error for error in errors)
    assert any("split leakage prohibitions incomplete" in error for error in errors)


def test_human_promotion_and_claim_boundaries_cannot_be_removed() -> None:
    loops = list(build_learning_loop_registry())
    loops[2] = replace(
        loops[2],
        promotion_gates=("automatic_metric_gate",),
        prohibited_claims=("real_world_prediction",),
    )
    errors = validate_learning_loop_registry(tuple(loops))
    assert any("claim boundaries incomplete" in error for error in errors)
    assert any("candidate cannot auto-promote" in error for error in errors)
    assert any("human promotion boundary missing" in error for error in errors)


def test_unknown_technique_is_rejected() -> None:
    loops = list(build_learning_loop_registry())
    loops[0] = replace(loops[0], technique_ids=("invented_technique",))
    errors = validate_learning_loop_registry(tuple(loops))
    assert any("unknown techniques" in error for error in errors)



def test_missing_rollback_trigger_is_rejected() -> None:
    loops = list(build_learning_loop_registry())
    loops[0] = replace(loops[0], rollback_trigger="")
    errors = validate_learning_loop_registry(tuple(loops))
    assert any("rollback trigger missing" in error for error in errors)


