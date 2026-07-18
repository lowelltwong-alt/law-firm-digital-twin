from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_simpy_runtime_and_lock_are_exactly_pinned() -> None:
    assert version("simpy") == "4.1.2"
    lock = (ROOT / "requirements" / "simulation.lock").read_text(encoding="utf-8")
    assert "simpy==4.1.2" in lock
    assert (
        "sha256:43071f84b6512c9b4fcb33ef057f240ccb1d1f3b263f9b4f9229d072e310b372"
        in lock
    )


def test_public_fixture_is_aggregate_only_and_nonjoinable() -> None:
    summary = json.loads(
        (ROOT / "generated" / "g2-simpy-scheduler-v1" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["nonjoinable"] is True
    assert summary["runtime"] == {"package": "simpy", "version": "4.1.2"}
    assert summary["qualification"] == {
        "capacity_validation": True,
        "deterministic_replay": True,
        "kernel_noninterference": True,
        "reference_equivalence": True,
    }
    forbidden_keys = {
        "seed",
        "matter_id",
        "matter_commitment",
        "command_id",
        "command_commitment",
        "cassette_hash",
        "source_cassette_commitment",
        "proposal_id",
        "trace_id",
        "trace_hash",
        "receipt_id",
        "receipt_hash",
        "route",
        "arm",
    }

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {key for child in value.values() for key in keys(child)}
        if isinstance(value, list):
            return {key for child in value for key in keys(child)}
        return set()

    assert keys(summary).isdisjoint(forbidden_keys)
    assert all(
        len(value) != 64
        for value in summary.values()
        if isinstance(value, str)
    )
