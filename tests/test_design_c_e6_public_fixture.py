from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_design_c_e6_recovery_fixture.py"
SPEC = importlib.util.spec_from_file_location("design_c_e6_fixture", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_checked_in_e6_summary_matches_ephemeral_builder() -> None:
    expected = MODULE.build_summary()
    actual = json.loads(
        (
            ROOT / "generated" / "design-c-e6-recovery-v1" / "summary.json"
        ).read_text(encoding="utf-8")
    )
    assert actual == expected


def test_public_e6_summary_is_noncanonical_and_nonjoinable() -> None:
    summary = MODULE.build_summary()
    assert summary["commit_protocol"]["accepted_once"] is True
    assert summary["commit_protocol"]["duplicate_replay"] is True
    assert summary["finance_journal"]["lifecycle_stage_count"] == 5
    assert summary["finance_journal"]["accounts_receivable_cents"] == 0
    assert summary["finance_journal"]["balanced"] is True
    assert summary["qualification_boundaries"] == {
        "canonical_store": False,
        "h10_storage_approved": False,
        "external_delivery": False,
        "unattended_execution": False,
        "lease_protocol": False,
    }
    assert summary["contains_case_identifiers"] is False
    assert summary["contains_financial_source_rows"] is False
    assert summary["contains_commitments"] is False
    assert summary["nonjoinable"] is True
