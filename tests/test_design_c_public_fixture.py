from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_design_c_g0c_readiness_fixture.py"
SPEC = importlib.util.spec_from_file_location("design_c_readiness_fixture", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_checked_in_design_c_readiness_summary_matches_builder() -> None:
    expected = MODULE.build_summary()
    actual = json.loads(
        (
            ROOT
            / "generated"
            / "design-c-g0c-readiness-v1"
            / "summary.json"
        ).read_text(encoding="utf-8")
    )
    assert actual == expected


def test_public_readiness_summary_is_honestly_incomplete_and_nonjoinable() -> None:
    summary = MODULE.build_summary()
    assert summary["baseline_state"] == "adopted_frozen_design_c_v1"
    assert summary["current_system_containment_state"] == "incomplete_surfaces"
    assert summary["scanner_mutation_evidence"]["mutation_count"] == 140
    assert summary["qualification_boundaries"] == {
        "worker_boundary_validated": False,
        "system_containment_qualified": False,
        "canonical_runtime_root_selected": True,
        "backup_location_selected": False,
        "canonical_storage_authorized": False,
        "unattended_execution_authorized": False,
        "external_effects": False,
    }
    assert summary["contains_case_identifiers"] is False
    assert summary["contains_canary_or_key"] is False
    assert summary["contains_source_rows"] is False
    assert summary["nonjoinable"] is True
