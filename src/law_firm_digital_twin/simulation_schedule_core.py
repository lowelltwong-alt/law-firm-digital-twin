from __future__ import annotations

import json
from dataclasses import replace

from .hashio import canonical_json, digest
from .simulation_schedule_contracts import (
    QueueDecision,
    REFERENCE_SCHEDULER_REVISION,
    SCHEDULE_NORMALIZATION_REVISION,
    SCHEDULER_CORE_REVISION,
    ScheduledCommandProposal,
    SchedulerResourceSpec,
    SchedulerTrace,
    SimulationScheduleManifest,
)


REFERENCE_ADAPTER_ID = "scheduler.reference_integer_ticks"

RESOURCE_CLASSES = (
    "intake_operations",
    "conflicts_operations",
    "responsible_counsel",
    "docketing_operations",
    "independent_deadline_review",
    "litigation_support",
    "billing_operations",
    "carrier_review",
)

ROLE_RESOURCE = {
    "intake": "intake_operations",
    "conflicts": "conflicts_operations",
    "lawyer": "responsible_counsel",
    "docketing": "docketing_operations",
    "deadline_reviewer": "independent_deadline_review",
    "paralegal": "litigation_support",
    "billing": "billing_operations",
    "carrier": "carrier_review",
}

VERB_SCHEDULING_CLASS = {
    "receive_referral": "intake_work",
    "submit_conflict_result": "conflicts_work",
    "record_lawyer_gate": "authority_review_work",
    "open_matter": "matter_opening_work",
    "calculate_deadlines": "deadline_calculation_work",
    "verify_deadlines": "deadline_verification_work",
    "issue_preservation": "preservation_work",
    "collect_evidence": "collection_work",
    "review_evidence": "evidence_review_work",
    "produce_discovery": "production_work",
    "take_deposition": "deposition_support_work",
    "retain_expert": "expert_coordination_work",
    "settle_case": "resolution_work",
    "mediate_to_impasse": "resolution_work",
    "resolve_dispositive": "resolution_work",
    "try_and_appeal": "resolution_work",
    "record_time": "timekeeping_work",
    "submit_invoice": "billing_submission_work",
    "carrier_audit": "carrier_audit_work",
    "appeal_reduction": "billing_appeal_work",
    "apply_payment": "payment_processing_work",
    "finalize_closeout": "closeout_work",
    "close_matter": "closure_work",
    "read_oracle": "boundary_probe_work",
}

SERVICE_TICKS = {
    "intake_work": 2,
    "conflicts_work": 2,
    "authority_review_work": 1,
    "matter_opening_work": 1,
    "deadline_calculation_work": 2,
    "deadline_verification_work": 2,
    "preservation_work": 2,
    "collection_work": 4,
    "evidence_review_work": 5,
    "production_work": 3,
    "deposition_support_work": 4,
    "expert_coordination_work": 4,
    "resolution_work": 3,
    "timekeeping_work": 1,
    "billing_submission_work": 1,
    "carrier_audit_work": 1,
    "billing_appeal_work": 1,
    "payment_processing_work": 1,
    "closeout_work": 1,
    "closure_work": 1,
    "boundary_probe_work": 1,
}

ALLOWED_SCHEDULING_CLASSES = frozenset(SERVICE_TICKS)


def default_scheduler_resources() -> tuple[SchedulerResourceSpec, ...]:
    return tuple(
        SchedulerResourceSpec(resource_class=value, capacity=1)
        for value in RESOURCE_CLASSES
    )


def validate_schedule_manifest(
    manifest: SimulationScheduleManifest,
) -> tuple[str, ...]:
    errors: list[str] = []
    if manifest.scheduler_core_revision != SCHEDULER_CORE_REVISION:
        errors.append("SCH-001:core_revision_mismatch")
    if manifest.normalization_revision != SCHEDULE_NORMALIZATION_REVISION:
        errors.append("SCH-002:normalization_revision_mismatch")
    if not manifest.route_blind or manifest.source_bodies_included:
        errors.append("SCH-003:information_boundary_invalid")
    if (
        manifest.external_io
        or manifest.canonical_time_authority
        or manifest.world_truth_write
        or manifest.branch_authority
        or manifest.outcome_authority
    ):
        errors.append("SCH-004:authority_boundary_invalid")
    if len(manifest.source_cassette_commitment) != 64 or len(manifest.matter_commitment) != 64:
        errors.append("SCH-005:commitment_shape_invalid")
    resources = {item.resource_class: item for item in manifest.resources}
    if len(resources) != len(manifest.resources):
        errors.append("SCH-006:duplicate_resource")
    if set(resources) != set(RESOURCE_CLASSES):
        errors.append("SCH-007:resource_coverage_invalid")
    for item in manifest.resources:
        if (
            type(item.capacity) is not int
            or item.capacity <= 0
            or item.capacity > 16
            or item.queue_policy != "deterministic_fifo"
            or not item.non_preemptive
        ):
            errors.append(f"SCH-008:{item.resource_class}:resource_policy_invalid")
    if not manifest.proposals or len(manifest.proposals) > 1000:
        errors.append("SCH-009:proposal_count_invalid")
    proposal_ids = tuple(item.proposal_id for item in manifest.proposals)
    ordinals = tuple(item.submission_ordinal for item in manifest.proposals)
    commitments = tuple(item.command_commitment for item in manifest.proposals)
    tie_keys = tuple(item.tie_break_key for item in manifest.proposals)
    if len(proposal_ids) != len(set(proposal_ids)):
        errors.append("SCH-010:duplicate_proposal_id")
    if len(ordinals) != len(set(ordinals)) or tuple(sorted(ordinals)) != tuple(range(1, len(ordinals) + 1)):
        errors.append("SCH-011:submission_ordinal_invalid")
    if len(commitments) != len(set(commitments)):
        errors.append("SCH-012:duplicate_command_commitment")
    if len(tie_keys) != len(set(tie_keys)):
        errors.append("SCH-013:duplicate_tie_break_key")
    for item in manifest.proposals:
        if item.matter_commitment != manifest.matter_commitment:
            errors.append(f"SCH-014:{item.proposal_id}:cross_matter_proposal")
        if item.source_cassette_commitment != manifest.source_cassette_commitment:
            errors.append(f"SCH-015:{item.proposal_id}:cassette_binding_mismatch")
        if item.scheduling_class not in ALLOWED_SCHEDULING_CLASSES:
            errors.append(f"SCH-016:{item.proposal_id}:scheduling_class_invalid")
        if item.resource_class not in resources:
            errors.append(f"SCH-017:{item.proposal_id}:resource_class_invalid")
        if (
            type(item.ready_tick) is not int
            or type(item.service_ticks) is not int
            or item.ready_tick < 0
            or item.service_ticks <= 0
            or item.service_ticks > manifest.max_finish_tick
        ):
            errors.append(f"SCH-018:{item.proposal_id}:tick_value_invalid")
        if type(item.priority) is not int or item.priority < 0 or item.priority > 100:
            errors.append(f"SCH-019:{item.proposal_id}:priority_invalid")
        if item.payload_included or item.kernel_acceptance_claimed:
            errors.append(f"SCH-020:{item.proposal_id}:proposal_authority_invalid")
        if item.expected_disposition not in {"accepted", "denied_boundary_probe"}:
            errors.append(f"SCH-021:{item.proposal_id}:disposition_invalid")
    if manifest.max_wait_ticks <= 0 or manifest.max_finish_tick <= 0:
        errors.append("SCH-022:liveness_ceiling_invalid")
    expected_id = f"SCHED-MANIFEST-{digest({'cassette': manifest.source_cassette_commitment, 'matter': manifest.matter_commitment, 'resources': manifest.resources, 'proposals': manifest.proposals, 'max_wait': manifest.max_wait_ticks, 'max_finish': manifest.max_finish_tick, 'core': manifest.scheduler_core_revision, 'normalization': manifest.normalization_revision})[:18]}"
    if manifest.manifest_id != expected_id:
        errors.append("SCH-023:manifest_id_invalid")
    forbidden = (
        "early_settlement",
        "mediation_impasse",
        "trial_appeal",
        "target_posture",
        "resolution_outcome",
        "settlement_amount",
        "verdict",
        "evaluator_case_id",
        "world_namespace",
        "matter_namespace",
        "oracle_material",
    )
    text = canonical_json(manifest).lower()
    for value in forbidden:
        if value in text:
            errors.append(f"SCH-024:forbidden_scheduler_content:{value}")
    return tuple(errors)


def build_g2_schedule_manifest(
    serialized_cassette: str,
    *,
    resources: tuple[SchedulerResourceSpec, ...] | None = None,
    max_wait_ticks: int = 100,
    max_finish_tick: int = 1000,
) -> SimulationScheduleManifest:
    try:
        cassette = json.loads(serialized_cassette)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("schedule_cassette_json_invalid") from exc
    if cassette.get("revision") != "g2_attempt_cassette_v2":
        raise ValueError("schedule_cassette_revision_invalid")
    attempts = cassette.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        raise ValueError("schedule_cassette_attempts_invalid")
    source_commitment = digest(cassette)
    matter_ids: set[str] = set()
    raw_rows: list[tuple[dict[str, object], dict[str, object], str]] = []
    for entry in attempts:
        if not isinstance(entry, dict) or not isinstance(entry.get("command"), dict):
            raise ValueError("schedule_cassette_attempt_invalid")
        command = dict(entry["command"])
        matter_id = str(command.get("matter_id", ""))
        if not matter_id:
            raise ValueError("schedule_cassette_matter_missing")
        matter_ids.add(matter_id)
        expected = str(entry.get("expected", ""))
        if expected not in {"accepted", "denied"}:
            raise ValueError("schedule_cassette_disposition_invalid")
        raw_rows.append((entry, command, matter_id))
    if len(matter_ids) != 1:
        raise ValueError("schedule_cassette_cross_matter")
    matter_id = next(iter(matter_ids))
    matter_commitment = digest({"matter_id": matter_id, "surface": "scheduler_only"})
    proposals: list[ScheduledCommandProposal] = []
    for ordinal, (entry, command, _) in enumerate(raw_rows, start=1):
        verb = str(command.get("verb", ""))
        role_id = str(command.get("role_id", ""))
        expected = str(entry["expected"])
        if expected == "denied":
            scheduling_class = "boundary_probe_work"
            disposition = "denied_boundary_probe"
            priority = 0
        else:
            scheduling_class = VERB_SCHEDULING_CLASS.get(verb, "")
            disposition = "accepted"
            priority = 10
        resource_class = ROLE_RESOURCE.get(role_id, "")
        if not scheduling_class or not resource_class:
            raise ValueError("schedule_cassette_command_not_mappable")
        command_commitment = digest(command)
        proposal_payload = {
            "cassette": source_commitment,
            "matter": matter_commitment,
            "command": command_commitment,
            "ordinal": ordinal,
            "class": scheduling_class,
        }
        proposal_id = f"SPROP-{digest(proposal_payload)[:18]}"
        proposals.append(
            ScheduledCommandProposal(
                proposal_id=proposal_id,
                matter_commitment=matter_commitment,
                command_commitment=command_commitment,
                scheduling_class=scheduling_class,
                ready_tick=(ordinal - 1) // 2,
                service_ticks=SERVICE_TICKS[scheduling_class],
                resource_class=resource_class,
                priority=priority,
                submission_ordinal=ordinal,
                tie_break_key=f"{ordinal:04d}:{proposal_id}",
                expected_disposition=disposition,  # type: ignore[arg-type]
                source_cassette_commitment=source_commitment,
            )
        )
    resource_specs = resources or default_scheduler_resources()
    payload = {
        "cassette": source_commitment,
        "matter": matter_commitment,
        "resources": resource_specs,
        "proposals": tuple(proposals),
        "max_wait": max_wait_ticks,
        "max_finish": max_finish_tick,
        "core": SCHEDULER_CORE_REVISION,
        "normalization": SCHEDULE_NORMALIZATION_REVISION,
    }
    manifest = SimulationScheduleManifest(
        manifest_id=f"SCHED-MANIFEST-{digest(payload)[:18]}",
        scheduler_core_revision=SCHEDULER_CORE_REVISION,
        normalization_revision=SCHEDULE_NORMALIZATION_REVISION,
        source_cassette_commitment=source_commitment,
        matter_commitment=matter_commitment,
        resources=resource_specs,
        proposals=tuple(proposals),
        max_wait_ticks=max_wait_ticks,
        max_finish_tick=max_finish_tick,
        route_blind=True,
        source_bodies_included=False,
        external_io=False,
        canonical_time_authority=False,
        world_truth_write=False,
        branch_authority=False,
        outcome_authority=False,
    )
    errors = validate_schedule_manifest(manifest)
    if errors:
        raise ValueError(f"schedule_manifest_invalid:{errors}")
    return manifest


def _normalized_proposals(
    manifest: SimulationScheduleManifest,
) -> tuple[ScheduledCommandProposal, ...]:
    errors = validate_schedule_manifest(manifest)
    if errors:
        raise ValueError(f"schedule_manifest_invalid:{errors}")
    return tuple(
        sorted(
            manifest.proposals,
            key=lambda item: (
                item.ready_tick,
                item.priority,
                item.submission_ordinal,
                item.tie_break_key,
                item.proposal_id,
            ),
        )
    )


def plan_with_reference_scheduler(
    manifest: SimulationScheduleManifest,
) -> SchedulerTrace:
    proposals = _normalized_proposals(manifest)
    capacities = {item.resource_class: item.capacity for item in manifest.resources}
    slots = {
        resource_class: [0 for _ in range(capacity)]
        for resource_class, capacity in capacities.items()
    }
    decisions: list[QueueDecision] = []
    for deterministic_ordinal, proposal in enumerate(proposals, start=1):
        resource_slots = slots[proposal.resource_class]
        slot_index = min(
            range(len(resource_slots)),
            key=lambda index: (resource_slots[index], index),
        )
        start = max(proposal.ready_tick, resource_slots[slot_index])
        finish = start + proposal.service_ticks
        wait = start - proposal.ready_tick
        if wait > manifest.max_wait_ticks:
            raise ValueError("schedule_starvation_ceiling_exceeded")
        if finish > manifest.max_finish_tick:
            raise ValueError("schedule_finish_ceiling_exceeded")
        resource_slots[slot_index] = finish
        decisions.append(
            QueueDecision(
                proposal_id=proposal.proposal_id,
                scheduling_class=proposal.scheduling_class,
                resource_class=proposal.resource_class,
                planned_start_tick=start,
                planned_finish_tick=finish,
                deterministic_ordinal=deterministic_ordinal,
                expected_disposition=proposal.expected_disposition,
                kernel_acceptance=False,
            )
        )
    semantics_hash = digest(tuple(decisions))
    payload = {
        "adapter_id": REFERENCE_ADAPTER_ID,
        "adapter_revision": REFERENCE_SCHEDULER_REVISION,
        "runtime_version": "python-integer-reference-v1",
        "manifest_hash": manifest.manifest_hash,
        "semantics": semantics_hash,
    }
    return SchedulerTrace(
        trace_id=f"SCHED-TRACE-{digest(payload)[:18]}",
        adapter_id=REFERENCE_ADAPTER_ID,
        adapter_revision=REFERENCE_SCHEDULER_REVISION,
        runtime_version="python-integer-reference-v1",
        scheduler_core_revision=SCHEDULER_CORE_REVISION,
        normalization_revision=SCHEDULE_NORMALIZATION_REVISION,
        manifest_hash=manifest.manifest_hash,
        decisions=tuple(decisions),
        decision_semantics_hash=semantics_hash,
        runtime_adapter_executed=False,
        external_io=False,
        kernel_acceptance_claimed=False,
        canonical_time_authority=False,
        world_truth_validated=False,
        branch_authority=False,
        outcome_authority=False,
        canonical_admission=False,
    )


def rebuild_manifest_with_proposals(
    manifest: SimulationScheduleManifest,
    proposals: tuple[ScheduledCommandProposal, ...],
) -> SimulationScheduleManifest:
    payload = {
        "cassette": manifest.source_cassette_commitment,
        "matter": manifest.matter_commitment,
        "resources": manifest.resources,
        "proposals": proposals,
        "max_wait": manifest.max_wait_ticks,
        "max_finish": manifest.max_finish_tick,
        "core": manifest.scheduler_core_revision,
        "normalization": manifest.normalization_revision,
    }
    return replace(
        manifest,
        manifest_id=f"SCHED-MANIFEST-{digest(payload)[:18]}",
        proposals=proposals,
    )

