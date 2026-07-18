from __future__ import annotations

from dataclasses import dataclass

from .berean import BereanAuditor
from .g2 import execute_g2_attempt_cassette
from .hashio import digest
from .simulation_schedule_contracts import (
    SIMPY_ADAPTER_REVISION,
    SIMPY_QUALIFIED_VERSION,
    SchedulingQualificationReceipt,
    SchedulerTrace,
    SimulationScheduleManifest,
)
from .simulation_schedule_core import plan_with_reference_scheduler
from .simpy_schedule_adapter import SimPyScheduleAdapter


SCHEDULE_CHECKER_REVISION = "simulation-schedule-independent-checker-g2-v1"


@dataclass(frozen=True)
class KernelNoninterferenceEvidence:
    direct_event_hash: str
    post_schedule_event_hash: str
    direct_projection_hash: str
    post_schedule_projection_hash: str
    direct_denial_hash: str
    post_schedule_denial_hash: str
    direct_command_hash: str
    post_schedule_command_hash: str
    direct_berean_hash: str
    post_schedule_berean_hash: str

    @property
    def validated(self) -> bool:
        return (
            self.direct_event_hash == self.post_schedule_event_hash
            and self.direct_projection_hash == self.post_schedule_projection_hash
            and self.direct_denial_hash == self.post_schedule_denial_hash
            and self.direct_command_hash == self.post_schedule_command_hash
            and self.direct_berean_hash == self.post_schedule_berean_hash
        )


def validate_scheduler_trace(
    manifest: SimulationScheduleManifest,
    trace: SchedulerTrace,
) -> tuple[str, ...]:
    errors: list[str] = []
    if trace.manifest_hash != manifest.manifest_hash:
        errors.append("STR-001:manifest_binding_invalid")
    if trace.scheduler_core_revision != manifest.scheduler_core_revision:
        errors.append("STR-002:core_revision_invalid")
    if trace.normalization_revision != manifest.normalization_revision:
        errors.append("STR-003:normalization_revision_invalid")
    if len(trace.decisions) != len(manifest.proposals):
        errors.append("STR-004:decision_count_invalid")
    if trace.decision_semantics_hash != digest(trace.decisions):
        errors.append("STR-005:decision_semantics_hash_invalid")
    if (
        trace.external_io
        or trace.kernel_acceptance_claimed
        or trace.canonical_time_authority
        or trace.world_truth_validated
        or trace.branch_authority
        or trace.outcome_authority
        or trace.canonical_admission
    ):
        errors.append("STR-006:authority_boundary_invalid")

    proposals = {item.proposal_id: item for item in manifest.proposals}
    seen: set[str] = set()
    resource_intervals: dict[str, list[tuple[int, int]]] = {}
    capacities = {item.resource_class: item.capacity for item in manifest.resources}
    for ordinal, decision in enumerate(trace.decisions, start=1):
        proposal = proposals.get(decision.proposal_id)
        if proposal is None or decision.proposal_id in seen:
            errors.append(f"STR-007:{decision.proposal_id}:decision_binding_invalid")
            continue
        seen.add(decision.proposal_id)
        if decision.deterministic_ordinal != ordinal:
            errors.append(f"STR-008:{decision.proposal_id}:ordinal_invalid")
        if (
            decision.scheduling_class != proposal.scheduling_class
            or decision.resource_class != proposal.resource_class
            or decision.expected_disposition != proposal.expected_disposition
            or decision.kernel_acceptance
        ):
            errors.append(f"STR-009:{decision.proposal_id}:proposal_semantics_invalid")
        if (
            decision.planned_start_tick < proposal.ready_tick
            or decision.planned_finish_tick - decision.planned_start_tick
            != proposal.service_ticks
            or decision.planned_start_tick - proposal.ready_tick > manifest.max_wait_ticks
            or decision.planned_finish_tick > manifest.max_finish_tick
        ):
            errors.append(f"STR-010:{decision.proposal_id}:timing_invalid")
        resource_intervals.setdefault(decision.resource_class, []).append(
            (decision.planned_start_tick, decision.planned_finish_tick)
        )

    for resource_class, intervals in resource_intervals.items():
        event_points = sorted({point for interval in intervals for point in interval})
        for point in event_points:
            active = sum(start <= point < finish for start, finish in intervals)
            if active > capacities.get(resource_class, 0):
                errors.append(f"STR-011:{resource_class}:capacity_exceeded")
                break
    return tuple(errors)


def build_kernel_noninterference_evidence(
    serialized_cassette: str,
    manifest: SimulationScheduleManifest,
    adapter: SimPyScheduleAdapter,
) -> KernelNoninterferenceEvidence:
    direct, direct_commands = execute_g2_attempt_cassette(
        serialized_cassette, run_suffix="schedule-direct"
    )
    adapter.plan(manifest)
    post, post_commands = execute_g2_attempt_cassette(
        serialized_cassette, run_suffix="schedule-post"
    )
    return KernelNoninterferenceEvidence(
        direct_event_hash=direct.canonical_event_hash(),
        post_schedule_event_hash=post.canonical_event_hash(),
        direct_projection_hash=direct.projection_hash(),
        post_schedule_projection_hash=post.projection_hash(),
        direct_denial_hash=direct.denial_hash(),
        post_schedule_denial_hash=post.denial_hash(),
        direct_command_hash=digest(direct_commands),
        post_schedule_command_hash=digest(post_commands),
        direct_berean_hash=BereanAuditor().audit(direct).report_hash,
        post_schedule_berean_hash=BereanAuditor().audit(post).report_hash,
    )


def qualify_simpy_schedule_adapter(
    serialized_cassette: str,
    manifest: SimulationScheduleManifest,
    *,
    adapter: SimPyScheduleAdapter | None = None,
) -> SchedulingQualificationReceipt:
    runtime_adapter = adapter or SimPyScheduleAdapter()
    if runtime_adapter.runtime_version != SIMPY_QUALIFIED_VERSION:
        raise ValueError("schedule_runtime_version_unqualified")
    reference = plan_with_reference_scheduler(manifest)
    runtime = runtime_adapter.plan(manifest)
    replay = runtime_adapter.plan(manifest)
    for trace in (reference, runtime, replay):
        errors = validate_scheduler_trace(manifest, trace)
        if errors:
            raise ValueError(f"schedule_trace_invalid:{errors}")
    if runtime.decisions != reference.decisions:
        raise ValueError("schedule_reference_equivalence_failed")
    if replay != runtime:
        raise ValueError("schedule_runtime_replay_failed")
    evidence = build_kernel_noninterference_evidence(
        serialized_cassette, manifest, runtime_adapter
    )
    if not evidence.validated:
        raise ValueError("schedule_kernel_noninterference_failed")
    payload = {
        "manifest": manifest.manifest_hash,
        "reference": reference.trace_hash,
        "runtime": runtime.trace_hash,
        "semantics": runtime.decision_semantics_hash,
        "checker": SCHEDULE_CHECKER_REVISION,
    }
    return SchedulingQualificationReceipt(
        receipt_id=f"SCHED-QUAL-{digest(payload)[:18]}",
        manifest_hash=manifest.manifest_hash,
        reference_trace_hash=reference.trace_hash,
        runtime_trace_hash=runtime.trace_hash,
        decision_semantics_hash=runtime.decision_semantics_hash,
        checker_revision=SCHEDULE_CHECKER_REVISION,
        scheduler_core_revision=manifest.scheduler_core_revision,
        adapter_revision=SIMPY_ADAPTER_REVISION,
        runtime_version=SIMPY_QUALIFIED_VERSION,
        decisions_equivalent=True,
        resource_capacity_validated=True,
        deterministic_replay_validated=True,
        kernel_noninterference_validated=True,
        external_io=False,
        kernel_acceptance_claimed=False,
        canonical_time_authority=False,
        world_truth_validated=False,
        branch_authority=False,
        outcome_authority=False,
        canonical_admission=False,
    )
