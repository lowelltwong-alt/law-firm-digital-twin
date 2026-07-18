from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any, Iterable

from .berean import BereanAuditor
from .hashio import canonical_json, digest
from .models import Arm, Command, Event, Route
from .rules import (
    PRIMARY_DEADLINE_CALCULATOR,
    SECONDARY_DEADLINE_CALCULATOR,
    calculate_deadlines_primary,
    calculate_deadlines_secondary,
    placeholder_data_first_rule_pack,
)
from .world import EvidenceArtifact, WorldBundle, build_employment_world


class GateError(ValueError):
    pass


@dataclass
class FinanceLedger:
    work: Decimal = Decimal("0.00")
    wip: Decimal = Decimal("0.00")
    submitted: Decimal = Decimal("0.00")
    approved: Decimal = Decimal("0.00")
    reduced: Decimal = Decimal("0.00")
    appeal_recovery: Decimal = Decimal("0.00")
    accounts_receivable: Decimal = Decimal("0.00")
    cash: Decimal = Decimal("0.00")
    write_off: Decimal = Decimal("0.00")

    def record(self, amount: Decimal) -> None:
        if amount <= 0:
            raise GateError("time value must be positive")
        self.work += amount
        self.wip += amount

    def submit(self) -> Decimal:
        if self.wip <= 0:
            raise GateError("invoice requires positive WIP")
        amount = self.wip
        self.wip = Decimal("0.00")
        self.submitted += amount
        return amount

    def audit(self, reduction: Decimal) -> None:
        if reduction < 0 or reduction > self.submitted:
            raise GateError("carrier reduction is out of bounds")
        self.reduced = reduction
        self.approved = self.submitted - reduction
        self.accounts_receivable = self.approved

    def appeal(self, recovered: Decimal) -> None:
        if recovered <= 0 or recovered > self.reduced:
            raise GateError("appeal recovery is out of bounds")
        self.reduced -= recovered
        self.approved += recovered
        self.appeal_recovery += recovered
        self.accounts_receivable += recovered

    def apply_payment(self, cash: Decimal) -> None:
        if cash < 0 or cash > self.accounts_receivable:
            raise GateError("payment is out of bounds")
        self.cash += cash
        self.accounts_receivable -= cash

    def invariant_errors(self) -> list[str]:
        errors: list[str] = []
        if self.work != self.wip + self.submitted:
            errors.append("work must equal wip plus submitted")
        if self.submitted != self.approved + self.reduced:
            errors.append("submitted must equal approved plus reduced")
        if self.approved != self.accounts_receivable + self.cash + self.write_off:
            errors.append("approved must equal AR plus cash plus write-off")
        return errors


@dataclass
class G2Projection:
    matter_status: str = "new"
    deadlines: dict[str, int] = field(default_factory=dict)
    deadline_proposal: dict[str, int] = field(default_factory=dict)
    deadline_audit: dict[str, str] = field(default_factory=dict)
    deadline_verifier: str = ""
    authority_holds: set[str] = field(default_factory=set)
    oracle_access_attempts: int = 0
    accepted_oracle_reads: int = 0
    human_gate_bypasses: int = 0
    evidence_status: dict[str, str] = field(default_factory=dict)
    custody_log: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    produced_artifact_ids: list[str] = field(default_factory=list)
    artifact_hashes: list[str] = field(default_factory=list)
    review_conflict_candidates: list[str] = field(default_factory=list)
    deposition_record: dict[str, Any] = field(default_factory=dict)
    expert_opinion: dict[str, Any] = field(default_factory=dict)
    resolution_milestones: list[str] = field(default_factory=list)
    resolution_outcome: str = ""
    outcome_source: str = ""
    time_entries: list[dict[str, str]] = field(default_factory=list)
    finance: FinanceLedger = field(default_factory=FinanceLedger)
    close_conditions: set[str] = field(default_factory=set)
    closed: bool = False
    route: str = ""


@dataclass(frozen=True)
class VerbPolicy:
    roles: tuple[str, ...]
    authority: tuple[str, ...] = ()
    knowledge: tuple[str, ...] = ()


VERB_POLICIES: dict[str, VerbPolicy] = {
    "receive_referral": VerbPolicy(("intake",), ("receive_referral",), ("referral_summary",)),
    "submit_conflict_result": VerbPolicy(("conflicts",), ("conflict_search",), ("party_names",)),
    "record_lawyer_gate": VerbPolicy(("lawyer",), ("lawyer_conflict_determination",), ("conflict_result",)),
    "open_matter": VerbPolicy(("lawyer",), ("matter_opening",), ("referral_summary",)),
    "calculate_deadlines": VerbPolicy(("docketing",), ("deadline_proposal",), ("rule_pack",)),
    "verify_deadlines": VerbPolicy(("deadline_reviewer",), ("deadline_verify",), ("rule_pack", "deadline_proposal")),
    "issue_preservation": VerbPolicy(("paralegal",), ("preservation",), ("evidence_inventory_metadata",)),
    "collect_evidence": VerbPolicy(("paralegal",), ("collection",), ("preservation_issued",)),
    "review_evidence": VerbPolicy(("lawyer",), ("legal_work",), ("collected_evidence",)),
    "produce_discovery": VerbPolicy(("paralegal",), ("production",), ("review_complete",)),
    "take_deposition": VerbPolicy(("lawyer",), ("legal_work",), ("produced_evidence",)),
    "retain_expert": VerbPolicy(("lawyer",), ("retain_expert",), ("deposition_transcript",)),
    "settle_case": VerbPolicy(("lawyer",), ("resolution",), ("expert_opinion",)),
    "mediate_to_impasse": VerbPolicy(("lawyer",), ("resolution",), ("expert_opinion",)),
    "resolve_dispositive": VerbPolicy(("lawyer",), ("resolution",), ("expert_opinion",)),
    "try_and_appeal": VerbPolicy(("lawyer",), ("resolution",), ("expert_opinion",)),
    "record_time": VerbPolicy(("lawyer", "paralegal"), ("record_time",), ("initial_record",)),
    "submit_invoice": VerbPolicy(("billing",), ("billing",), ("guidelines",)),
    "carrier_audit": VerbPolicy(("carrier",), ("carrier_audit",), ("guidelines",)),
    "appeal_reduction": VerbPolicy(("billing",), ("billing",), ("guidelines",)),
    "apply_payment": VerbPolicy(("billing",), ("billing",), ("guidelines",)),
    "finalize_closeout": VerbPolicy(("lawyer",), ("matter_close",), ("expert_opinion",)),
    "close_matter": VerbPolicy(("lawyer",), ("matter_close",), ("expert_opinion",)),
    "read_oracle": VerbPolicy(("lawyer",), ("legal_work",), ("initial_record",)),
}


class G2WorldKernel:
    def __init__(self, *, run_id: str, bundle: WorldBundle, arm: Arm, route: Route):
        self.run_id = run_id
        self.bundle = bundle
        self.arm = arm
        self.route = route
        self.clock = 0
        self.events: list[Event] = []
        self.denials: list[dict[str, Any]] = []
        self.projection = G2Projection(route=route.value)
        self.authority: dict[str, set[str]] = {
            actor_id: set(profile.initial_authority)
            for actor_id, profile in bundle.matter.actors.items()
        }
        self.knowledge: dict[str, set[str]] = {
            actor_id: set(profile.initial_knowledge)
            for actor_id, profile in bundle.matter.actors.items()
        }

    def submit(self, command: Command) -> Event:
        if command.matter_id != self.bundle.matter.matter_id:
            self._deny(command, "matter_boundary", (command.matter_id,))
        profile = self.bundle.matter.actors.get(command.actor_id)
        if profile is None:
            self._deny(command, "unknown_actor", (command.actor_id,))
        policy = VERB_POLICIES.get(command.verb)
        if policy is None:
            self._deny(command, "unsupported_verb", (command.verb,))
        if profile.role_id != command.role_id:
            self._deny(command, "role_mismatch", (command.role_id,))
        if profile.role_id not in policy.roles:
            self._deny(command, "verb_role_forbidden", tuple(policy.roles))
        if command.verb == "read_oracle":
            self.projection.oracle_access_attempts += 1
            self._deny(command, "oracle_boundary", ("sealed_world",))

        required_authority = set(policy.authority) | set(command.requires_authority)
        required_knowledge = set(policy.knowledge) | set(command.requires_knowledge)
        effective_authority = tuple(sorted(required_authority))
        missing_authority = tuple(sorted(required_authority - self.authority[command.actor_id]))
        missing_knowledge = tuple(sorted(required_knowledge - self.knowledge[command.actor_id]))
        if missing_authority:
            self._deny(command, "missing_authority", missing_authority)
        if missing_knowledge:
            self._deny(command, "missing_knowledge", missing_knowledge)

        self.clock += 1
        payload = self._transition(command)
        event = Event(
            event_id=f"EV-{len(self.events) + 1:04d}-{digest({'run': self.run_id, 'cmd': command.command_id})[:10]}",
            run_id=self.run_id,
            matter_id=command.matter_id,
            simulated_at=self.clock,
            event_type=f"{command.verb}_accepted",
            command_id=command.command_id,
            actor_id=command.actor_id,
            role_id=command.role_id,
            knowledge_scope=f"actor:{command.actor_id}:{digest(sorted(self.knowledge[command.actor_id]))[:10]}",
            authority_basis=";".join(effective_authority) or "front_door",
            payload=payload,
            input_hash=digest(asdict(command)),
            output_hash=digest(payload),
            random_stream_key=digest({"run": self.run_id, "clock": self.clock, "verb": command.verb})[:16],
            treatment_arm=self.arm.value,
        )
        self.events.append(event)
        return event

    def _deny(self, command: Command, reason: str, missing: tuple[str, ...]) -> None:
        self.denials.append(
            {
                "command_id": command.command_id,
                "verb": command.verb,
                "actor_id": command.actor_id,
                "reason": reason,
                "missing": missing,
                "denial_hash": digest(
                    {
                        "command_id": command.command_id,
                        "verb": command.verb,
                        "actor_id": command.actor_id,
                        "reason": reason,
                        "missing": missing,
                    }
                ),
            }
        )
        raise GateError(f"{reason}: {list(missing)}")

    def _grant(
        self,
        actor_id: str,
        *,
        authority: Iterable[str] = (),
        knowledge: Iterable[str] = (),
    ) -> None:
        self.authority[actor_id].update(authority)
        self.knowledge[actor_id].update(knowledge)

    def _artifact(self, artifact_id: str) -> EvidenceArtifact:
        for artifact in self.bundle.matter.evidence_inventory:
            if artifact.artifact_id == artifact_id:
                return artifact
        raise GateError(f"unknown artifact: {artifact_id}")
    def _transition(self, command: Command) -> dict[str, Any]:
        verb = command.verb
        payload = dict(command.payload)
        projection = self.projection

        if verb == "receive_referral":
            projection.matter_status = "referral_received"
            self._grant("conflicts_analyst", authority=("conflict_search",), knowledge=("party_names",))
            self._grant("responsible_lawyer", knowledge=("referral_summary",))
        elif verb == "submit_conflict_result":
            projection.authority_holds.add("affected_client_consent")
            self._grant(
                "responsible_lawyer",
                authority=("lawyer_conflict_determination",),
                knowledge=("conflict_result", "party_names"),
            )
        elif verb == "record_lawyer_gate":
            gate = str(payload["gate"])
            if gate not in projection.authority_holds:
                raise GateError(f"human gate not pending: {gate}")
            projection.authority_holds.remove(gate)
            self._grant("responsible_lawyer", authority=(str(payload["grants"]),))
        elif verb == "open_matter":
            if projection.authority_holds:
                raise GateError(f"unresolved authority holds: {sorted(projection.authority_holds)}")
            projection.matter_status = "matter_opened"
            self._grant(
                "responsible_lawyer",
                authority=("legal_work", "retain_expert", "resolution", "matter_close", "record_time"),
                knowledge=("coverage_posture", "guidelines", "initial_record"),
            )
            self._grant(
                "litigation_paralegal",
                authority=("preservation", "collection", "production", "record_time"),
                knowledge=("initial_record", "evidence_inventory_metadata"),
            )
            self._grant(
                "docketing_specialist",
                authority=("deadline_proposal",),
                knowledge=("initial_record", "rule_pack"),
            )
            self._grant(
                "deadline_reviewer",
                authority=("deadline_verify",),
                knowledge=("initial_record", "rule_pack"),
            )
            self._grant(
                "billing_specialist",
                authority=("billing",),
                knowledge=("guidelines", "initial_record"),
            )
        elif verb == "calculate_deadlines":
            filed_day = int(payload.get("complaint_filed_day", 0))
            proposal = calculate_deadlines_primary(self.bundle.matter.rule_pack, filed_day)
            projection.deadline_proposal = proposal
            projection.deadline_audit = {
                "primary_actor": command.actor_id,
                "primary_calculator": PRIMARY_DEADLINE_CALCULATOR,
            }
            payload["proposal"] = proposal
            payload["calculator_revision"] = PRIMARY_DEADLINE_CALCULATOR
            self._grant("deadline_reviewer", knowledge=("deadline_proposal",))
        elif verb == "verify_deadlines":
            if not projection.deadline_proposal:
                raise GateError("deadline proposal must exist before verification")
            filed_day = int(payload.get("complaint_filed_day", 0))
            independent = calculate_deadlines_secondary(self.bundle.matter.rule_pack, filed_day)
            if independent != projection.deadline_proposal:
                raise GateError("independent deadline calculation mismatch")
            if projection.deadline_audit.get("primary_actor") == command.actor_id:
                raise GateError("deadline verifier must be a different actor")
            projection.deadlines = independent
            projection.deadline_audit.update({
                "secondary_actor": command.actor_id,
                "secondary_calculator": SECONDARY_DEADLINE_CALCULATOR,
            })
            projection.deadline_verifier = f"{command.actor_id}:{SECONDARY_DEADLINE_CALCULATOR}"
            payload["verified_deadlines"] = independent
            payload["calculator_revision"] = SECONDARY_DEADLINE_CALCULATOR
            self._grant("responsible_lawyer", knowledge=("verified_deadlines",))
        elif verb == "issue_preservation":
            for artifact in self.bundle.matter.evidence_inventory:
                projection.evidence_status[artifact.artifact_id] = "preserved"
                created = artifact.custody[0]
                projection.custody_log[artifact.artifact_id] = [asdict(created)]
            self._grant("litigation_paralegal", knowledge=("preservation_issued",))
        elif verb == "collect_evidence":
            for artifact in self.bundle.matter.evidence_inventory:
                if projection.evidence_status.get(artifact.artifact_id) != "preserved":
                    raise GateError(f"artifact not preserved: {artifact.artifact_id}")
                projection.evidence_status[artifact.artifact_id] = "collected"
                projection.custody_log[artifact.artifact_id].extend(
                    asdict(step) for step in artifact.custody[1:]
                )
            self._grant("responsible_lawyer", knowledge=("collected_evidence",))
            self._grant("litigation_paralegal", knowledge=("collected_evidence",))
        elif verb == "review_evidence":
            selected: list[str] = []
            claims: dict[str, set[str]] = {}
            for artifact in self.bundle.matter.evidence_inventory:
                if projection.evidence_status.get(artifact.artifact_id) != "collected":
                    raise GateError(f"artifact not collected: {artifact.artifact_id}")
                if artifact.responsive and not artifact.privileged:
                    selected.append(artifact.artifact_id)
                    projection.evidence_status[artifact.artifact_id] = "reviewed"
                    projection.custody_log[artifact.artifact_id].append(
                        {
                            "action": "reviewed",
                            "actor_id": command.actor_id,
                            "simulated_day": 51,
                            "object_hash": artifact.custody[0].object_hash,
                        }
                    )
                    for claim in artifact.claims:
                        claims.setdefault(claim.fact_id, set()).add(claim.value)
                else:
                    projection.evidence_status[artifact.artifact_id] = "withheld_nonresponsive"
            projection.review_conflict_candidates = sorted(
                fact_id for fact_id, values in claims.items() if len(values) > 1
            )
            payload["selected_artifact_ids"] = selected
            payload["conflict_candidates"] = list(projection.review_conflict_candidates)
            self._grant("litigation_paralegal", knowledge=("review_complete",))
            self._grant("responsible_lawyer", knowledge=("review_complete",))
        elif verb == "produce_discovery":
            selected = [
                artifact.artifact_id
                for artifact in self.bundle.matter.evidence_inventory
                if projection.evidence_status.get(artifact.artifact_id) == "reviewed"
            ]
            if not selected:
                raise GateError("production cannot be empty")
            for artifact_id in selected:
                artifact = self._artifact(artifact_id)
                projection.evidence_status[artifact_id] = "produced"
                projection.produced_artifact_ids.append(artifact_id)
                projection.artifact_hashes.append(artifact.content_hash)
                projection.custody_log[artifact_id].append(
                    {
                        "action": "produced",
                        "actor_id": command.actor_id,
                        "simulated_day": 52,
                        "object_hash": artifact.custody[0].object_hash,
                    }
                )
            payload["produced_artifact_ids"] = selected
            payload["production_hash"] = digest(
                [(artifact_id, self._artifact(artifact_id).content_hash) for artifact_id in selected]
            )
            self._grant("responsible_lawyer", knowledge=("produced_evidence",))
        elif verb == "take_deposition":
            witness = self.bundle.matter.actors["hr_witness"]
            projection.deposition_record = {
                "witness_id": witness.actor_id,
                "knowledge_tokens": list(self.bundle.sealed.witness_fact_frontier),
                "answers": (
                    "I recall expecting another HR review before a final recommendation.",
                    "The policy called for HR consultation, although operations could document an exception.",
                    "I do not remember the exact hour and would need the emails for the sequence.",
                ),
                "memory_profile": asdict(witness.memory),
                "oracle_material_used": False,
            }
            projection.artifact_hashes.append(digest(projection.deposition_record))
            self._grant("responsible_lawyer", knowledge=("deposition_transcript",))
        elif verb == "retain_expert":
            sources = [
                artifact_id
                for artifact_id in projection.produced_artifact_ids
                if artifact_id in self.bundle.sealed.expert_authorized_artifacts
            ]
            projection.expert_opinion = {
                "expert_id": "independent_expert",
                "source_artifact_ids": sources,
                "method": "compare documented process, chronology, and policy without deciding credibility",
                "limitations": "no opinion on legal liability, intent, or facts outside the produced record",
                "opinion": "The produced chronology contains a material process and timing inconsistency.",
                "independence_attested": True,
                "oracle_material_used": False,
            }
            projection.artifact_hashes.append(digest(projection.expert_opinion))
            self._grant("responsible_lawyer", knowledge=("expert_opinion",))
        elif verb in {"settle_case", "mediate_to_impasse", "resolve_dispositive", "try_and_appeal"}:
            expected = {
                Route.EARLY_SETTLEMENT: "settle_case",
                Route.MEDIATION_IMPASSE: "mediate_to_impasse",
                Route.DISPOSITIVE: "resolve_dispositive",
                Route.TRIAL_APPEAL: "try_and_appeal",
            }[self.route]
            if verb != expected:
                raise GateError(f"route command mismatch: expected {expected}")
            projection.resolution_milestones = {
                "settle_case": ["demand_evaluated", "authority_obtained", "synthetic_release_executed"],
                "mediate_to_impasse": ["mediation_statement", "session_completed", "impasse_recorded"],
                "resolve_dispositive": ["motion_filed", "opposition_modeled", "order_entered"],
                "try_and_appeal": ["pretrial_completed", "trial_modeled", "judgment_entered", "appeal_modeled"],
            }[verb]
            projection.resolution_outcome = {
                "defense_favorable": "defense_favorable",
                "claimant_favorable": "claimant_favorable",
                "balanced": "mixed_compromise",
            }[self.bundle.sealed.target_posture]
            projection.outcome_source = "world_kernel"
            projection.matter_status = f"resolved_{self.route.value}"
            payload["milestones"] = list(projection.resolution_milestones)
            payload["synthetic_outcome"] = projection.resolution_outcome
        elif verb == "record_time":
            amount = Decimal(str(payload["amount"]))
            projection.finance.record(amount)
            entry = {
                "timekeeper_id": command.actor_id,
                "task_code": str(payload["task_code"]),
                "narrative": str(payload["narrative"]),
                "amount": str(amount),
                "arm": self.arm.value,
            }
            projection.time_entries.append(entry)
            payload["entry_hash"] = digest(entry)
        elif verb == "submit_invoice":
            amount = projection.finance.submit()
            payload["submitted_amount"] = str(amount)
            payload["time_entry_count"] = len(projection.time_entries)
        elif verb == "carrier_audit":
            reduction = Decimal(str(payload["reduction"]))
            projection.finance.audit(reduction)
            payload["approved_amount"] = str(projection.finance.approved)
        elif verb == "appeal_reduction":
            recovered = Decimal(str(payload["recovered"]))
            projection.finance.appeal(recovered)
            payload["post_appeal_approved"] = str(projection.finance.approved)
        elif verb == "apply_payment":
            cash = Decimal(str(payload["cash"]))
            projection.finance.apply_payment(cash)
            payload["remaining_ar"] = str(projection.finance.accounts_receivable)
        elif verb == "finalize_closeout":
            if not projection.resolution_outcome:
                raise GateError("resolution must precede closeout")
            projection.close_conditions.update(
                {
                    "procedural_complete",
                    "final_report_delivered",
                    "retention_scheduled",
                    "conflict_history_updated",
                }
            )
            if not projection.finance.invariant_errors() and projection.finance.accounts_receivable == Decimal("0.00"):
                projection.close_conditions.add("finance_reconciled")
        elif verb == "close_matter":
            required = {
                "procedural_complete",
                "final_report_delivered",
                "retention_scheduled",
                "conflict_history_updated",
                "finance_reconciled",
            }
            missing = required - projection.close_conditions
            if missing:
                raise GateError(f"close conditions missing: {sorted(missing)}")
            if projection.finance.invariant_errors():
                raise GateError("finance invariants must reconcile before close")
            projection.closed = True
            projection.matter_status = "closed"
        else:
            raise GateError(f"unsupported command: {verb}")
        return payload

    def canonical_event_hash(self) -> str:
        neutral_events: list[dict[str, Any]] = []
        for event in self.events:
            item = asdict(event)
            item.pop("run_id", None)
            item.pop("event_id", None)
            item.pop("random_stream_key", None)
            neutral_events.append(item)
        return digest(neutral_events)

    def denial_hash(self) -> str:
        return digest(self.denials)

    def projection_hash(self) -> str:
        return digest(self.projection)

def _command(
    index: int,
    verb: str,
    bundle: WorldBundle,
    actor_id: str,
    payload: dict[str, Any],
    authority: tuple[str, ...] = (),
    knowledge: tuple[str, ...] = (),
    *,
    suffix: str = "",
) -> Command:
    role_id = bundle.matter.actors[actor_id].role_id
    token = f"-{suffix}" if suffix else ""
    return Command(
        command_id=f"CMD-{index:03d}-{verb}{token}",
        verb=verb,
        actor_id=actor_id,
        role_id=role_id,
        matter_id=bundle.matter.matter_id,
        payload=payload,
        requires_authority=authority,
        requires_knowledge=knowledge,
    )


def _workflow_commands(bundle: WorldBundle, arm: Arm, route: Route) -> list[Command]:
    resolution_verb = {
        Route.EARLY_SETTLEMENT: "settle_case",
        Route.MEDIATION_IMPASSE: "mediate_to_impasse",
        Route.DISPOSITIVE: "resolve_dispositive",
        Route.TRIAL_APPEAL: "try_and_appeal",
    }[route]
    time_values = (
        (Decimal("600.00"), Decimal("300.00"))
        if arm is Arm.TRADITIONAL
        else (Decimal("450.00"), Decimal("250.00"))
    )
    reduction = Decimal("90.00") if arm is Arm.TRADITIONAL else Decimal("70.00")
    return [
        _command(1, "receive_referral", bundle, "intake_coordinator", {"referral_id": bundle.matter.referral_id}, ("receive_referral",), ("referral_summary",)),
        _command(2, "submit_conflict_result", bundle, "conflicts_analyst", {"conflict": "prior affiliate contact requires affected-client consent"}, ("conflict_search",), ("party_names",)),
        _command(3, "record_lawyer_gate", bundle, "responsible_lawyer", {"gate": "affected_client_consent", "grants": "matter_opening"}, ("lawyer_conflict_determination",), ("conflict_result",)),
        _command(4, "open_matter", bundle, "responsible_lawyer", {"coverage": "reservation_of_rights", "guidelines": "synthetic_ocg_v0"}, ("matter_opening",), ("referral_summary",)),
        _command(5, "calculate_deadlines", bundle, "docketing_specialist", {"complaint_filed_day": 0}, ("deadline_proposal",), ("rule_pack",)),
        _command(6, "verify_deadlines", bundle, "deadline_reviewer", {"complaint_filed_day": 0}, ("deadline_verify",), ("rule_pack", "deadline_proposal")),
        _command(7, "issue_preservation", bundle, "litigation_paralegal", {"scope": "synthetic_employment_sources"}, ("preservation",), ("evidence_inventory_metadata",)),
        _command(8, "collect_evidence", bundle, "litigation_paralegal", {"method": "deterministic_synthetic_collection"}, ("collection",), ("preservation_issued",)),
        _command(9, "review_evidence", bundle, "responsible_lawyer", {"protocol": "responsive_nonprivileged_g2"}, ("legal_work",), ("collected_evidence",)),
        _command(10, "produce_discovery", bundle, "litigation_paralegal", {"production": "G2-PROD-001"}, ("production",), ("review_complete",)),
        _command(11, "take_deposition", bundle, "responsible_lawyer", {"witness_id": "hr_witness"}, ("legal_work",), ("produced_evidence",)),
        _command(12, "retain_expert", bundle, "responsible_lawyer", {"expert_id": "independent_expert"}, ("retain_expert",), ("deposition_transcript",)),
        _command(13, resolution_verb, bundle, "responsible_lawyer", {"route": route.value}, ("resolution",), ("expert_opinion",)),
        _command(14, "record_time", bundle, "responsible_lawyer", {"amount": str(time_values[0]), "task_code": "L120", "narrative": "Analyze synthetic evidence and resolution route."}, ("record_time",), ("initial_record",), suffix="lawyer"),
        _command(15, "record_time", bundle, "litigation_paralegal", {"amount": str(time_values[1]), "task_code": "L320", "narrative": "Preserve, collect, and prepare synthetic production."}, ("record_time",), ("review_complete",), suffix="paralegal"),
        _command(16, "submit_invoice", bundle, "billing_specialist", {}, ("billing",), ("guidelines",)),
        _command(17, "carrier_audit", bundle, "claim_handler", {"reduction": str(reduction), "reason": "synthetic_guideline_adjustment"}, ("carrier_audit",), ("guidelines",)),
        _command(18, "appeal_reduction", bundle, "billing_specialist", {"recovered": "20.00", "basis": "task_and_narrative_support"}, ("billing",), ("guidelines",)),
        _command(19, "apply_payment", bundle, "billing_specialist", {"cash": str(sum(time_values) - reduction + Decimal("20.00"))}, ("billing",), ("guidelines",)),
        _command(20, "finalize_closeout", bundle, "responsible_lawyer", {"retention": "scheduled", "final_report": "delivered", "conflict_history": "updated"}, ("matter_close",), ("expert_opinion",)),
        _command(21, "close_matter", bundle, "responsible_lawyer", {}, ("matter_close",), ("expert_opinion",)),
    ]


def _execute_once(seed: str, arm: Arm, route: Route, *, run_suffix: str) -> tuple[G2WorldKernel, list[Command]]:
    serialized = _build_serialized_cassette(seed, arm, route)
    return _execute_serialized_cassette(serialized, run_suffix=run_suffix)


def _cassette_hash(bundle: WorldBundle) -> str:
    return digest(
        {
            "renderer": "deterministic_g2_cassette_v1",
            "artifacts": [
                (artifact.artifact_id, artifact.content_hash, artifact.voice_signature)
                for artifact in bundle.matter.evidence_inventory
            ],
        }
    )

def _command_from_record(record: dict[str, Any]) -> Command:
    return Command(
        command_id=str(record["command_id"]),
        verb=str(record["verb"]),
        actor_id=str(record["actor_id"]),
        role_id=str(record["role_id"]),
        matter_id=str(record["matter_id"]),
        payload=dict(record.get("payload", {})),
        requires_authority=tuple(record.get("requires_authority", ())),
        requires_knowledge=tuple(record.get("requires_knowledge", ())),
    )


def _build_serialized_cassette(seed: str, arm: Arm, route: Route) -> str:
    bundle = build_employment_world(seed, placeholder_data_first_rule_pack())
    commands = _workflow_commands(bundle, arm, route)
    premature_open = _command(
        90, "open_matter", bundle, "responsible_lawyer",
        {"probe": "must_be_denied_before_consent"},
        ("matter_opening",), ("referral_summary",), suffix="authority-probe",
    )
    oracle_probe = _command(
        99, "read_oracle", bundle, "responsible_lawyer", {},
        ("legal_work",), ("initial_record",), suffix="oracle-probe",
    )
    attempts: list[dict[str, Any]] = []
    for command in commands[:2]:
        attempts.append({"expected": "accepted", "command": asdict(command)})
    attempts.append({"expected": "denied", "reason": "missing_authority", "command": asdict(premature_open)})
    for command in commands[2:]:
        attempts.append({"expected": "accepted", "command": asdict(command)})
    attempts.append({"expected": "denied", "reason": "oracle_boundary", "command": asdict(oracle_probe)})
    cassette = {
        "revision": "g2_attempt_cassette_v2",
        "seed": seed,
        "arm": arm.value,
        "route": route.value,
        "rule_pack_hash": digest(bundle.matter.rule_pack),
        "artifact_commitments": [
            {
                "artifact_id": artifact.artifact_id,
                "content_hash": artifact.content_hash,
                "voice_signature": artifact.voice_signature,
            }
            for artifact in bundle.matter.evidence_inventory
        ],
        "attempts": attempts,
    }
    return canonical_json(cassette)


def _execute_serialized_cassette(serialized: str, *, run_suffix: str) -> tuple[G2WorldKernel, list[Command]]:
    cassette = json.loads(serialized)
    seed = str(cassette["seed"])
    arm = Arm(str(cassette["arm"]))
    route = Route(str(cassette["route"]))
    bundle = build_employment_world(seed, placeholder_data_first_rule_pack())
    actual_commitments = [
        {
            "artifact_id": artifact.artifact_id,
            "content_hash": artifact.content_hash,
            "voice_signature": artifact.voice_signature,
        }
        for artifact in bundle.matter.evidence_inventory
    ]
    if cassette.get("rule_pack_hash") != digest(bundle.matter.rule_pack):
        raise GateError("cassette rule-pack commitment mismatch")
    if cassette.get("artifact_commitments") != actual_commitments:
        raise GateError("cassette artifact commitment mismatch")
    kernel = G2WorldKernel(
        run_id=f"RUN-{arm.value}-{route.value}-{seed}-{run_suffix}",
        bundle=bundle,
        arm=arm,
        route=route,
    )
    attempted: list[Command] = []
    for entry in cassette["attempts"]:
        command = _command_from_record(entry["command"])
        attempted.append(command)
        expected = str(entry["expected"])
        try:
            kernel.submit(command)
        except GateError:
            actual_reason = kernel.denials[-1]["reason"] if kernel.denials else "transition_rejection"
            if expected != "denied" or actual_reason != entry.get("reason"):
                raise
        else:
            if expected != "accepted":
                raise GateError(f"cassette expected denial but accepted {command.command_id}")
    return kernel, attempted


def build_g2_attempt_cassette(seed: str, arm: Arm, route: Route) -> str:
    """Build the versioned G2 attempt cassette for bounded internal adapters."""

    return _build_serialized_cassette(seed, arm, route)


def execute_g2_attempt_cassette(
    serialized: str, *, run_suffix: str
) -> tuple[G2WorldKernel, list[Command]]:
    """Execute a cassette through the kernel; adapters cannot bypass this seam."""

    return _execute_serialized_cassette(serialized, run_suffix=run_suffix)


def run_walking_skeleton(seed: str, arm: Arm, route: Route) -> dict[str, Any]:
    serialized_cassette = _build_serialized_cassette(seed, arm, route)
    kernel, commands = _execute_serialized_cassette(serialized_cassette, run_suffix="primary")
    audit = BereanAuditor().audit(kernel)
    reloaded_cassette = canonical_json(json.loads(serialized_cassette))
    replay, replay_commands = _execute_serialized_cassette(reloaded_cassette, run_suffix="replay")
    replay_audit = BereanAuditor().audit(replay)

    event_hash = kernel.canonical_event_hash()
    projection_hash = kernel.projection_hash()
    denial_hash = kernel.denial_hash()
    cassette_hash = digest(json.loads(serialized_cassette))
    replay_verified = (
        serialized_cassette == reloaded_cassette
        and event_hash == replay.canonical_event_hash()
        and projection_hash == replay.projection_hash()
        and denial_hash == replay.denial_hash()
        and digest(commands) == digest(replay_commands)
        and audit.report_hash == replay_audit.report_hash
    )
    produced = [
        {
            "artifact_id": artifact.artifact_id,
            "family": artifact.family,
            "author_id": artifact.author_id,
            "created_day": artifact.created_day,
            "content_hash": artifact.content_hash,
            "native_format": artifact.native_format,
        }
        for artifact in kernel.bundle.matter.evidence_inventory
        if artifact.artifact_id in kernel.projection.produced_artifact_ids
    ]
    return {
        "seed": seed,
        "arm": arm.value,
        "route": route.value,
        "matter": kernel.bundle.matter.operating_view(),
        "event_count": len(kernel.events),
        "event_hash": event_hash,
        "denial_hash": denial_hash,
        "projection_hash": projection_hash,
        "cassette_hash": cassette_hash,
        "command_cassette_hash": digest(commands),
        "replay_verified": replay_verified,
        "closed": kernel.projection.closed,
        "deadlines": dict(kernel.projection.deadlines),
        "finance_errors": kernel.projection.finance.invariant_errors(),
        "finance": asdict(kernel.projection.finance),
        "oracle_blocked": kernel.projection.oracle_access_attempts >= 1 and kernel.projection.accepted_oracle_reads == 0,
        "blocked_human_gate_attempts": len(
            [
                item for item in kernel.denials
                if item["reason"] == "missing_authority" and "matter_opening" in item["missing"]
            ]
        ),
        "human_gate_bypasses": kernel.projection.human_gate_bypasses,
        "produced_evidence": produced,
        "evidence_status": dict(kernel.projection.evidence_status),
        "deposition": dict(kernel.projection.deposition_record),
        "expert_opinion": dict(kernel.projection.expert_opinion),
        "resolution_milestones": list(kernel.projection.resolution_milestones),
        "resolution_outcome": kernel.projection.resolution_outcome,
        "close_conditions": sorted(kernel.projection.close_conditions),
        "berean_audit": asdict(audit),
        "treatment_metrics": {
            "work_value": str(kernel.projection.finance.work),
            "accepted_event_count": len(kernel.events),
            "denied_boundary_probe_count": len(kernel.denials),
            "produced_artifact_count": len(produced),
            "audit_passed": audit.passed,
        },
        "synthetic_non_predictive": True,
    }


def _blind_pair(seed: str, route: Route, pair: list[dict[str, Any]]) -> dict[str, Any]:
    del seed
    work_values = sorted(Decimal(run["treatment_metrics"]["work_value"]) for run in pair)
    records = [
        {
            "blind_label": label,
            "evaluation_status": "sealed_pending_controlled_reveal",
            "audit_passed": all(run["treatment_metrics"]["audit_passed"] for run in pair),
            "closed": all(run["closed"] for run in pair),
        }
        for label in ("arm_a", "arm_b")
    ]
    paired_metrics = {
        "work_value_multiset": [str(value) for value in work_values],
        "absolute_work_value_difference": str(abs(work_values[1] - work_values[0])),
        "mapping_to_labels": "withheld",
    }
    return {
        "route": route.value,
        "records": records,
        "paired_unordered_metrics": paired_metrics,
        "treatment_mapping_disclosed": False,
        "label": "synthetic treatment-blind comparison; non-predictive",
        "comparison_hash": digest({"records": records, "paired_unordered_metrics": paired_metrics}),
    }


def run_all_routes(seed: str = "alpha") -> dict[str, Any]:
    internal_runs = [
        run_walking_skeleton(seed, arm, route)
        for arm in (Arm.TRADITIONAL, Arm.AI_FIRST)
        for route in Route
    ]
    comparisons: list[dict[str, Any]] = []
    blinded_runs: list[dict[str, Any]] = []
    for route in Route:
        pair = [run for run in internal_runs if run["route"] == route.value]
        comparisons.append(_blind_pair(seed, route, pair))
        common_outcomes = {run["resolution_outcome"] for run in pair}
        jurisdiction_labels = {run["matter"]["rule_pack"]["jurisdiction_label"] for run in pair}
        common_record = {
            "route": route.value,
            "closed": all(run["closed"] for run in pair),
            "finance_errors": sorted({error for run in pair for error in run["finance_errors"]}),
            "audit_passed": all(run["berean_audit"]["passed"] for run in pair),
            "resolution_outcome": next(iter(common_outcomes)) if len(common_outcomes) == 1 else "divergent_withheld",
            "jurisdiction_label": next(iter(jurisdiction_labels)) if len(jurisdiction_labels) == 1 else "divergent_withheld",
            "synthetic_non_predictive": True,
        }
        for label in ("arm_a", "arm_b"):
            blinded_runs.append({"blind_label": label, **common_record})
    return {
        "simulator": "Law Firm Digital Twin",
        "scope": "G0-G2 evaluator export",
        "runs": blinded_runs,
        "treatment_blind_comparisons": comparisons,
        "bundle_hash": digest({"runs": blinded_runs, "comparisons": comparisons}),
        "blinding_note": "No per-arm hashes, values, or join keys are exported; reveal mapping is a separate controlled artifact and is not produced at G2.",
        "synthetic_non_predictive": True,
    }
