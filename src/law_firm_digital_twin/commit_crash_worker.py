from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .commit_protocol import GENESIS_HEAD_HASH, CommitProposal
from .hashio import digest
from .sqlite_commit_adapter import FAULT_POINTS, SQLiteCommitAdapter


def crash_fixture_proposal() -> CommitProposal:
    return CommitProposal(
        proposal_id="CPROP-SUBPROCESS-CRASH-V1",
        idempotency_key="commit-subprocess-crash:v1:r1",
        command_commitment=digest("subprocess-crash-command-v1"),
        expected_parent_hash=GENESIS_HEAD_HASH,
        dependency_hash=digest("subprocess-crash-dependency-v1"),
        event_type="subprocess_crash_fixture",
        result_commitment=digest("subprocess-crash-result-v1"),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("--fault-point", choices=FAULT_POINTS)
    args = parser.parse_args()
    adapter = SQLiteCommitAdapter(args.database)

    def fault_hook(point: str) -> None:
        if args.fault_point == point:
            os._exit(77)

    decision = adapter.commit(
        crash_fixture_proposal(),
        fault_hook=fault_hook if args.fault_point else None,
    )
    print(
        json.dumps(
            {
                "disposition": decision.disposition,
                "event_sequence": decision.event_sequence,
                "canonical_admission": decision.canonical_admission,
                "external_effects": decision.external_effects,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
