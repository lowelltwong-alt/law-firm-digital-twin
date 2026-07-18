from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from law_firm_digital_twin.commit_crash_worker import crash_fixture_proposal
from law_firm_digital_twin.commit_protocol import GENESIS_HEAD_HASH
from law_firm_digital_twin.commit_protocol_validator import (
    validate_commit_snapshot,
)
from law_firm_digital_twin.sqlite_commit_adapter import (
    FAULT_POINTS,
    SQLiteCommitAdapter,
)


ROOT = Path(__file__).resolve().parents[1]


def _run(database: Path, fault_point: str | None = None) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-m",
        "law_firm_digital_twin.commit_crash_worker",
        str(database),
    ]
    if fault_point is not None:
        command.extend(("--fault-point", fault_point))
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


@pytest.mark.parametrize("fault_point", FAULT_POINTS[:-1])
def test_real_process_crash_before_commit_recovers_empty_atomic_store(
    tmp_path: Path, fault_point: str
) -> None:
    database = tmp_path / f"crash-{fault_point}.sqlite3"
    completed = _run(database, fault_point)
    assert completed.returncode == 77
    recovered = SQLiteCommitAdapter(database)
    snapshot = recovered.snapshot()
    assert snapshot.head_hash == GENESIS_HEAD_HASH
    assert snapshot.event_count == 0
    assert snapshot.command_count == 0
    assert snapshot.outbox_count == 0
    assert validate_commit_snapshot(snapshot) == ()


def test_real_process_crash_after_commit_retries_as_duplicate_once(
    tmp_path: Path,
) -> None:
    database = tmp_path / "crash-after-commit.sqlite3"
    completed = _run(database, "after_commit_before_return")
    assert completed.returncode == 77
    recovered = SQLiteCommitAdapter(database)
    before = recovered.snapshot()
    assert before.event_count == 1
    retry = recovered.commit(crash_fixture_proposal())
    after = recovered.snapshot()
    assert retry.disposition == "duplicate_replay"
    assert before == after
    assert validate_commit_snapshot(after) == ()


def test_two_real_processes_delivering_same_key_commit_once(tmp_path: Path) -> None:
    database = tmp_path / "concurrent-process.sqlite3"
    SQLiteCommitAdapter(database)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    command = [
        sys.executable,
        "-m",
        "law_firm_digital_twin.commit_crash_worker",
        str(database),
    ]
    processes = [
        subprocess.Popen(
            command,
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(2)
    ]
    outputs = [process.communicate(timeout=30) for process in processes]
    assert all(process.returncode == 0 for process in processes)
    payloads = [json.loads(stdout) for stdout, _ in outputs]
    assert sorted(item["disposition"] for item in payloads) == [
        "accepted",
        "duplicate_replay",
    ]
    assert all(item["canonical_admission"] is False for item in payloads)
    snapshot = SQLiteCommitAdapter(database).snapshot()
    assert snapshot.event_count == 1
    assert snapshot.outbox_count == 1
    assert validate_commit_snapshot(snapshot) == ()
