from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Callable, Literal

from .hashio import digest


FINANCE_JOURNAL_REVISION = "design-c-finance-journal-g0c-v1"
FINANCE_GENESIS_HASH = digest("design-c-finance-genesis-g0c-v1")
FINANCE_FAULT_POINTS = (
    "after_begin",
    "after_transaction_insert",
    "after_entries_insert",
    "before_commit",
    "after_commit_before_return",
)


@dataclass(frozen=True)
class FinanceEntry:
    account: str
    debit_cents: int
    credit_cents: int


@dataclass(frozen=True)
class FinanceTransactionProposal:
    transaction_id: str
    idempotency_key: str
    stage: Literal["invoice", "reduction", "appeal", "payment", "write_off"]
    expected_parent_hash: str
    entries: tuple[FinanceEntry, ...]
    source_event_commitment: str
    revision: str = FINANCE_JOURNAL_REVISION
    external_effect_requested: Literal[False] = False
    canonical_write_requested: Literal[False] = False

    @property
    def proposal_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class FinancePostDecision:
    decision_id: str
    disposition: Literal[
        "accepted",
        "duplicate_replay",
        "rejected_stale_parent",
        "rejected_idempotency_conflict",
    ]
    proposal_hash: str
    transaction_sequence: int | None
    transaction_hash: str
    head_hash: str
    rejection_code: str
    duplicate: bool
    ephemeral_test_only: Literal[True]
    canonical_admission: Literal[False]
    external_effects: Literal[False]


@dataclass(frozen=True)
class FinanceJournalSnapshot:
    head_hash: str
    transaction_count: int
    entry_count: int
    debit_total_cents: int
    credit_total_cents: int
    balances: tuple[tuple[str, int], ...]
    stage_counts: tuple[tuple[str, int], ...]
    journal_hash: str
    invariant_errors: tuple[str, ...]
    sqlite_integrity: str
    ephemeral_test_only: Literal[True]
    canonical_store: Literal[False]
    external_effects: Literal[False]

    @property
    def checkpoint_hash(self) -> str:
        return digest(self)


FinanceFaultHook = Callable[[str], None]


class SQLiteFinanceJournal:
    def __init__(self, database_path: Path, *, ephemeral_test_only: bool = True) -> None:
        if not ephemeral_test_only:
            raise ValueError("finance_canonical_activation_requires_h10")
        self.database_path = database_path.resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path, timeout=10, isolation_level=None
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS finance_metadata(
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS finance_transactions(
                    transaction_sequence INTEGER PRIMARY KEY,
                    transaction_id TEXT NOT NULL UNIQUE,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    proposal_hash TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    parent_hash TEXT NOT NULL,
                    transaction_hash TEXT NOT NULL UNIQUE,
                    source_event_commitment TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS finance_entries(
                    transaction_sequence INTEGER NOT NULL,
                    entry_ordinal INTEGER NOT NULL,
                    account TEXT NOT NULL,
                    debit_cents INTEGER NOT NULL CHECK(debit_cents >= 0),
                    credit_cents INTEGER NOT NULL CHECK(credit_cents >= 0),
                    PRIMARY KEY(transaction_sequence, entry_ordinal),
                    FOREIGN KEY(transaction_sequence)
                        REFERENCES finance_transactions(transaction_sequence)
                );
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO finance_metadata(key,value) VALUES('head_hash',?)",
                (FINANCE_GENESIS_HASH,),
            )
            connection.execute(
                "INSERT OR IGNORE INTO finance_metadata(key,value) VALUES('revision',?)",
                (FINANCE_JOURNAL_REVISION,),
            )
            connection.commit()

    @staticmethod
    def _validate(proposal: FinanceTransactionProposal) -> None:
        if proposal.revision != FINANCE_JOURNAL_REVISION:
            raise ValueError("finance_revision_invalid")
        if (
            not proposal.transaction_id
            or not proposal.idempotency_key
            or len(proposal.expected_parent_hash) != 64
            or len(proposal.source_event_commitment) != 64
            or not proposal.entries
        ):
            raise ValueError("finance_proposal_invalid")
        debit = sum(item.debit_cents for item in proposal.entries)
        credit = sum(item.credit_cents for item in proposal.entries)
        if debit <= 0 or debit != credit:
            raise ValueError("finance_transaction_unbalanced")
        for entry in proposal.entries:
            if (
                not entry.account
                or entry.debit_cents < 0
                or entry.credit_cents < 0
                or (entry.debit_cents == 0) == (entry.credit_cents == 0)
            ):
                raise ValueError("finance_entry_invalid")
        if proposal.external_effect_requested or proposal.canonical_write_requested:
            raise ValueError("finance_authority_invalid")

    @staticmethod
    def _fault(hook: FinanceFaultHook | None, point: str) -> None:
        if hook is not None:
            hook(point)

    def post(
        self,
        proposal: FinanceTransactionProposal,
        *,
        fault_hook: FinanceFaultHook | None = None,
    ) -> FinancePostDecision:
        self._validate(proposal)
        connection = self._connect()
        committed = False
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._fault(fault_hook, "after_begin")
            head = str(
                connection.execute(
                    "SELECT value FROM finance_metadata WHERE key='head_hash'"
                ).fetchone()[0]
            )
            existing = connection.execute(
                "SELECT * FROM finance_transactions WHERE idempotency_key=?",
                (proposal.idempotency_key,),
            ).fetchone()
            if existing is not None:
                connection.rollback()
                if str(existing["proposal_hash"]) != proposal.proposal_hash:
                    return self._decision(
                        proposal,
                        "rejected_idempotency_conflict",
                        head,
                        rejection="idempotency_key_reused_with_changed_input",
                    )
                return self._decision(
                    proposal,
                    "duplicate_replay",
                    head,
                    sequence=int(existing["transaction_sequence"]),
                    transaction_hash=str(existing["transaction_hash"]),
                    duplicate=True,
                )
            if proposal.expected_parent_hash != head:
                connection.rollback()
                return self._decision(
                    proposal,
                    "rejected_stale_parent",
                    head,
                    rejection="expected_parent_does_not_match_head",
                )
            sequence = int(
                connection.execute(
                    "SELECT COALESCE(MAX(transaction_sequence),0)+1 FROM finance_transactions"
                ).fetchone()[0]
            )
            transaction_payload = {
                "sequence": sequence,
                "parent": head,
                "stage": proposal.stage,
                "entries": proposal.entries,
                "source": proposal.source_event_commitment,
                "proposal": proposal.proposal_hash,
                "revision": FINANCE_JOURNAL_REVISION,
            }
            transaction_hash = digest(transaction_payload)
            connection.execute(
                """
                INSERT INTO finance_transactions(
                    transaction_sequence,transaction_id,idempotency_key,
                    proposal_hash,stage,parent_hash,transaction_hash,
                    source_event_commitment
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    sequence,
                    proposal.transaction_id,
                    proposal.idempotency_key,
                    proposal.proposal_hash,
                    proposal.stage,
                    head,
                    transaction_hash,
                    proposal.source_event_commitment,
                ),
            )
            self._fault(fault_hook, "after_transaction_insert")
            connection.executemany(
                """
                INSERT INTO finance_entries(
                    transaction_sequence,entry_ordinal,account,debit_cents,credit_cents
                ) VALUES(?,?,?,?,?)
                """,
                tuple(
                    (
                        sequence,
                        ordinal,
                        entry.account,
                        entry.debit_cents,
                        entry.credit_cents,
                    )
                    for ordinal, entry in enumerate(proposal.entries, start=1)
                ),
            )
            self._fault(fault_hook, "after_entries_insert")
            connection.execute(
                "UPDATE finance_metadata SET value=? WHERE key='head_hash'",
                (transaction_hash,),
            )
            self._fault(fault_hook, "before_commit")
            connection.commit()
            committed = True
            self._fault(fault_hook, "after_commit_before_return")
            return self._decision(
                proposal,
                "accepted",
                transaction_hash,
                sequence=sequence,
                transaction_hash=transaction_hash,
            )
        except Exception:
            if not committed:
                connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _decision(
        proposal: FinanceTransactionProposal,
        disposition: str,
        head_hash: str,
        *,
        sequence: int | None = None,
        transaction_hash: str = "",
        rejection: str = "",
        duplicate: bool = False,
    ) -> FinancePostDecision:
        payload = {
            "proposal": proposal.proposal_hash,
            "disposition": disposition,
            "head": head_hash,
            "sequence": sequence,
            "transaction": transaction_hash,
            "rejection": rejection,
        }
        return FinancePostDecision(
            decision_id=f"FINANCE-DECISION-{digest(payload)[:18]}",
            disposition=disposition,  # type: ignore[arg-type]
            proposal_hash=proposal.proposal_hash,
            transaction_sequence=sequence,
            transaction_hash=transaction_hash,
            head_hash=head_hash,
            rejection_code=rejection,
            duplicate=duplicate,
            ephemeral_test_only=True,
            canonical_admission=False,
            external_effects=False,
        )

    def snapshot(self) -> FinanceJournalSnapshot:
        with closing(self._connect()) as connection:
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            head = str(
                connection.execute(
                    "SELECT value FROM finance_metadata WHERE key='head_hash'"
                ).fetchone()[0]
            )
            transactions = tuple(
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM finance_transactions ORDER BY transaction_sequence"
                ).fetchall()
            )
            entries = tuple(
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM finance_entries ORDER BY transaction_sequence,entry_ordinal"
                ).fetchall()
            )
            errors: list[str] = []
            expected_parent = FINANCE_GENESIS_HASH
            for index, transaction in enumerate(transactions, start=1):
                if int(transaction["transaction_sequence"]) != index:
                    errors.append(f"finance_sequence_gap:{index}")
                if str(transaction["parent_hash"]) != expected_parent:
                    errors.append(f"finance_parent_break:{index}")
                transaction_entries = tuple(
                    FinanceEntry(
                        account=str(item["account"]),
                        debit_cents=int(item["debit_cents"]),
                        credit_cents=int(item["credit_cents"]),
                    )
                    for item in entries
                    if int(item["transaction_sequence"]) == index
                )
                payload = {
                    "sequence": index,
                    "parent": str(transaction["parent_hash"]),
                    "stage": str(transaction["stage"]),
                    "entries": transaction_entries,
                    "source": str(transaction["source_event_commitment"]),
                    "proposal": str(transaction["proposal_hash"]),
                    "revision": FINANCE_JOURNAL_REVISION,
                }
                if str(transaction["transaction_hash"]) != digest(payload):
                    errors.append(f"finance_hash_mismatch:{index}")
                debit = sum(item.debit_cents for item in transaction_entries)
                credit = sum(item.credit_cents for item in transaction_entries)
                if debit <= 0 or debit != credit:
                    errors.append(f"finance_unbalanced:{index}")
                expected_parent = str(transaction["transaction_hash"])
            if head != expected_parent:
                errors.append("finance_head_mismatch")
            balances: dict[str, int] = {}
            for entry in entries:
                account = str(entry["account"])
                balances[account] = balances.get(account, 0) + int(
                    entry["debit_cents"]
                ) - int(entry["credit_cents"])
            stages: dict[str, int] = {}
            for item in transactions:
                stage = str(item["stage"])
                stages[stage] = stages.get(stage, 0) + 1
            debit_total = sum(int(item["debit_cents"]) for item in entries)
            credit_total = sum(int(item["credit_cents"]) for item in entries)
            if debit_total != credit_total:
                errors.append("finance_global_imbalance")
            return FinanceJournalSnapshot(
                head_hash=head,
                transaction_count=len(transactions),
                entry_count=len(entries),
                debit_total_cents=debit_total,
                credit_total_cents=credit_total,
                balances=tuple(sorted(balances.items())),
                stage_counts=tuple(sorted(stages.items())),
                journal_hash=digest((transactions, entries)),
                invariant_errors=tuple(errors),
                sqlite_integrity=integrity,
                ephemeral_test_only=True,
                canonical_store=False,
                external_effects=False,
            )


def build_finance_lifecycle(
    parent_hash: str = FINANCE_GENESIS_HASH,
) -> tuple[FinanceTransactionProposal, ...]:
    stages = (
        ("invoice", (FinanceEntry("accounts_receivable", 100_000, 0), FinanceEntry("fee_revenue", 0, 100_000))),
        ("reduction", (FinanceEntry("billing_write_off", 20_000, 0), FinanceEntry("accounts_receivable", 0, 20_000))),
        ("appeal", (FinanceEntry("accounts_receivable", 10_000, 0), FinanceEntry("billing_write_off", 0, 10_000))),
        ("payment", (FinanceEntry("cash", 85_000, 0), FinanceEntry("accounts_receivable", 0, 85_000))),
        ("write_off", (FinanceEntry("billing_write_off", 5_000, 0), FinanceEntry("accounts_receivable", 0, 5_000))),
    )
    proposals: list[FinanceTransactionProposal] = []
    current_parent = parent_hash
    for ordinal, (stage, entries) in enumerate(stages, start=1):
        proposal = FinanceTransactionProposal(
            transaction_id=f"FIN-TX-{ordinal}",
            idempotency_key=f"finance-lifecycle:{ordinal}:r1",
            stage=stage,  # type: ignore[arg-type]
            expected_parent_hash=current_parent,
            entries=entries,
            source_event_commitment=digest({"finance_source_event": ordinal}),
        )
        proposals.append(proposal)
        transaction_payload = {
            "sequence": ordinal,
            "parent": current_parent,
            "stage": stage,
            "entries": entries,
            "source": proposal.source_event_commitment,
            "proposal": proposal.proposal_hash,
            "revision": FINANCE_JOURNAL_REVISION,
        }
        current_parent = digest(transaction_payload)
    return tuple(proposals)
