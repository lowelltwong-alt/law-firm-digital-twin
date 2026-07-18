from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .hashio import digest


LoopStatus = Literal["candidate_g2", "design_only", "suspended"]


@dataclass(frozen=True)
class DatasetSplitContract:
    split_unit: str
    grouping_keys: tuple[str, ...]
    train_percent: int
    calibration_percent: int
    test_percent: int
    protected_holdout_percent: int
    seed_policy: str
    leakage_prohibitions: tuple[str, ...]


@dataclass(frozen=True)
class LearningTechnique:
    technique_id: str
    use_here: str
    required_inputs: tuple[str, ...]
    output_kind: str
    limitations: tuple[str, ...]
    qualification_gates: tuple[str, ...]


@dataclass(frozen=True)
class LearningLoopContract:
    loop_id: str
    revision: str
    status: LoopStatus
    decision_improved: str
    observations: tuple[str, ...]
    sealed_labels: tuple[str, ...]
    operating_outputs: tuple[str, ...]
    technique_ids: tuple[str, ...]
    split_contract: DatasetSplitContract
    metrics: tuple[str, ...]
    feedback_destination: str
    evaluator_only_fields: tuple[str, ...]
    promotion_gates: tuple[str, ...]
    rollback_trigger: str
    prohibited_claims: tuple[str, ...]
    stop_conditions: tuple[str, ...]

    @property
    def contract_hash(self) -> str:
        return digest(self)


def default_split_contract() -> DatasetSplitContract:
    return DatasetSplitContract(
        split_unit="sealed_world_id",
        grouping_keys=("case_family_id", "organization_id", "persona_namespace", "seed_lineage"),
        train_percent=60,
        calibration_percent=15,
        test_percent=15,
        protected_holdout_percent=10,
        seed_policy="immutable split seed stored only in evaluation control plane",
        leakage_prohibitions=(
            "same_world_across_splits",
            "persona_namespace_across_splits",
            "thread_or_attachment_across_splits",
            "duplicate_or_superseded_version_across_splits",
            "sealed_label_in_operating_prompt",
            "test_or_holdout_feedback_into_generator",
            "arm_mapping_in_blind_evaluator_export",
        ),
    )


def build_learning_techniques() -> tuple[LearningTechnique, ...]:
    definitions = (
        (
            "probabilistic_classification_and_calibration",
            "Estimate synthetic verdict or design-posture probabilities, then calibrate on a separate split.",
            ("case_features", "sealed_design_outcome"),
            "calibrated_probability_distribution",
            ("synthetic_only", "not_real_world_base_rate", "requires_grouped_holdout", "calibration_can_drift"),
            ("brier_score", "log_loss", "calibration_error", "protected_holdout"),
        ),
        (
            "evidence_ranking_with_hard_negatives",
            "Rank responsive/conflict-bearing artifacts amid irrelevant e-discovery and duplicates.",
            ("artifact_projection", "sealed_relevance_label", "conflict_membership"),
            "ranked_artifact_ids_with_uncertainty",
            ("never_drop_on_score_alone", "privilege_is_separate", "noise_can_leak_labels"),
            ("ndcg", "recall_at_k", "conflict_pair_recall", "hard_negative_holdout"),
        ),
        (
            "active_learning_from_checker_failures",
            "Route uncertain or repeatedly failed cells for new synthetic fixtures and human review.",
            ("validator_findings", "uncertainty", "coverage_matrix"),
            "candidate_fixture_queue",
            ("cannot_auto_promote", "failure_frequency_is_not_real_prevalence", "avoid_feedback_monoculture"),
            ("coverage_gain", "failure_reproduction", "human_disposition"),
        ),
        (
            "curriculum_and_adversarial_generation",
            "Increase difficulty through controlled noise, missingness, conflicts, and uphill cases after easier gates pass.",
            ("population_axes", "prior_gate_receipts", "complexity_budget"),
            "next_difficulty_blueprints",
            ("never_weaken_gates", "bounded_complexity", "preserve_base_distribution"),
            ("coverage_balance", "difficulty_monotonicity", "replay", "repair_rate"),
        ),
        (
            "representation_clustering_and_drift",
            "Detect template collapse, near duplicates, voice convergence, and organization/channel drift.",
            ("artifact_features", "author_channel_relationship_groups"),
            "cluster_and_drift_findings",
            ("embedding_is_not_truth", "high_author_separability_can_mean_caricature", "qualitative_review_required"),
            ("template_concentration", "near_duplicate_rate", "within_author_drift", "cross_author_collapse"),
        ),
        (
            "uncertainty_and_conformal_sets",
            "Expose bounded uncertainty or candidate sets instead of forcing a single answer.",
            ("calibration_split", "model_scores", "group_keys"),
            "prediction_or_retrieval_set",
            ("coverage_is_split_specific", "exchangeability_is_not_guaranteed", "no_legal_reliance"),
            ("empirical_coverage", "set_size", "group_coverage"),
        ),
        (
            "offline_policy_evaluation_in_simulation",
            "Compare synthetic settlement, mediation, or work-allocation policies under randomized world-owned arms.",
            ("world_events", "randomized_arm_receipt", "policy_decisions", "synthetic_rewards"),
            "paired_policy_evaluation",
            ("simulation_policy_only", "no_real_causal_claim", "blinded_evaluator_required", "world_owns_outcome"),
            ("paired_difference", "synthetic_regret", "budget_effect", "calibration"),
        ),
        (
            "deduplication_and_data_valuation",
            "Measure redundant artifacts and marginal synthetic fixture value before scaling storage.",
            ("content_commitments", "lineage_graph", "gate_outcomes"),
            "duplicate_groups_and_value_candidates",
            ("never_delete_automatically", "semantic_similarity_is_candidate_only", "preserve_lineage"),
            ("exact_duplicate_rate", "near_duplicate_candidate_rate", "marginal_coverage_gain"),
        ),
    )
    return tuple(LearningTechnique(*item) for item in definitions)


def build_learning_loop_registry() -> tuple[LearningLoopContract, ...]:
    split = default_split_contract()
    common_prohibited = (
        "real_world_prediction",
        "legal_advice_or_compliance",
        "real_case_outcome_claim",
        "protected_attribute_causality",
        "unblinded_holdout_tuning",
        "automatic_production_promotion",
        "unadmitted_real_or_private_source_use",
    )
    common_stops = (
        "split_leakage",
        "oracle_leakage",
        "privacy_or_source_boundary",
        "protected_holdout_access",
        "metric_regression",
        "calibration_failure",
        "validation_inconclusive",
    )
    return (
        LearningLoopContract(
            "mock_trial_design_recovery", "1", "design_only",
            "Test whether a blinded mock-trial system recovers world-designed case strength and conflict signals.",
            ("operating_case_record", "mock_juror_votes", "mock_verdict_distribution"),
            ("merits_posture", "designed_conflict_ids", "evidence_direction"),
            ("blinded_verdict_distribution", "uncertainty", "reason_codes"),
            ("probabilistic_classification_and_calibration", "uncertainty_and_conformal_sets"),
            split,
            ("brier_score", "log_loss", "expected_calibration_error", "balanced_case_rank_correlation", "conflict_recovery"),
            "mock_trial_evaluator_candidate",
            ("sealed_design_labels", "arm_mapping", "test_and_holdout_labels"),
            ("deterministic_split_check", "blinded_evaluation", "protected_holdout_pass", "human_promotion"),
            "rollback when holdout calibration or conflict recovery regresses beyond the approved bound",
            common_prohibited, common_stops,
        ),
        LearningLoopContract(
            "settlement_timing_and_value", "1", "design_only",
            "Evaluate when to settle and synthetic value ranges under world-owned outcomes and budgets.",
            ("operating_timeline", "exposure_updates", "billing_events", "policy_decisions"),
            ("synthetic_resolution_value", "world_outcome", "authority_timing"),
            ("blinded_value_range", "recommended_action", "uncertainty", "authority_needed"),
            ("probabilistic_classification_and_calibration", "offline_policy_evaluation_in_simulation", "uncertainty_and_conformal_sets"),
            split,
            ("range_coverage", "median_absolute_error", "synthetic_regret", "budget_effect", "decision_calibration"),
            "settlement_policy_candidate",
            ("world_outcome", "arm_mapping", "holdout_rewards"),
            ("randomization_receipt", "blinded_pairing", "finance_invariants", "protected_holdout_pass", "human_promotion"),
            "rollback on leakage, miscalibration, or worse protected-holdout regret",
            common_prohibited, common_stops,
        ),
        LearningLoopContract(
            "evidence_relevance_and_conflict", "1", "candidate_g2",
            "Improve retrieval of responsive, conflict-bearing evidence amid realistic irrelevant and duplicate material.",
            ("artifact_operating_projection", "query_or_issue_projection", "custody_metadata"),
            ("responsiveness", "conflict_membership", "privilege_separate_label"),
            ("ranked_artifact_ids", "uncertainty", "abstentions"),
            ("evidence_ranking_with_hard_negatives", "active_learning_from_checker_failures", "uncertainty_and_conformal_sets"),
            split,
            ("recall_at_k", "ndcg", "conflict_pair_recall", "irrelevant_false_positive_rate", "privilege_boundary_violations"),
            "evidence_capability_fixture_queue",
            ("sealed_relevance_labels", "conflict_design_purpose", "holdout_labels"),
            ("never_drop_on_score", "privilege_separation", "hard_negative_holdout", "human_fixture_review"),
            "suspend on any privilege/oracle boundary violation or conflict-recall regression",
            common_prohibited, common_stops,
        ),
        LearningLoopContract(
            "voice_document_and_representation", "1", "candidate_g2",
            "Detect voice collapse, template concentration, caricature, and low-substance documents.",
            ("rendered_artifact_features", "persona_channel_relationship_projection", "family_schema_findings"),
            ("protected_template_groups", "known_failure_fixtures", "human_review_labels"),
            ("voice_findings", "fidelity_findings", "representation_findings", "abstentions"),
            ("representation_clustering_and_drift", "active_learning_from_checker_failures", "deduplication_and_data_valuation"),
            split,
            ("template_concentration", "near_duplicate_rate", "substantive_density", "cross_author_collapse", "stereotype_failure_rate"),
            "renderer_and_fixture_candidate_queue",
            ("human_review_labels", "holdout_failure_fixtures"),
            ("qualitative_independent_review", "protected_fixture_pass", "no_classifier_only_promotion", "human_renderer_promotion"),
            "suspend a renderer on template collapse, caricature, or low-substance regression",
            common_prohibited, common_stops,
        ),
        LearningLoopContract(
            "billing_reduction_and_appeal", "1", "design_only",
            "Evaluate synthetic billing narratives, guideline reductions, appeals, recovery, and write-offs.",
            ("time_entries", "synthetic_guideline_contract", "audit_events", "appeal_events"),
            ("reduction_reason", "approved_amount", "appeal_recovery", "write_off"),
            ("reduction_risk", "appeal_candidate", "uncertainty", "finance_reconciliation"),
            ("probabilistic_classification_and_calibration", "offline_policy_evaluation_in_simulation"),
            split,
            ("reduction_calibration", "recovery_calibration", "appeal_precision", "cash_and_ar_invariant_errors"),
            "billing_policy_candidate",
            ("holdout_audit_outcomes", "arm_mapping"),
            ("finance_invariants", "blinded_evaluation", "protected_holdout_pass", "human_promotion"),
            "rollback on any finance invariant failure or protected-holdout regression",
            common_prohibited, common_stops,
        ),
        LearningLoopContract(
            "generator_curriculum_and_coverage", "1", "candidate_g2",
            "Increase synthetic difficulty and coverage without distorting declared population distributions.",
            ("coverage_matrix", "validator_failures", "repair_receipts", "population_distribution_receipt"),
            ("failure_class", "coverage_gap", "sealed_difficulty_label"),
            ("candidate_blueprint_queue", "candidate_fixture_queue", "coverage_report"),
            ("curriculum_and_adversarial_generation", "active_learning_from_checker_failures", "deduplication_and_data_valuation"),
            split,
            ("cell_coverage", "distribution_divergence", "replay_rate", "repair_rate", "new_failure_reproduction"),
            "campaign_candidate_backlog",
            ("sealed_difficulty_labels", "holdout_failures"),
            ("distribution_preservation", "complexity_budget", "independent_checker", "human_campaign_revision"),
            "rollback when curriculum shifts protected distributions or exceeds complexity/repair ceilings",
            common_prohibited, common_stops,
        ),
    )


def validate_learning_loop_registry(
    loops: tuple[LearningLoopContract, ...],
    techniques: tuple[LearningTechnique, ...] | None = None,
) -> tuple[str, ...]:
    techniques = techniques or build_learning_techniques()
    errors: list[str] = []
    technique_ids = {item.technique_id for item in techniques}
    if len(technique_ids) != len(techniques):
        errors.append("duplicate technique id")
    for technique in techniques:
        if not technique.limitations or not technique.qualification_gates:
            errors.append(f"{technique.technique_id}: limitations or qualification gates missing")
        if not any(term in technique.limitations for term in ("synthetic_only", "simulation_policy_only", "embedding_is_not_truth", "cannot_auto_promote", "never_delete_automatically", "never_weaken_gates", "never_drop_on_score_alone", "coverage_is_split_specific")):
            errors.append(f"{technique.technique_id}: epistemic limitation missing")

    loop_ids = [item.loop_id for item in loops]
    if len(loop_ids) != len(set(loop_ids)):
        errors.append("duplicate loop id")
    for loop in loops:
        split = loop.split_contract
        if split.train_percent + split.calibration_percent + split.test_percent + split.protected_holdout_percent != 100:
            errors.append(f"{loop.loop_id}: split does not total 100")
        if split.split_unit != "sealed_world_id":
            errors.append(f"{loop.loop_id}: split unit must isolate sealed worlds")
        required_groups = {"case_family_id", "organization_id", "persona_namespace", "seed_lineage"}
        if not required_groups.issubset(split.grouping_keys):
            errors.append(f"{loop.loop_id}: grouped split keys incomplete")
        if split.protected_holdout_percent <= 0:
            errors.append(f"{loop.loop_id}: protected holdout missing")
        if "same_world_across_splits" not in split.leakage_prohibitions or "test_or_holdout_feedback_into_generator" not in split.leakage_prohibitions:
            errors.append(f"{loop.loop_id}: split leakage prohibitions incomplete")

        missing = set(loop.technique_ids) - technique_ids
        if missing:
            errors.append(f"{loop.loop_id}: unknown techniques {sorted(missing)}")
        if not loop.sealed_labels or not loop.evaluator_only_fields:
            errors.append(f"{loop.loop_id}: sealed evaluation boundary incomplete")
        if "real_world_prediction" not in loop.prohibited_claims:
            errors.append(f"{loop.loop_id}: real-world claim boundary missing")
        required_claim_boundaries = {"legal_advice_or_compliance", "protected_attribute_causality", "automatic_production_promotion", "unadmitted_real_or_private_source_use"}
        if not required_claim_boundaries.issubset(loop.prohibited_claims):
            errors.append(f"{loop.loop_id}: claim boundaries incomplete")
        if loop.status == "candidate_g2" and not any("human" in gate for gate in loop.promotion_gates):
            errors.append(f"{loop.loop_id}: candidate cannot auto-promote")
        if not loop.rollback_trigger.strip():
            errors.append(f"{loop.loop_id}: rollback trigger missing")
        if "split_leakage" not in loop.stop_conditions or "oracle_leakage" not in loop.stop_conditions:
            errors.append(f"{loop.loop_id}: leakage stops missing")
        if not any("human" in gate for gate in loop.promotion_gates):
            errors.append(f"{loop.loop_id}: human promotion boundary missing")
    return tuple(errors)

