from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .hashio import digest
from .rules import PRIMARY_DEADLINE_CALCULATOR, SECONDARY_DEADLINE_CALCULATOR


@dataclass(frozen=True)
class AuditFinding:
    code: str
    title: str
    status: str
    severity: str
    evidence: tuple[str, ...]
    explanation: str


@dataclass(frozen=True)
class AuditReport:
    auditor: str
    revision: str
    plane: str
    passed: bool
    findings: tuple[AuditFinding, ...]
    detected_conflict_ids: tuple[str, ...]
    report_hash: str


class BereanAuditor:
    """Independent evaluation-plane cross-checker for the G2 world."""

    revision = "berean-g2-v2"

    def audit(self, kernel: Any) -> AuditReport:
        findings: list[AuditFinding] = []
        matter = kernel.bundle.matter
        sealed = kernel.bundle.sealed
        projection = kernel.projection
        events = tuple(kernel.events)
        denials = tuple(kernel.denials)
        oracle_denials = [item for item in denials if item.get("reason") == "oracle_boundary"]
        accepted_oracle = [event for event in events if event.event_type == "read_oracle_accepted"]

        self._check(
            findings,
            "BRN-001",
            "Oracle isolation",
            bool(oracle_denials) and not accepted_oracle,
            tuple(item["command_id"] for item in oracle_denials),
            "The attempt ledger contains an oracle denial and no accepted oracle-read event.",
        )
        conflict_denials = [
            item for item in denials
            if item.get("reason") == "missing_authority" and "matter_opening" in item.get("missing", ())
        ]
        open_events = [event for event in events if event.event_type == "open_matter_accepted"]
        gate_events = [event for event in events if event.event_type == "record_lawyer_gate_accepted"]
        gate_order_ok = bool(gate_events and open_events and gate_events[0].simulated_at < open_events[0].simulated_at)
        self._check(
            findings,
            "BRN-002",
            "Conflict and human authority gate",
            bool(conflict_denials) and gate_order_ok and not projection.authority_holds and projection.human_gate_bypasses == 0,
            tuple(item["command_id"] for item in conflict_denials) + tuple(event.command_id for event in gate_events + open_events),
            "A premature opening was denied, consent was recorded, and the accepted opening followed the lawyer gate.",
        )

        expected_deadlines = {
            "response_due": matter.rule_pack.response_days,
            "initial_disclosures_due": matter.rule_pack.disclosure_days,
            "discovery_cutoff": matter.rule_pack.discovery_cutoff_days,
        }
        deadline_audit = projection.deadline_audit
        calculator_events = [event for event in events if event.event_type == "calculate_deadlines_accepted"]
        verifier_events = [event for event in events if event.event_type == "verify_deadlines_accepted"]
        independent_deadline_ok = bool(
            calculator_events
            and verifier_events
            and calculator_events[0].actor_id != verifier_events[0].actor_id
            and deadline_audit.get("primary_actor") == calculator_events[0].actor_id
            and deadline_audit.get("secondary_actor") == verifier_events[0].actor_id
            and deadline_audit.get("primary_calculator") == PRIMARY_DEADLINE_CALCULATOR
            and deadline_audit.get("secondary_calculator") == SECONDARY_DEADLINE_CALCULATOR
            and PRIMARY_DEADLINE_CALCULATOR != SECONDARY_DEADLINE_CALCULATOR
        )
        self._check(
            findings,
            "BRN-003",
            "Deadline derivation",
            projection.deadlines == expected_deadlines and independent_deadline_ok,
            tuple(f"{key}:{value}" for key, value in sorted(deadline_audit.items())),
            "Different actors executed separately versioned calculators and agreed with the admitted rule-pack fields.",
        )

        produced = set(projection.produced_artifact_ids)
        detected_conflicts = self._detect_conflicts(matter.evidence_inventory, produced)
        declared_covered = all(
            set(item.artifact_ids).issubset(produced) and item.fact_id in detected_conflicts
            for item in sealed.declared_conflicts
        )
        self._check(
            findings,
            "BRN-004",
            "Independent evidence conflict detection",
            bool(detected_conflicts) and declared_covered,
            tuple(sorted(detected_conflicts)),
            "Berean derived incompatible claims from produced artifacts without relying on writer explanations.",
        )

        custody_errors: list[str] = []
        for artifact_id in sorted(produced):
            steps = projection.custody_log.get(artifact_id, [])
            days = [int(step["simulated_day"]) for step in steps]
            actions = [str(step["action"]) for step in steps]
            if days != sorted(days):
                custody_errors.append(f"{artifact_id}:nonmonotonic")
            for required in ("created", "collected", "hashed", "reviewed", "produced"):
                if required not in actions:
                    custody_errors.append(f"{artifact_id}:missing_{required}")
            artifact = next(item for item in matter.evidence_inventory if item.artifact_id == artifact_id)
            hashes = {str(step["object_hash"]) for step in steps}
            if hashes != {artifact.content_hash}:
                custody_errors.append(f"{artifact_id}:content_hash_mismatch")
        self._check(
            findings,
            "BRN-005",
            "Evidence custody and production",
            bool(produced) and not custody_errors,
            tuple(custody_errors) if custody_errors else tuple(sorted(produced)),
            "Every produced artifact has a monotonic, hash-stable custody trail.",
        )

        deposition = projection.deposition_record
        witness_tokens = set(sealed.witness_fact_frontier)
        used_tokens = set(deposition.get("knowledge_tokens", ()))
        self._check(
            findings,
            "BRN-006",
            "Witness-limited deposition",
            bool(deposition) and used_tokens.issubset(witness_tokens) and not deposition.get("oracle_material_used", True),
            tuple(sorted(used_tokens)),
            "The modeled witness answers use only the witness projection and explicitly avoid the oracle.",
        )

        expert = projection.expert_opinion
        expert_sources = set(expert.get("source_artifact_ids", ()))
        self._check(
            findings,
            "BRN-007",
            "Independent expert source boundary",
            bool(expert)
            and expert_sources.issubset(set(sealed.expert_authorized_artifacts))
            and expert_sources.issubset(produced)
            and not expert.get("oracle_material_used", True)
            and expert.get("independence_attested") is True,
            tuple(sorted(expert_sources)),
            "The expert opinion is derived only from the authorized produced record and carries an independence attestation.",
        )

        voice_pairs = {
            (item.author_id, item.voice_signature)
            for item in matter.evidence_inventory
            if item.artifact_id in produced
        }
        authors = {author for author, _ in voice_pairs}
        signatures = {signature for _, signature in voice_pairs}
        self._check(
            findings,
            "BRN-008",
            "Persona and voice separation",
            len(authors) >= 3 and len(signatures) == len(authors),
            tuple(f"{author}:{signature}" for author, signature in sorted(voice_pairs)),
            "Produced records retain distinct author-level voice signatures without using protected-class stereotypes.",
        )

        finance_errors = projection.finance.invariant_errors()
        self._check(
            findings,
            "BRN-009",
            "Billing, reduction appeal, AR, and cash reconciliation",
            not finance_errors
            and projection.finance.appeal_recovery > Decimal("0.00")
            and projection.finance.accounts_receivable == Decimal("0.00"),
            tuple(finance_errors) if finance_errors else (
                f"approved:{projection.finance.approved}",
                f"appeal_recovery:{projection.finance.appeal_recovery}",
                f"cash:{projection.finance.cash}",
            ),
            "The invoice reduction, appeal recovery, payment, and balances reconcile.",
        )

        required_close = {
            "procedural_complete",
            "final_report_delivered",
            "retention_scheduled",
            "conflict_history_updated",
            "finance_reconciled",
        }
        self._check(
            findings,
            "BRN-010",
            "Matter close conditions",
            projection.closed and required_close.issubset(projection.close_conditions),
            tuple(sorted(projection.close_conditions)),
            "Closure requires procedure, reporting, retention, conflict history, and finance conditions.",
        )

        self._check(
            findings,
            "BRN-011",
            "World outcome authority",
            projection.outcome_source == "world_kernel"
            and projection.resolution_outcome in {
                "defense_favorable", "claimant_favorable", "mixed_compromise"
            },
            (projection.outcome_source, projection.resolution_outcome),
            "The world kernel, not a firm arm or renderer, owns the synthetic outcome.",
        )

        passed = all(item.status == "pass" for item in findings)
        conflict_ids = tuple(sorted(detected_conflicts))
        report_payload = {
            "auditor": "Berean",
            "revision": self.revision,
            "plane": "evaluation",
            "passed": passed,
            "findings": findings,
            "detected_conflict_ids": conflict_ids,
        }
        return AuditReport(
            auditor="Berean",
            revision=self.revision,
            plane="evaluation",
            passed=passed,
            findings=tuple(findings),
            detected_conflict_ids=conflict_ids,
            report_hash=digest(report_payload),
        )

    @staticmethod
    def _detect_conflicts(artifacts: tuple[Any, ...], produced: set[str]) -> set[str]:
        values: dict[str, set[str]] = {}
        for artifact in artifacts:
            if artifact.artifact_id not in produced:
                continue
            for claim in artifact.claims:
                values.setdefault(claim.fact_id, set()).add(claim.value)
        return {fact_id for fact_id, observed in values.items() if len(observed) > 1}

    @staticmethod
    def _check(
        findings: list[AuditFinding],
        code: str,
        title: str,
        passed: bool,
        evidence: tuple[str, ...],
        explanation: str,
    ) -> None:
        findings.append(
            AuditFinding(
                code=code,
                title=title,
                status="pass" if passed else "fail",
                severity="error",
                evidence=evidence,
                explanation=explanation,
            )
        )
