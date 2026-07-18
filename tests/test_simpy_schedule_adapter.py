from __future__ import annotations

import inspect
from dataclasses import replace

import pytest

from law_firm_digital_twin.g2 import build_g2_attempt_cassette
from law_firm_digital_twin.hashio import canonical_json, digest
from law_firm_digital_twin.models import Arm, Route
from law_firm_digital_twin.simpy_schedule_adapter import SimPyScheduleAdapter
from law_firm_digital_twin.simulation_schedule_contracts import (
    SIMPY_QUALIFIED_VERSION,
)
from law_firm_digital_twin.simulation_schedule_core import (
    build_g2_schedule_manifest,
    plan_with_reference_scheduler,
    rebuild_manifest_with_proposals,
)
from law_firm_digital_twin.simulation_schedule_validator import (
    build_kernel_noninterference_evidence,
    qualify_simpy_schedule_adapter,
    validate_scheduler_trace,
)


@pytest.fixture(scope="module")
def serialized() -> str:
    return build_g2_attempt_cassette(
        "simpy-qualification", Arm.AI_FIRST, Route.TRIAL_APPEAL
    )


@pytest.fixture(scope="module")
def manifest(serialized: str):
    return build_g2_schedule_manifest(serialized)


def test_manifest_is_opaque_route_blind_and_non_authoritative(manifest) -> None:
    text = canonical_json(manifest).lower()
    assert "trial_appeal" not in text
    assert "early_settlement" not in text
    assert "settlement_amount" not in text
    assert all(not item.payload_included for item in manifest.proposals)
    assert manifest.route_blind
    assert not manifest.world_truth_write
    assert not manifest.canonical_time_authority
    assert not manifest.branch_authority
    assert not manifest.outcome_authority


def test_simpy_matches_protected_integer_reference_exactly(manifest) -> None:
    reference = plan_with_reference_scheduler(manifest)
    runtime = SimPyScheduleAdapter().plan(manifest)
    assert runtime.runtime_version == SIMPY_QUALIFIED_VERSION
    assert runtime.decisions == reference.decisions
    assert runtime.decision_semantics_hash == reference.decision_semantics_hash
    assert validate_scheduler_trace(manifest, runtime) == ()


def test_simpy_replay_is_byte_semantically_deterministic(manifest) -> None:
    adapter = SimPyScheduleAdapter()
    assert adapter.plan(manifest) == adapter.plan(manifest)


def test_input_permutation_cannot_change_decisions(manifest) -> None:
    reversed_manifest = rebuild_manifest_with_proposals(
        manifest, tuple(reversed(manifest.proposals))
    )
    original = SimPyScheduleAdapter().plan(manifest)
    reversed_trace = SimPyScheduleAdapter().plan(reversed_manifest)
    assert original.decisions == reversed_trace.decisions
    assert original.decision_semantics_hash == reversed_trace.decision_semantics_hash


def test_resolution_routes_share_one_route_blind_schedule_class() -> None:
    signatures = []
    for route in Route:
        cassette = build_g2_attempt_cassette("route-blind-schedule", Arm.AI_FIRST, route)
        route_manifest = build_g2_schedule_manifest(cassette)
        signatures.append(
            tuple(
                (
                    item.scheduling_class,
                    item.resource_class,
                    item.ready_tick,
                    item.service_ticks,
                    item.priority,
                    item.expected_disposition,
                )
                for item in route_manifest.proposals
            )
        )
    assert len(set(signatures)) == 1
    assert any(item[0] == "resolution_work" for item in signatures[0])


def test_schedule_planning_cannot_change_kernel_or_berean_hashes(
    serialized: str, manifest
) -> None:
    evidence = build_kernel_noninterference_evidence(
        serialized, manifest, SimPyScheduleAdapter()
    )
    assert evidence.validated


def test_qualification_receipt_is_bounded_and_noncanonical(
    serialized: str, manifest
) -> None:
    receipt = qualify_simpy_schedule_adapter(serialized, manifest)
    assert receipt.decisions_equivalent
    assert receipt.resource_capacity_validated
    assert receipt.deterministic_replay_validated
    assert receipt.kernel_noninterference_validated
    assert not receipt.kernel_acceptance_claimed
    assert not receipt.canonical_time_authority
    assert not receipt.world_truth_validated
    assert not receipt.branch_authority
    assert not receipt.outcome_authority
    assert not receipt.canonical_admission


def test_cross_matter_tamper_is_rejected(manifest) -> None:
    attacked = replace(
        manifest.proposals[0], matter_commitment=digest("other-matter")
    )
    attacked_manifest = rebuild_manifest_with_proposals(
        manifest, (attacked, *manifest.proposals[1:])
    )
    with pytest.raises(ValueError, match="cross_matter_proposal"):
        SimPyScheduleAdapter().plan(attacked_manifest)


@pytest.mark.parametrize(
    "field,value,error",
    (
        ("ready_tick", -1, "tick_value_invalid"),
        ("service_ticks", 0, "tick_value_invalid"),
        ("priority", -1, "priority_invalid"),
        ("payload_included", True, "proposal_authority_invalid"),
        ("kernel_acceptance_claimed", True, "proposal_authority_invalid"),
    ),
)
def test_malformed_or_authoritative_proposal_is_rejected(
    manifest, field: str, value: object, error: str
) -> None:
    attacked = replace(manifest.proposals[0], **{field: value})
    attacked_manifest = rebuild_manifest_with_proposals(
        manifest, (attacked, *manifest.proposals[1:])
    )
    with pytest.raises(ValueError, match=error):
        SimPyScheduleAdapter().plan(attacked_manifest)


def test_liveness_ceiling_fails_closed(serialized: str) -> None:
    constrained = build_g2_schedule_manifest(
        serialized, max_wait_ticks=1, max_finish_tick=1000
    )
    with pytest.raises(ValueError, match="starvation_ceiling_exceeded"):
        SimPyScheduleAdapter().plan(constrained)


def test_unqualified_runtime_version_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="simpy_runtime_unqualified"):
        SimPyScheduleAdapter(expected_version="4.1.1")


def test_trace_tamper_is_detected(manifest) -> None:
    trace = SimPyScheduleAdapter().plan(manifest)
    attacked_decision = replace(
        trace.decisions[0], planned_finish_tick=trace.decisions[0].planned_finish_tick + 1
    )
    attacked = replace(
        trace, decisions=(attacked_decision, *trace.decisions[1:])
    )
    errors = validate_scheduler_trace(manifest, attacked)
    assert "STR-005:decision_semantics_hash_invalid" in errors
    assert any(value.endswith("timing_invalid") for value in errors)


def test_adapter_source_has_no_kernel_submit_random_wall_clock_or_uuid() -> None:
    source = inspect.getsource(SimPyScheduleAdapter).lower()
    assert "kernel.submit" not in source
    assert "random" not in source
    assert "datetime" not in source
    assert "time.time" not in source
    assert "uuid" not in source
