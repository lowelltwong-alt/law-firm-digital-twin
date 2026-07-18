from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from law_firm_digital_twin.finance_journal import (
    FINANCE_GENESIS_HASH,
    SQLiteFinanceJournal,
    build_finance_lifecycle,
)


ROOT = Path(__file__).resolve().parents[1]


def _crash(database: Path, point: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "law_firm_digital_twin.finance_crash_worker",
            str(database),
            "--fault-point",
            point,
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_real_crash_after_finance_entries_recovers_no_partial_transaction(
    tmp_path: Path,
) -> None:
    database = tmp_path / "finance-before-commit.sqlite3"
    completed = _crash(database, "after_entries_insert")
    assert completed.returncode == 78
    recovered = SQLiteFinanceJournal(database)
    snapshot = recovered.snapshot()
    assert snapshot.head_hash == FINANCE_GENESIS_HASH
    assert snapshot.transaction_count == 0
    assert snapshot.entry_count == 0
    assert snapshot.invariant_errors == ()


def test_real_crash_after_finance_commit_retries_once(tmp_path: Path) -> None:
    database = tmp_path / "finance-after-commit.sqlite3"
    completed = _crash(database, "after_commit_before_return")
    assert completed.returncode == 78
    recovered = SQLiteFinanceJournal(database)
    before = recovered.snapshot()
    assert before.transaction_count == 1
    decision = recovered.post(build_finance_lifecycle()[0])
    after = recovered.snapshot()
    assert decision.disposition == "duplicate_replay"
    assert before == after
    assert after.invariant_errors == ()
