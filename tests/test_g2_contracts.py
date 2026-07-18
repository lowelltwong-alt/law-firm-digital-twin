from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal

import pytest

from law_firm_digital_twin.g2 import (
    G2WorldKernel,
    GateError,
    _build_serialized_cassette,
    _execute_once,
    _execute_serialized_cassette,
 )
from law_firm_digital_twin.hashio import canonical_json
from law_firm_digital_twin.models import Arm, Command, Route
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack
from law_firm_digital_twin.simulation import run_all_routes, run_walking_skeleton
from law_firm_digital_twin.world import build_employment_world


def finding_map(run: dict[str, object]) -> dict[str, dict[str, object]]:
    audit = run["berean_audit"]
    return {item["code"]: item for item in audit["findings"]}


def test_berean_audits_every_required_structural_boundary() -> None:
    run = run_walking_skeleton("alpha", Arm.AI_FIRST, Route.TRIAL_APPEAL)
    findings = finding_map(run)
    assert run["berean_audit"]["passed"] is True
    assert set(findings) == {f"BRN-{index:03d}" for index in range(1, 12)}
    assert all(item["status"] == "pass" for item in findings.values())
    assert "decision_status" in run["berean_audit"]["detected_conflict_ids"]


def test_operating_view_contains_commitments_but_not_oracle_labels() -> None:
    run = run_walking_skeleton("alpha", Arm.TRADITIONAL, Route.DISPOSITIVE)
    matter = run["matter"]
    serialized = repr(matter)
    assert matter["hidden_truth_hash"]
    assert matter["oracle_commitment_hash"]
    assert "target_posture" not in serialized
    assert "target_strength" not in serialized
    assert "declared_conflicts" not in serialized
    assert "employee_reported_wage_and_safety_concerns" not in serialized


def test_actor_knowledge_and_authority_are_separate_frontiers() -> None:
    kernel, _ = _execute_once("alpha", Arm.AI_FIRST, Route.EARLY_SETTLEMENT, run_suffix="test")
    assert kernel.knowledge["hr_witness"] != kernel.knowledge["responsible_lawyer"]
    assert "sealed_world" not in set().union(*kernel.knowledge.values())
    assert kernel.projection.accepted_oracle_reads == 0
    assert kernel.projection.human_gate_bypasses == 0
    assert any(item["reason"] == "oracle_boundary" for item in kernel.denials)
    assert any(
        item["reason"] == "missing_authority" and "matter_opening" in item["missing"]
        for item in kernel.denials
    )


def test_evidence_lifecycle_includes_noise_conflict_and_custody() -> None:
    run = run_walking_skeleton("alpha", Arm.TRADITIONAL, Route.MEDIATION_IMPASSE)
    assert len(run["produced_evidence"]) == 7
    assert run["evidence_status"]["E-NOISE-008"] == "withheld_nonresponsive"
    assert run["evidence_status"]["E-MGREMAIL-004"] == "produced"
    assert run["evidence_status"]["E-HREMAIL-005"] == "produced"
    findings = finding_map(run)
    assert findings["BRN-004"]["status"] == "pass"
    assert findings["BRN-005"]["status"] == "pass"


def test_personas_have_noncollapsed_voices_and_memory_models() -> None:
    run = run_walking_skeleton("alpha", Arm.AI_FIRST, Route.EARLY_SETTLEMENT)
    actors = run["matter"]["actors"]
    voice_signatures = {item["voice"]["signature"] for item in actors.values()}
    memory_models = {
        (
            item["memory"]["encoding"],
            item["memory"]["retrieval"],
            item["memory"]["confidence_calibration"],
        )
        for item in actors.values()
    }
    assert len(actors) >= 9
    assert len(voice_signatures) == len(actors)
    assert len(memory_models) >= 7


def test_deposition_and_expert_are_projection_limited() -> None:
    run = run_walking_skeleton("alpha", Arm.AI_FIRST, Route.TRIAL_APPEAL)
    assert run["deposition"]["oracle_material_used"] is False
    assert "exact hour" in " ".join(run["deposition"]["answers"])
    assert run["expert_opinion"]["oracle_material_used"] is False
    assert run["expert_opinion"]["independence_attested"] is True
    produced_ids = {item["artifact_id"] for item in run["produced_evidence"]}
    assert set(run["expert_opinion"]["source_artifact_ids"]).issubset(produced_ids)


def test_route_branches_have_distinct_milestones_and_world_owned_outcome() -> None:
    milestones = {}
    outcomes = {}
    for route in Route:
        traditional = run_walking_skeleton("alpha", Arm.TRADITIONAL, route)
        ai_first = run_walking_skeleton("alpha", Arm.AI_FIRST, route)
        milestones[route.value] = tuple(traditional["resolution_milestones"])
        outcomes[route.value] = traditional["resolution_outcome"]
        assert traditional["resolution_outcome"] == ai_first["resolution_outcome"]
        assert finding_map(traditional)["BRN-011"]["status"] == "pass"
    assert len(set(milestones.values())) == len(Route)
    assert len(set(outcomes.values())) == 1


def test_billing_reduction_appeal_payment_and_close_reconcile() -> None:
    run = run_walking_skeleton("alpha", Arm.TRADITIONAL, Route.DISPOSITIVE)
    finance = run["finance"]
    assert finance["appeal_recovery"] == Decimal("20.00")
    assert finance["accounts_receivable"] == Decimal("0.00")
    assert finance["submitted"] == finance["approved"] + finance["reduced"]
    assert run["finance_errors"] == []
    assert set(run["close_conditions"]) == {
        "conflict_history_updated",
        "final_report_delivered",
        "finance_reconciled",
        "procedural_complete",
        "retention_scheduled",
    }


def test_replay_and_cassettes_are_stable_across_multiple_seeds() -> None:
    for seed in ("alpha", "bravo", "charlie"):
        run = run_walking_skeleton(seed, Arm.AI_FIRST, Route.TRIAL_APPEAL)
        assert run["replay_verified"] is True
        assert run["event_hash"]
        assert run["projection_hash"]
        assert run["cassette_hash"]
        assert run["command_cassette_hash"]


def test_treatment_blind_comparison_omits_mapping_and_arm_names() -> None:
    result = run_all_routes("alpha")
    assert len(result["treatment_blind_comparisons"]) == 4
    for comparison in result["treatment_blind_comparisons"]:
        assert comparison["treatment_mapping_disclosed"] is False
        assert "synthetic" in comparison["label"]
        assert "non-predictive" in comparison["label"]
        assert {item["blind_label"] for item in comparison["records"]} == {"arm_a", "arm_b"}
        assert all("arm" not in item for item in comparison["records"])


def test_seeded_case_population_contains_varied_strength_postures() -> None:
    pack = placeholder_data_first_rule_pack()
    worlds = [build_employment_world(f"population-{index}", pack).sealed for index in range(60)]
    postures = {world.target_posture for world in worlds}
    strengths = {world.target_strength for world in worlds}
    assert postures == {"defense_favorable", "claimant_favorable", "balanced"}
    assert strengths == {28, 50, 72}


def test_kernel_owned_verb_policy_rejects_forged_empty_requirements() -> None:
    bundle = build_employment_world("authority-hostile", placeholder_data_first_rule_pack())
    kernel = G2WorldKernel(
        run_id="RUN-hostile-authority",
        bundle=bundle,
        arm=Arm.AI_FIRST,
        route=Route.EARLY_SETTLEMENT,
    )
    forged_role = Command(
        command_id="CMD-FORGE-ROLE",
        verb="open_matter",
        actor_id="intake_coordinator",
        role_id="intake",
        matter_id=bundle.matter.matter_id,
        payload={},
    )
    with pytest.raises(GateError, match="verb_role_forbidden"):
        kernel.submit(forged_role)

    forged_requirements = Command(
        command_id="CMD-FORGE-REQUIREMENTS",
        verb="open_matter",
        actor_id="responsible_lawyer",
        role_id="lawyer",
        matter_id=bundle.matter.matter_id,
        payload={},
    )
    with pytest.raises(GateError, match="missing_authority"):
        kernel.submit(forged_requirements)


def test_deadline_dual_control_uses_distinct_actors_and_calculators() -> None:
    kernel, _ = _execute_once("deadline-hostile", Arm.AI_FIRST, Route.DISPOSITIVE, run_suffix="test")
    audit = kernel.projection.deadline_audit
    assert audit["primary_actor"] == "docketing_specialist"
    assert audit["secondary_actor"] == "deadline_reviewer"
    assert audit["primary_actor"] != audit["secondary_actor"]
    assert audit["primary_calculator"] != audit["secondary_calculator"]
    assert kernel.projection.deadline_proposal == kernel.projection.deadlines


def test_custody_hash_authenticates_the_actual_artifact_content() -> None:
    kernel, _ = _execute_once("custody-hostile", Arm.TRADITIONAL, Route.TRIAL_APPEAL, run_suffix="test")
    inventory = {item.artifact_id: item for item in kernel.bundle.matter.evidence_inventory}
    for artifact_id in kernel.projection.produced_artifact_ids:
        observed = {step["object_hash"] for step in kernel.projection.custody_log[artifact_id]}
        assert observed == {inventory[artifact_id].content_hash}


def test_serialized_cassette_rejects_tampered_artifact_commitment() -> None:
    serialized = _build_serialized_cassette("tamper", Arm.AI_FIRST, Route.EARLY_SETTLEMENT)
    record = json.loads(serialized)
    record["artifact_commitments"][0]["content_hash"] = "0" * 64
    with pytest.raises(GateError, match="artifact commitment mismatch"):
        _execute_serialized_cassette(canonical_json(record), run_suffix="tampered")


def test_evaluator_export_cannot_be_joined_to_an_arm_mapping_in_bundle() -> None:
    result = run_all_routes("blind-hostile")
    serialized = canonical_json(result)
    operational = [
        run_walking_skeleton("blind-hostile", arm, route)
        for arm in (Arm.TRADITIONAL, Arm.AI_FIRST)
        for route in Route
    ]
    assert '"arm"' not in serialized
    assert "traditional" not in serialized
    assert "ai_first" not in serialized
    assert all("blind_label" in run for run in result["runs"])
    assert all(run["event_hash"] not in serialized for run in operational)
    forbidden = {"event_hash", "projection_hash", "cassette_hash", "finance", "treatment_metrics", "work_value"}
    assert all(forbidden.isdisjoint(run) for run in result["runs"])
    for comparison in result["treatment_blind_comparisons"]:
        assert comparison["paired_unordered_metrics"]["mapping_to_labels"] == "withheld"
        assert all("work_value" not in record for record in comparison["records"])


def test_all_public_outputs_remain_synthetic_and_nonpredictive() -> None:
    result = run_all_routes("alpha")
    assert result["synthetic_non_predictive"] is True
    assert all(run["synthetic_non_predictive"] is True for run in result["runs"])
    assert all(run["jurisdiction_label"] == "DATA_FIRST_PENDING" for run in result["runs"])
