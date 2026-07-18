from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from law_firm_digital_twin.finance_journal import (
    FINANCE_FAULT_POINTS,
    FINANCE_GENESIS_HASH,
    FinanceEntry,
    SQLiteFinanceJournal,
    build_finance_lifecycle,
)


def test_full_billing_lifecycle_is_balanced_and_reconciles_ar(tmp_path: Path) -> None:
    journal = SQLiteFinanceJournal(tmp_path / "finance.sqlite3")
    decisions = [journal.post(item) for item in build_finance_lifecycle()]
    snapshot = journal.snapshot()
    assert all(item.disposition == "accepted" for item in decisions)
    assert snapshot.transaction_count == 5
    assert snapshot.entry_count == 10
    assert snapshot.debit_total_cents == snapshot.credit_total_cents
    assert dict(snapshot.balances) == {
        "accounts_receivable": 0,
        "billing_write_off": 15_000,
        "cash": 85_000,
        "fee_revenue": -100_000,
    }
    assert dict(snapshot.stage_counts) == {
        "appeal": 1,
        "invoice": 1,
        "payment": 1,
        "reduction": 1,
        "write_off": 1,
    }
    assert snapshot.invariant_errors == ()
    assert snapshot.sqlite_integrity == "ok"
    assert not snapshot.canonical_store
    assert not snapshot.external_effects


def test_finance_replay_is_idempotent(tmp_path: Path) -> None:
    journal = SQLiteFinanceJournal(tmp_path / "finance.sqlite3")
    first = build_finance_lifecycle()[0]
    accepted = journal.post(first)
    before = journal.snapshot()
    duplicate = journal.post(first)
    after = journal.snapshot()
    assert accepted.disposition == "accepted"
    assert duplicate.disposition == "duplicate_replay"
    assert duplicate.transaction_hash == accepted.transaction_hash
    assert before == after


@pytest.mark.parametrize("fault_point", FINANCE_FAULT_POINTS[:-1])
def test_partial_finance_transaction_rolls_back(
    tmp_path: Path, fault_point: str
) -> None:
    journal = SQLiteFinanceJournal(tmp_path / f"{fault_point}.sqlite3")
    proposal = build_finance_lifecycle()[0]

    def inject(point: str) -> None:
        if point == fault_point:
            raise RuntimeError(f"finance-injected:{point}")

    with pytest.raises(RuntimeError, match=fault_point):
        journal.post(proposal, fault_hook=inject)
    snapshot = journal.snapshot()
    assert snapshot.head_hash == FINANCE_GENESIS_HASH
    assert snapshot.transaction_count == 0
    assert snapshot.entry_count == 0
    assert snapshot.invariant_errors == ()


def test_after_commit_failure_recovers_once(tmp_path: Path) -> None:
    path = tmp_path / "after-commit.sqlite3"
    journal = SQLiteFinanceJournal(path)
    proposal = build_finance_lifecycle()[0]

    def inject(point: str) -> None:
        if point == "after_commit_before_return":
            raise RuntimeError("finance-injected:after_commit_before_return")

    with pytest.raises(RuntimeError, match="after_commit_before_return"):
        journal.post(proposal, fault_hook=inject)
    recovered = SQLiteFinanceJournal(path)
    before = recovered.snapshot()
    duplicate = recovered.post(proposal)
    after = recovered.snapshot()
    assert duplicate.disposition == "duplicate_replay"
    assert before == after
    assert after.transaction_count == 1


def test_unbalanced_invalid_and_authoritative_transactions_are_rejected(
    tmp_path: Path,
) -> None:
    journal = SQLiteFinanceJournal(tmp_path / "finance.sqlite3")
    proposal = build_finance_lifecycle()[0]
    attacks = (
        replace(proposal, entries=(FinanceEntry("ar", 100, 0),)),
        replace(proposal, external_effect_requested=True),
        replace(proposal, canonical_write_requested=True),
    )
    for attacked in attacks:
        with pytest.raises(ValueError):
            journal.post(attacked)
    assert journal.snapshot().transaction_count == 0


def test_stale_parent_and_changed_idempotency_are_rejected(tmp_path: Path) -> None:
    journal = SQLiteFinanceJournal(tmp_path / "finance.sqlite3")
    first = build_finance_lifecycle()[0]
    accepted = journal.post(first)
    stale = replace(
        build_finance_lifecycle()[1], expected_parent_hash=FINANCE_GENESIS_HASH
    )
    assert journal.post(stale).disposition == "rejected_stale_parent"
    changed = replace(
        first,
        entries=(
            FinanceEntry("accounts_receivable", 90_000, 0),
            FinanceEntry("fee_revenue", 0, 90_000),
        ),
    )
    assert journal.post(changed).disposition == "rejected_idempotency_conflict"
    snapshot = journal.snapshot()
    assert snapshot.head_hash == accepted.transaction_hash
    assert snapshot.transaction_count == 1


def test_finance_journal_refuses_canonical_activation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires_h10"):
        SQLiteFinanceJournal(
            tmp_path / "canonical.sqlite3", ephemeral_test_only=False
        )

def test_finance_journal_releases_sqlite_handles(tmp_path: Path) -> None:
    database = tmp_path / "handle-release.sqlite3"
    journal = SQLiteFinanceJournal(database)
    journal.snapshot()
    database.unlink()
    assert not database.exists()
