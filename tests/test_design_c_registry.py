from __future__ import annotations

from dataclasses import replace

from law_firm_digital_twin.design_c_contracts import (
    DESIGN_C_CONTRACT_REVISION,
    DesignCJobManifest,
    DesignCJobResult,
    JobBudget,
)
from law_firm_digital_twin.design_c_registry import build_design_c_unified_registry
from law_firm_digital_twin.design_c_validator import (
    REQUIRED_STOPS,
    validate_design_c_job_manifest,
    validate_design_c_job_result,
    validate_design_c_registry,
)
from law_firm_digital_twin.hashio import digest


def _manifest() -> DesignCJobManifest:
    return DesignCJobManifest(
        job_id="C010",
        campaign_id="design-c-g0c-spine-v1",
        contract_revision=DESIGN_C_CONTRACT_REVISION,
        objective="Build the proposed typed registry without activating it.",
        non_goals=("canonical_store", "external_effect", "unattended_execution"),
        input_commitments=(("baseline", digest("design-c-baseline-v1")),),
        dependency_hashes=(("constitution", digest("constitution-v1")),),
        output_paths=("src/law_firm_digital_twin/design_c_contracts.py",),
        write_owner="design_c_contract_worker",
        checker_id="design_c_contract_checker",
        idempotency_key="design-c-g0c-spine-v1:C010:r1",
        checkpoint_path="checks/design-c-g0c-spine-v1/C010.json",
        budget=JobBudget(
            max_attempts=2,
            max_repairs=1,
            max_wall_seconds=600,
            max_cost_units=0,
            max_output_bytes=250_000,
        ),
        required_gate_ids=(),
        stop_conditions=tuple(sorted(REQUIRED_STOPS)),
    )


def test_design_c_registry_is_frozen_adopted_and_fail_closed() -> None:
    registry = build_design_c_unified_registry()
    assert validate_design_c_registry(registry) == ()
    assert {item.decision_id for item in registry.decisions} == {
        f"H-{index}" for index in range(1, 13)
    }
    assert {item.asset_id for item in registry.assets} == {
        f"A{index}" for index in range(1, 15)
    }
    assert {item.loop_id for item in registry.loops} == {
        "L0", "L1", "L2", "L3", "L4"
    }
    decisions = {item.decision_id: item for item in registry.decisions}
    assert {
        item.decision_id for item in registry.decisions if item.status == "pending"
    } == {"H-4", "H-8", "H-9", "H-12"}
    assert {
        item.decision_id for item in registry.decisions if item.status == "adopted"
    } == {"H-2", "H-3", "H-5", "H-6", "H-7", "H-10", "H-11"}
    assert registry.baseline_id == "design-c-baseline-v1"
    assert "LFDT_RUNTIME_ROOT" in decisions["H-10"].selected_policy
    assert "separately_pending" in decisions["H-10"].selected_policy
    assert not registry.canonical_activation_authorized
    assert not registry.unattended_execution_authorized


def test_simpy_is_preserved_only_as_optional_nondefault_adapter() -> None:
    registry = build_design_c_unified_registry()
    qualification = registry.runtime_qualifications[0]
    assert qualification.capability_id == "scheduler.simpy_integer_ticks"
    assert qualification.state == "qualified_optional_nondefault"
    assert qualification.runtime_version == "4.1.2"
    assert not qualification.canonical_authority


def test_pending_human_decision_cannot_self_activate() -> None:
    registry = build_design_c_unified_registry()
    decisions = list(registry.decisions)
    decisions[3] = replace(
        decisions[3], status="adopted", selected_policy="self_activated"
    )
    errors = validate_design_c_registry(
        replace(registry, decisions=tuple(decisions))
    )
    assert "DCR-011:H-4:decision_state_invalid" in errors


def test_frozen_baseline_rejects_proposed_obligation() -> None:
    registry = build_design_c_unified_registry()
    attacked = replace(registry.obligations[1], status="proposed")
    errors = validate_design_c_registry(
        replace(
            registry,
            obligations=(
                registry.obligations[0],
                attacked,
                *registry.obligations[2:],
            ),
        )
    )
    assert (
        "DCR-016:DC-O02:frozen_baseline_has_proposed_obligation" in errors
    )

def test_registry_rejects_missing_asset_and_unknown_human_gate() -> None:
    registry = build_design_c_unified_registry()
    missing = replace(registry, assets=registry.assets[:-1])
    assert "DCR-009:asset_coverage_invalid" in validate_design_c_registry(missing)
    attacked = replace(registry.assets[2], human_gate_ids=("H-99",))
    errors = validate_design_c_registry(
        replace(registry, assets=(registry.assets[0], registry.assets[1], attacked, *registry.assets[3:]))
    )
    assert "DCR-014:A3:unknown_human_gate" in errors


def test_registry_rejects_asset_dependency_cycle() -> None:
    registry = build_design_c_unified_registry()
    a1 = replace(registry.assets[0], depends_on=("A2",))
    errors = validate_design_c_registry(
        replace(registry, assets=(a1, *registry.assets[1:]))
    )
    assert "DCR-021:asset_dependency_cycle" in errors


def test_registry_rejects_loop_self_promotion_and_runtime_authority() -> None:
    registry = build_design_c_unified_registry()
    attacked_loop = replace(registry.loops[0], self_promotion=True)
    errors = validate_design_c_registry(
        replace(registry, loops=(attacked_loop, *registry.loops[1:]))
    )
    assert "DCR-017:L0:loop_authority_invalid" in errors
    qualification = replace(
        registry.runtime_qualifications[0], canonical_authority=True
    )
    errors = validate_design_c_registry(
        replace(registry, runtime_qualifications=(qualification,))
    )
    assert any(value.startswith("DCR-018") for value in errors)


def test_job_manifest_passes_portable_fail_closed_contract() -> None:
    manifest = _manifest()
    assert validate_design_c_job_manifest(manifest) == ()
    assert manifest.manifest_hash == manifest.manifest_hash
    assert not manifest.external_effects
    assert not manifest.canonical_truth_write


def test_job_manifest_rejects_self_check_absolute_paths_and_authority() -> None:
    manifest = _manifest()
    attacks = (
        (replace(manifest, checker_id=manifest.write_owner), "DCJ-003:self_checking_job"),
        (replace(manifest, output_paths=("C:/lfdt-data/output.json",)), "DCJ-006:output_scope_invalid"),
        (replace(manifest, external_effects=True), "DCJ-010:authority_boundary_invalid"),
        (replace(manifest, unattended_execution_authorized=True), "DCJ-010:authority_boundary_invalid"),
    )
    for attacked, expected in attacks:
        assert expected in validate_design_c_job_manifest(attacked)


def test_job_manifest_requires_one_repair_and_all_terminal_stops() -> None:
    manifest = _manifest()
    attacked = replace(
        manifest,
        budget=replace(manifest.budget, max_repairs=2),
        stop_conditions=("canary_leak",),
    )
    errors = validate_design_c_job_manifest(attacked)
    assert "DCJ-008:budget_invalid" in errors
    assert "DCJ-009:mandatory_stop_missing" in errors


def test_job_result_is_bound_budgeted_checked_and_noncanonical() -> None:
    manifest = _manifest()
    result = DesignCJobResult(
        result_id="RESULT-C010-r1",
        job_id=manifest.job_id,
        manifest_hash=manifest.manifest_hash,
        state="passed",
        attempt_count=1,
        repair_count=0,
        output_commitments=(("registry", digest("registry")),),
        evidence_commitments=(("focused_tests", digest("tests")),),
        failure_codes=(),
        checker_id=manifest.checker_id,
        checker_passed=True,
        human_gate_ids_satisfied=(),
        cost_units_used=0,
        wall_seconds_used=10,
    )
    assert validate_design_c_job_result(manifest, result) == ()
    assert not result.canonical_admission
    assert not result.self_approved


def test_job_result_rejects_budget_overrun_and_false_pass() -> None:
    manifest = _manifest()
    result = DesignCJobResult(
        result_id="RESULT-C010-r1",
        job_id=manifest.job_id,
        manifest_hash=manifest.manifest_hash,
        state="passed",
        attempt_count=manifest.budget.max_attempts + 1,
        repair_count=manifest.budget.max_repairs + 1,
        output_commitments=(),
        evidence_commitments=(),
        failure_codes=("hidden_failure",),
        checker_id=manifest.write_owner,
        checker_passed=False,
        human_gate_ids_satisfied=(),
        cost_units_used=1,
        wall_seconds_used=manifest.budget.max_wall_seconds + 1,
        canonical_admission=True,
    )
    errors = validate_design_c_job_result(manifest, result)
    assert {
        "DCJR-002:attempt_budget_invalid",
        "DCJR-003:repair_budget_invalid",
        "DCJR-005:wall_budget_invalid",
        "DCJR-006:checker_identity_invalid",
        "DCJR-007:pass_claim_invalid",
        "DCJR-010:result_authority_invalid",
    }.issubset(set(errors))
