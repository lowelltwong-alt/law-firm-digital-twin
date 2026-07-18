from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from .hashio import digest


SCHEDULER_CORE_REVISION = "simulation-scheduler-core-g2-v1"
SCHEDULE_NORMALIZATION_REVISION = "simulation-schedule-normalization-g2-v1"
REFERENCE_SCHEDULER_REVISION = "reference-integer-scheduler-g2-v1"
SIMPY_ADAPTER_REVISION = "simpy-scheduler-adapter-g2-v1"
SIMPY_QUALIFIED_VERSION = "4.1.2"


@dataclass(frozen=True)
class SchedulerResourceSpec:
    resource_class: str
    capacity: int
    queue_policy: Literal["deterministic_fifo"] = "deterministic_fifo"
    non_preemptive: Literal[True] = True


@dataclass(frozen=True)
class ScheduledCommandProposal:
    proposal_id: str
    matter_commitment: str
    command_commitment: str
    scheduling_class: str
    ready_tick: int
    service_ticks: int
    resource_class: str
    priority: int
    submission_ordinal: int
    tie_break_key: str
    expected_disposition: Literal["accepted", "denied_boundary_probe"]
    source_cassette_commitment: str
    payload_included: Literal[False] = False
    kernel_acceptance_claimed: Literal[False] = False


@dataclass(frozen=True)
class SimulationScheduleManifest:
    manifest_id: str
    scheduler_core_revision: str
    normalization_revision: str
    source_cassette_commitment: str
    matter_commitment: str
    resources: tuple[SchedulerResourceSpec, ...]
    proposals: tuple[ScheduledCommandProposal, ...]
    max_wait_ticks: int
    max_finish_tick: int
    route_blind: Literal[True]
    source_bodies_included: Literal[False]
    external_io: Literal[False]
    canonical_time_authority: Literal[False]
    world_truth_write: Literal[False]
    branch_authority: Literal[False]
    outcome_authority: Literal[False]

    @property
    def manifest_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class QueueDecision:
    proposal_id: str
    scheduling_class: str
    resource_class: str
    planned_start_tick: int
    planned_finish_tick: int
    deterministic_ordinal: int
    expected_disposition: str
    kernel_acceptance: Literal[False] = False


@dataclass(frozen=True)
class SchedulerTrace:
    trace_id: str
    adapter_id: str
    adapter_revision: str
    runtime_version: str
    scheduler_core_revision: str
    normalization_revision: str
    manifest_hash: str
    decisions: tuple[QueueDecision, ...]
    decision_semantics_hash: str
    runtime_adapter_executed: bool
    external_io: Literal[False]
    kernel_acceptance_claimed: Literal[False]
    canonical_time_authority: Literal[False]
    world_truth_validated: Literal[False]
    branch_authority: Literal[False]
    outcome_authority: Literal[False]
    canonical_admission: Literal[False]

    @property
    def trace_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class SchedulingQualificationReceipt:
    receipt_id: str
    manifest_hash: str
    reference_trace_hash: str
    runtime_trace_hash: str
    decision_semantics_hash: str
    checker_revision: str
    scheduler_core_revision: str
    adapter_revision: str
    runtime_version: str
    decisions_equivalent: Literal[True]
    resource_capacity_validated: Literal[True]
    deterministic_replay_validated: Literal[True]
    kernel_noninterference_validated: Literal[True]
    external_io: Literal[False]
    kernel_acceptance_claimed: Literal[False]
    canonical_time_authority: Literal[False]
    world_truth_validated: Literal[False]
    branch_authority: Literal[False]
    outcome_authority: Literal[False]
    canonical_admission: Literal[False]

    @property
    def receipt_hash(self) -> str:
        return digest(self)


class SimulationRuntimeAdapter(Protocol):
    adapter_id: str
    adapter_revision: str
    scheduler_core_revision: str
    runtime_version: str

    def plan(self, manifest: SimulationScheduleManifest) -> SchedulerTrace: ...

