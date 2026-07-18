from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
from typing import Iterable

from .commit_protocol import (
    COMMIT_CORE_REVISION,
    COMMIT_SCHEMA_REVISION,
    GENESIS_HEAD_HASH,
    CommitDecision,
    CommitProposal,
    CommitStoreSnapshot,
    FaultHook,
)
from .hashio import digest


SQLITE_COMMIT_ADAPTER_REVISION = "design-c-sqlite-commit-adapter-g0c-v1"
FAULT_POINTS = (
    "after_begin",
    "after_event_insert",
    "after_command_insert",
    "after_outbox_insert",
    "before_commit",
    "after_commit_before_return",
)


class SQLiteCommitAdapter:
    """Ephemeral crash-test adapter; never a canonical store."""

    adapter_revision = SQLITE_COMMIT_ADAPTER_REVISION
    schema_revision = COMMIT_SCHEMA_REVISION

    def __init__(
        self,
        database_path: Path,
        *,
        prohibited_roots: Iterable[Path] = (),
        ephemeral_test_only: bool = True,
    ) -> None:
        if not ephemeral_test_only:
            raise ValueError("sqlite_commit_canonical_activation_requires_h10")
        self.database_path = database_path.resolve()
        if self.database_path.name in {"", ".", ".."}:
            raise ValueError("sqlite_commit_database_path_invalid")
        for root in prohibited_roots:
            resolved_root = root.resolve()
            try:
                self.database_path.relative_to(resolved_root)
            except ValueError:
                continue
            raise ValueError("sqlite_commit_path_inside_prohibited_root")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=10,
            isolation_level=None,
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
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_sequence INTEGER PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    parent_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    command_commitment TEXT NOT NULL,
                    dependency_hash TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    result_commitment TEXT NOT NULL,
                    proposal_hash TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS commands (
                    idempotency_key TEXT PRIMARY KEY,
                    proposal_hash TEXT NOT NULL,
                    command_commitment TEXT NOT NULL,
                    dependency_hash TEXT NOT NULL,
                    event_sequence INTEGER NOT NULL,
                    event_hash TEXT NOT NULL,
                    outbox_id TEXT NOT NULL,
                    FOREIGN KEY(event_sequence) REFERENCES events(event_sequence)
                );
                CREATE TABLE IF NOT EXISTS outbox (
                    outbox_id TEXT PRIMARY KEY,
                    event_sequence INTEGER NOT NULL UNIQUE,
                    event_hash TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending','acknowledged')),
                    delivery_attempts INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(event_sequence) REFERENCES events(event_sequence)
                );
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(key,value) VALUES('head_hash',?)",
                (GENESIS_HEAD_HASH,),
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(key,value) VALUES('schema_revision',?)",
                (COMMIT_SCHEMA_REVISION,),
            )
            connection.commit()

    @staticmethod
    def _validate_proposal(proposal: CommitProposal) -> None:
        if proposal.core_revision != COMMIT_CORE_REVISION:
            raise ValueError("commit_core_revision_invalid")
        if not proposal.proposal_id or not proposal.idempotency_key or not proposal.event_type:
            raise ValueError("commit_proposal_identity_invalid")
        for name, value in (
            ("command", proposal.command_commitment),
            ("parent", proposal.expected_parent_hash),
            ("dependency", proposal.dependency_hash),
            ("result", proposal.result_commitment),
        ):
            if len(value) != 64:
                raise ValueError(f"commit_{name}_commitment_invalid")
        if (
            proposal.contains_payload
            or proposal.external_effect_requested
            or proposal.canonical_write_requested
        ):
            raise ValueError("commit_proposal_authority_invalid")

    @staticmethod
    def _fault(fault_hook: FaultHook | None, point: str) -> None:
        if fault_hook is not None:
            fault_hook(point)

    def _rejection(
        self,
        proposal: CommitProposal,
        *,
        disposition: str,
        head_hash: str,
        rejection_code: str,
    ) -> CommitDecision:
        payload = {
            "proposal": proposal.proposal_hash,
            "disposition": disposition,
            "head": head_hash,
            "rejection": rejection_code,
            "adapter": self.adapter_revision,
        }
        return CommitDecision(
            decision_id=f"COMMIT-DECISION-{digest(payload)[:18]}",
            proposal_hash=proposal.proposal_hash,
            disposition=disposition,  # type: ignore[arg-type]
            event_sequence=None,
            event_hash="",
            head_hash=head_hash,
            outbox_id="",
            duplicate=False,
            rejection_code=rejection_code,
            adapter_revision=self.adapter_revision,
            schema_revision=self.schema_revision,
            ephemeral_test_only=True,
            canonical_admission=False,
            external_effects=False,
        )

    def commit(
        self,
        proposal: CommitProposal,
        *,
        fault_hook: FaultHook | None = None,
    ) -> CommitDecision:
        self._validate_proposal(proposal)
        connection = self._connect()
        committed = False
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._fault(fault_hook, "after_begin")
            head_hash = str(
                connection.execute(
                    "SELECT value FROM metadata WHERE key='head_hash'"
                ).fetchone()[0]
            )
            existing = connection.execute(
                "SELECT * FROM commands WHERE idempotency_key=?",
                (proposal.idempotency_key,),
            ).fetchone()
            if existing is not None:
                if (
                    str(existing["proposal_hash"]) != proposal.proposal_hash
                    or str(existing["command_commitment"])
                    != proposal.command_commitment
                    or str(existing["dependency_hash"]) != proposal.dependency_hash
                ):
                    connection.rollback()
                    return self._rejection(
                        proposal,
                        disposition="rejected_idempotency_conflict",
                        head_hash=head_hash,
                        rejection_code="idempotency_key_reused_with_changed_input",
                    )
                payload = {
                    "proposal": proposal.proposal_hash,
                    "disposition": "duplicate_replay",
                    "event": str(existing["event_hash"]),
                    "head": head_hash,
                }
                connection.rollback()
                return CommitDecision(
                    decision_id=f"COMMIT-DECISION-{digest(payload)[:18]}",
                    proposal_hash=proposal.proposal_hash,
                    disposition="duplicate_replay",
                    event_sequence=int(existing["event_sequence"]),
                    event_hash=str(existing["event_hash"]),
                    head_hash=head_hash,
                    outbox_id=str(existing["outbox_id"]),
                    duplicate=True,
                    rejection_code="",
                    adapter_revision=self.adapter_revision,
                    schema_revision=self.schema_revision,
                    ephemeral_test_only=True,
                    canonical_admission=False,
                    external_effects=False,
                )
            if proposal.expected_parent_hash != head_hash:
                connection.rollback()
                return self._rejection(
                    proposal,
                    disposition="rejected_stale_parent",
                    head_hash=head_hash,
                    rejection_code="expected_parent_does_not_match_head",
                )
            next_sequence = int(
                connection.execute(
                    "SELECT COALESCE(MAX(event_sequence),0)+1 FROM events"
                ).fetchone()[0]
            )
            event_payload = {
                "sequence": next_sequence,
                "parent": head_hash,
                "command": proposal.command_commitment,
                "dependency": proposal.dependency_hash,
                "event_type": proposal.event_type,
                "result": proposal.result_commitment,
                "proposal": proposal.proposal_hash,
                "core": COMMIT_CORE_REVISION,
            }
            event_hash = digest(event_payload)
            event_id = f"EVENT-{event_hash[:18]}"
            outbox_id = f"OUTBOX-{digest({'event': event_hash, 'schema': self.schema_revision})[:18]}"
            connection.execute(
                """
                INSERT INTO events(
                    event_sequence,event_id,parent_hash,event_hash,
                    command_commitment,dependency_hash,event_type,
                    result_commitment,proposal_hash
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    next_sequence,
                    event_id,
                    head_hash,
                    event_hash,
                    proposal.command_commitment,
                    proposal.dependency_hash,
                    proposal.event_type,
                    proposal.result_commitment,
                    proposal.proposal_hash,
                ),
            )
            self._fault(fault_hook, "after_event_insert")
            connection.execute(
                """
                INSERT INTO commands(
                    idempotency_key,proposal_hash,command_commitment,
                    dependency_hash,event_sequence,event_hash,outbox_id
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    proposal.idempotency_key,
                    proposal.proposal_hash,
                    proposal.command_commitment,
                    proposal.dependency_hash,
                    next_sequence,
                    event_hash,
                    outbox_id,
                ),
            )
            self._fault(fault_hook, "after_command_insert")
            connection.execute(
                """
                INSERT INTO outbox(outbox_id,event_sequence,event_hash,status)
                VALUES(?,?,?,'pending')
                """,
                (outbox_id, next_sequence, event_hash),
            )
            self._fault(fault_hook, "after_outbox_insert")
            connection.execute(
                "UPDATE metadata SET value=? WHERE key='head_hash'",
                (event_hash,),
            )
            self._fault(fault_hook, "before_commit")
            connection.commit()
            committed = True
            self._fault(fault_hook, "after_commit_before_return")
            payload = {
                "proposal": proposal.proposal_hash,
                "disposition": "accepted",
                "event": event_hash,
                "head": event_hash,
            }
            return CommitDecision(
                decision_id=f"COMMIT-DECISION-{digest(payload)[:18]}",
                proposal_hash=proposal.proposal_hash,
                disposition="accepted",
                event_sequence=next_sequence,
                event_hash=event_hash,
                head_hash=event_hash,
                outbox_id=outbox_id,
                duplicate=False,
                rejection_code="",
                adapter_revision=self.adapter_revision,
                schema_revision=self.schema_revision,
                ephemeral_test_only=True,
                canonical_admission=False,
                external_effects=False,
            )
        except Exception:
            if not committed:
                connection.rollback()
            raise
        finally:
            connection.close()

    def acknowledge_outbox(self, outbox_id: str) -> bool:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM outbox WHERE outbox_id=?", (outbox_id,)
            ).fetchone()
            if row is None:
                connection.rollback()
                return False
            if str(row["status"]) == "pending":
                connection.execute(
                    """
                    UPDATE outbox
                    SET status='acknowledged', delivery_attempts=delivery_attempts+1
                    WHERE outbox_id=?
                    """,
                    (outbox_id,),
                )
            connection.commit()
            return True

    def snapshot(self) -> CommitStoreSnapshot:
        with closing(self._connect()) as connection:
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            head_hash = str(
                connection.execute(
                    "SELECT value FROM metadata WHERE key='head_hash'"
                ).fetchone()[0]
            )
            events = tuple(
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM events ORDER BY event_sequence"
                ).fetchall()
            )
            commands = tuple(
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM commands ORDER BY idempotency_key"
                ).fetchall()
            )
            outbox = tuple(
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM outbox ORDER BY event_sequence"
                ).fetchall()
            )
            errors: list[str] = []
            expected_parent = GENESIS_HEAD_HASH
            for index, event in enumerate(events, start=1):
                if int(event["event_sequence"]) != index:
                    errors.append(f"sequence_gap:{index}")
                if str(event["parent_hash"]) != expected_parent:
                    errors.append(f"parent_break:{index}")
                event_payload = {
                    "sequence": int(event["event_sequence"]),
                    "parent": str(event["parent_hash"]),
                    "command": str(event["command_commitment"]),
                    "dependency": str(event["dependency_hash"]),
                    "event_type": str(event["event_type"]),
                    "result": str(event["result_commitment"]),
                    "proposal": str(event["proposal_hash"]),
                    "core": COMMIT_CORE_REVISION,
                }
                if str(event["event_hash"]) != digest(event_payload):
                    errors.append(f"event_hash_mismatch:{index}")
                expected_parent = str(event["event_hash"])
            if head_hash != expected_parent:
                errors.append("head_hash_mismatch")
            if len(commands) != len(events):
                errors.append("command_event_count_mismatch")
            if len(outbox) != len(events):
                errors.append("outbox_event_count_mismatch")
            event_by_sequence = {
                int(item["event_sequence"]): item for item in events
            }
            for command in commands:
                event = event_by_sequence.get(int(command["event_sequence"]))
                if event is None or str(command["event_hash"]) != str(event["event_hash"]):
                    errors.append(
                        f"command_event_binding_mismatch:{command['idempotency_key']}"
                    )
            for item in outbox:
                event = event_by_sequence.get(int(item["event_sequence"]))
                if event is None or str(item["event_hash"]) != str(event["event_hash"]):
                    errors.append(f"outbox_event_binding_mismatch:{item['outbox_id']}")
            pending = sum(item["status"] == "pending" for item in outbox)
            acknowledged = sum(item["status"] == "acknowledged" for item in outbox)
            return CommitStoreSnapshot(
                adapter_revision=self.adapter_revision,
                schema_revision=self.schema_revision,
                head_hash=head_hash,
                event_count=len(events),
                command_count=len(commands),
                outbox_count=len(outbox),
                pending_outbox_count=pending,
                acknowledged_outbox_count=acknowledged,
                event_chain_hash=digest(events),
                outbox_state_hash=digest(outbox),
                invariant_errors=tuple(errors),
                sqlite_integrity=integrity,
                ephemeral_test_only=True,
                canonical_store=False,
                external_effects=False,
            )

    def protected_debug_dump(self) -> str:
        snapshot = self.snapshot()
        return json.dumps(
            {
                "checkpoint_hash": snapshot.checkpoint_hash,
                "invariant_errors": snapshot.invariant_errors,
                "ephemeral_test_only": True,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
