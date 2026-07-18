from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import simpy

from .hashio import digest
from .simulation_schedule_contracts import (
    QueueDecision,
    SCHEDULE_NORMALIZATION_REVISION,
    SCHEDULER_CORE_REVISION,
    SIMPY_ADAPTER_REVISION,
    SIMPY_QUALIFIED_VERSION,
    ScheduledCommandProposal,
    SchedulerTrace,
    SimulationScheduleManifest,
)
from .simulation_schedule_core import _normalized_proposals


SIMPY_ADAPTER_ID = "scheduler.simpy_integer_ticks"


class SimPyScheduleAdapter:
    """A schedule-only adapter with no kernel, route, fact, or outcome authority."""

    adapter_id = SIMPY_ADAPTER_ID
    adapter_revision = SIMPY_ADAPTER_REVISION
    scheduler_core_revision = SCHEDULER_CORE_REVISION

    def __init__(self, *, expected_version: str = SIMPY_QUALIFIED_VERSION) -> None:
        try:
            installed_version = version("simpy")
        except PackageNotFoundError as exc:  # pragma: no cover - import already proves presence
            raise RuntimeError("simpy_runtime_missing") from exc
        if installed_version != expected_version or expected_version != SIMPY_QUALIFIED_VERSION:
            raise RuntimeError(
                f"simpy_runtime_unqualified:{installed_version}:{expected_version}"
            )
        self.runtime_version = installed_version

    def plan(self, manifest: SimulationScheduleManifest) -> SchedulerTrace:
        proposals = _normalized_proposals(manifest)
        environment = simpy.Environment(initial_time=0)
        resources = {
            spec.resource_class: simpy.Resource(environment, capacity=spec.capacity)
            for spec in manifest.resources
        }
        recorded: dict[str, QueueDecision] = {}

        def execute(proposal: ScheduledCommandProposal, deterministic_ordinal: int):
            ready_tick = proposal.ready_tick
            if ready_tick:
                yield environment.timeout(ready_tick)
            resource = resources[proposal.resource_class]
            with resource.request() as request:
                yield request
                start = int(environment.now)
                wait = start - ready_tick
                if wait > manifest.max_wait_ticks:
                    raise ValueError("schedule_starvation_ceiling_exceeded")
                yield environment.timeout(proposal.service_ticks)
                finish = int(environment.now)
                if finish > manifest.max_finish_tick:
                    raise ValueError("schedule_finish_ceiling_exceeded")
                recorded[proposal.proposal_id] = QueueDecision(
                    proposal_id=proposal.proposal_id,
                    scheduling_class=proposal.scheduling_class,
                    resource_class=proposal.resource_class,
                    planned_start_tick=start,
                    planned_finish_tick=finish,
                    deterministic_ordinal=deterministic_ordinal,
                    expected_disposition=proposal.expected_disposition,
                    kernel_acceptance=False,
                )

        for ordinal, proposal in enumerate(proposals, start=1):
            environment.process(execute(proposal, ordinal))
        environment.run()

        decisions = tuple(
            recorded[proposal.proposal_id]
            for proposal in proposals
        )
        semantics_hash = digest(decisions)
        trace_payload = {
            "adapter_id": self.adapter_id,
            "adapter_revision": self.adapter_revision,
            "runtime_version": self.runtime_version,
            "manifest_hash": manifest.manifest_hash,
            "semantics": semantics_hash,
        }
        return SchedulerTrace(
            trace_id=f"SCHED-TRACE-{digest(trace_payload)[:18]}",
            adapter_id=self.adapter_id,
            adapter_revision=self.adapter_revision,
            runtime_version=self.runtime_version,
            scheduler_core_revision=SCHEDULER_CORE_REVISION,
            normalization_revision=SCHEDULE_NORMALIZATION_REVISION,
            manifest_hash=manifest.manifest_hash,
            decisions=decisions,
            decision_semantics_hash=semantics_hash,
            runtime_adapter_executed=True,
            external_io=False,
            kernel_acceptance_claimed=False,
            canonical_time_authority=False,
            world_truth_validated=False,
            branch_authority=False,
            outcome_authority=False,
            canonical_admission=False,
        )
