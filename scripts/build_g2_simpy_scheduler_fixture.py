from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from law_firm_digital_twin.g2 import build_g2_attempt_cassette
from law_firm_digital_twin.models import Arm, Route
from law_firm_digital_twin.simpy_schedule_adapter import SimPyScheduleAdapter
from law_firm_digital_twin.simulation_schedule_contracts import (
    SCHEDULE_NORMALIZATION_REVISION,
    SCHEDULER_CORE_REVISION,
    SIMPY_ADAPTER_REVISION,
    SIMPY_QUALIFIED_VERSION,
)
from law_firm_digital_twin.simulation_schedule_core import build_g2_schedule_manifest
from law_firm_digital_twin.simulation_schedule_validator import (
    qualify_simpy_schedule_adapter,
)


OUTPUT = ROOT / "generated" / "g2-simpy-scheduler-v1"


def build_summary() -> dict[str, object]:
    adapter = SimPyScheduleAdapter()
    class_counts: Counter[str] = Counter()
    resource_counts: Counter[str] = Counter()
    proposal_count = 0
    for route in Route:
        serialized = build_g2_attempt_cassette(
            "public-scheduler-qualification", Arm.AI_FIRST, route
        )
        manifest = build_g2_schedule_manifest(serialized)
        qualify_simpy_schedule_adapter(serialized, manifest, adapter=adapter)
        proposal_count += len(manifest.proposals)
        class_counts.update(item.scheduling_class for item in manifest.proposals)
        resource_counts.update(item.resource_class for item in manifest.proposals)
    return {
        "schema": "g2_simpy_scheduler_public_summary_v1",
        "fidelity": "G2",
        "scenario_count": len(tuple(Route)),
        "proposal_count": proposal_count,
        "scheduling_class_counts": dict(sorted(class_counts.items())),
        "resource_class_counts": dict(sorted(resource_counts.items())),
        "scheduler_core_revision": SCHEDULER_CORE_REVISION,
        "normalization_revision": SCHEDULE_NORMALIZATION_REVISION,
        "adapter_revision": SIMPY_ADAPTER_REVISION,
        "runtime": {"package": "simpy", "version": SIMPY_QUALIFIED_VERSION},
        "qualification": {
            "reference_equivalence": True,
            "deterministic_replay": True,
            "kernel_noninterference": True,
            "capacity_validation": True,
        },
        "authority": {
            "kernel_acceptance": False,
            "canonical_time": False,
            "world_truth": False,
            "branch": False,
            "outcome": False,
        },
        "nonjoinable": True,
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    summary = build_summary()
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUTPUT / "README.md").write_text(
        "# G2 SimPy Scheduler Public Fixture\n\n"
        "Aggregate qualification summary only. It intentionally excludes source, "
        "matter, command, cassette, proposal, trace, and receipt commitments. "
        "The schedule is advisory and has no world-truth authority.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
