from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_design_c_c023_secure_ipc_fixture.py"
SPEC = importlib.util.spec_from_file_location("c023_secure_ipc_fixture", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_checked_in_c023_secure_ipc_summary_matches_builder() -> None:
    actual = json.loads(
        (ROOT / "generated" / "design-c-c023-secure-ipc-v1" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert actual == MODULE.build_summary()


def test_public_c023_summary_is_nonjoinable_and_fail_closed() -> None:
    summary = MODULE.build_summary()
    assert all(summary["validated_contracts"].values())
    assert summary["aggregate_counts"] == {
        "operation_count": 3,
        "schema_count": 3,
        "mutation_count": 22,
        "detected_mutation_count": 22,
        "max_frame_bytes": 65536,
        "live_pipe_api_call_count": 0,
    }
    assert summary["qualification_boundaries"] == {
        "implementation_present": True,
        "static_and_fake_backend_qualified": True,
        "live_pipe_created": False,
        "live_os_probe_pending": True,
        "c020_gap_ipc_still_blocking": True,
        "host_mutation_authorized": False,
        "physical_isolation_qualified": False,
        "canonical_activation_authorized": False,
        "unattended_execution_authorized": False,
        "external_effects": False,
    }
    serialized = json.dumps(summary, sort_keys=True).casefold()
    for forbidden in (
        r"\\.\pipe",
        "s-1-5-21",
        "ipccap-",
        "ipcreq-",
        "c:\\lfdt-data",
        "fixture-key",
    ):
        assert forbidden not in serialized
    assert summary["nonjoinable"] is True
