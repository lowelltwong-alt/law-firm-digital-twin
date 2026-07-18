from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import uuid


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from law_firm_digital_twin.commit_protocol import (  # noqa: E402
    GENESIS_HEAD_HASH,
    CommitProposal,
)
from law_firm_digital_twin.commit_protocol_validator import (  # noqa: E402
    validate_commit_snapshot,
)
from law_firm_digital_twin.finance_journal import (  # noqa: E402
    SQLiteFinanceJournal,
    build_finance_lifecycle,
)
from law_firm_digital_twin.hashio import digest  # noqa: E402
from law_firm_digital_twin.sqlite_commit_adapter import (  # noqa: E402
    FAULT_POINTS,
    SQLiteCommitAdapter,
)


OUTPUT = ROOT / "generated" / "design-c-e6-recovery-v1"
EPHEMERAL_ROOT = Path(
    os.environ.get("LFDT_EPHEMERAL_ROOT", tempfile.gettempdir())
) / "law-firm-digital-twin"


def build_summary() -> dict[str, object]:
    EPHEMERAL_ROOT.mkdir(parents=True, exist_ok=True)
    stem = f"lfdt-e6-summary-{uuid.uuid4().hex}"
    commit_path = EPHEMERAL_ROOT / f"{stem}-commit.sqlite3"
    finance_path = EPHEMERAL_ROOT / f"{stem}-finance.sqlite3"
    try:
        commit = SQLiteCommitAdapter(commit_path)
        proposal = CommitProposal(
            proposal_id="PUBLIC-SUMMARY-PROPOSAL",
            idempotency_key="public-summary:r1",
            command_commitment=digest("public-summary-command"),
            expected_parent_hash=GENESIS_HEAD_HASH,
            dependency_hash=digest("public-summary-dependency"),
            event_type="public_summary_fixture",
            result_commitment=digest("public-summary-result"),
        )
        accepted = commit.commit(proposal)
        duplicate = commit.commit(proposal)
        commit_snapshot = commit.snapshot()
        if validate_commit_snapshot(commit_snapshot):
            raise ValueError("public_commit_snapshot_invalid")

        finance = SQLiteFinanceJournal(finance_path)
        finance_decisions = tuple(
            finance.post(item) for item in build_finance_lifecycle()
        )
        finance_snapshot = finance.snapshot()
        if finance_snapshot.invariant_errors:
            raise ValueError("public_finance_snapshot_invalid")
        return {
            "schema": "design_c_e6_public_recovery_summary_v1",
            "scope": "ephemeral_noncanonical_reference",
            "commit_protocol": {
                "accepted_once": accepted.disposition == "accepted",
                "duplicate_replay": duplicate.disposition == "duplicate_replay",
                "event_count": commit_snapshot.event_count,
                "command_count": commit_snapshot.command_count,
                "outbox_count": commit_snapshot.outbox_count,
                "precommit_fault_point_count": len(FAULT_POINTS) - 1,
                "real_process_crash_tests": 7,
            },
            "finance_journal": {
                "lifecycle_stage_count": len(finance_decisions),
                "all_stages_accepted": all(
                    item.disposition == "accepted" for item in finance_decisions
                ),
                "accounts_receivable_cents": dict(finance_snapshot.balances)[
                    "accounts_receivable"
                ],
                "balanced": finance_snapshot.debit_total_cents
                == finance_snapshot.credit_total_cents,
                "real_process_crash_tests": 2,
            },
            "qualification_boundaries": {
                "canonical_store": False,
                "h10_storage_approved": False,
                "external_delivery": False,
                "unattended_execution": False,
                "lease_protocol": False,
            },
            "contains_case_identifiers": False,
            "contains_financial_source_rows": False,
            "contains_commitments": False,
            "nonjoinable": True,
        }
    finally:
        for database_path in (commit_path, finance_path):
            for suffix in ("", "-wal", "-shm"):
                Path(f"{database_path}{suffix}").unlink(missing_ok=True)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "summary.json").write_text(
        json.dumps(build_summary(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUTPUT / "README.md").write_text(
        "# Design C E-6 Recovery Fixture\n\n"
        "Aggregate evidence for the ephemeral SQLite reference adapters only. "
        "It does not authorize canonical storage, external delivery, leases, or "
        "unattended execution.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
