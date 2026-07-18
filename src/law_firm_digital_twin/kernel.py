from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal

from .factory import SyntheticMatter
from .hashio import digest
from .models import Command, Event, Projection, Route


class GateError(ValueError):
    pass


class WorldKernel:
    def __init__(self, *, run_id: str, matter: SyntheticMatter, arm_label: str, route: Route):
        self.run_id = run_id
        self.matter = matter
        self.arm_label = arm_label
        self.route = route
        self.clock = 0
        self.events: list[Event] = []
        self.projection = Projection(route=route.value)
        self.authority: set[str] = {"receive_referral"}
        self.knowledge: set[str] = {"referral_summary"}

    def submit(self, command: Command) -> Event:
        missing_authority = set(command.requires_authority) - self.authority
        missing_knowledge = set(command.requires_knowledge) - self.knowledge
        if command.verb == "read_oracle":
            self.projection.oracle_access_attempts += 1
            raise GateError("operating actors cannot read the sealed oracle")
        if missing_authority:
            raise GateError(f"missing authority: {sorted(missing_authority)}")
        if missing_knowledge:
            raise GateError(f"missing knowledge: {sorted(missing_knowledge)}")
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
            knowledge_scope="operating",
            authority_basis=";".join(command.requires_authority) or "front_door",
            payload=payload,
            input_hash=digest(asdict(command)),
            output_hash=digest(payload),
            random_stream_key=digest({"run": self.run_id, "clock": self.clock, "verb": command.verb})[:16],
            treatment_arm=None,
        )
        self.events.append(event)
        return event

    def _transition(self, command: Command) -> dict[str, object]:
        verb = command.verb
        payload = dict(command.payload)
        if verb == "receive_referral":
            self.projection.matter_status = "referral_received"
            self.authority.add("conflict_search")
            self.knowledge.add("party_names")
        elif verb == "submit_conflict_result":
            self.projection.authority_holds.add("affected_client_consent")
            self.authority.add("lawyer_conflict_determination")
        elif verb == "record_lawyer_gate":
            gate = str(payload["gate"])
            if gate in self.projection.authority_holds:
                self.projection.authority_holds.remove(gate)
            self.authority.add(str(payload["grants"]))
        elif verb == "open_matter":
            self.projection.matter_status = "matter_opened"
            self.knowledge.update({"coverage_posture", "guidelines", "initial_record"})
            self.authority.update({"deadline_proposal", "legal_work", "billing"})
        elif verb == "verify_deadlines":
            filed_day = int(payload.get("complaint_filed_day", 0))
            rp = self.matter.rule_pack
            self.projection.deadlines = {
                "response_due": filed_day + rp.response_days,
                "initial_disclosures_due": filed_day + rp.disclosure_days,
                "discovery_cutoff": filed_day + rp.discovery_cutoff_days,
            }
        elif verb == "produce_discovery":
            self.projection.artifact_hashes.append(digest({"artifact": "small_inconsistent_evidence_set", "matter": self.matter.matter_id}))
            self.knowledge.add("produced_evidence")
        elif verb == "take_deposition":
            self.projection.artifact_hashes.append(digest({"artifact": "hr_witness_deposition", "frontier": "witness_limited"}))
            self.knowledge.add("deposition_transcript")
        elif verb == "retain_expert":
            self.projection.artifact_hashes.append(digest({"artifact": "independent_hr_expert_opinion", "scope": "authorized_record"}))
            self.knowledge.add("expert_opinion")
        elif verb == "resolve_route":
            self.projection.matter_status = f"resolved_{self.route.value}"
        elif verb == "record_time":
            amount = Decimal(str(payload["amount"]))
            self.projection.finance.work += amount
            self.projection.finance.wip += amount
        elif verb == "submit_invoice":
            amount = self.projection.finance.wip
            self.projection.finance.wip = Decimal("0.00")
            self.projection.finance.submitted += amount
            payload["submitted_amount"] = str(amount)
        elif verb == "carrier_audit":
            reduction = Decimal(str(payload["reduction"]))
            self.projection.finance.reduced += reduction
            self.projection.finance.approved += self.projection.finance.submitted - reduction
        elif verb == "appeal_reduction":
            recovered = Decimal(str(payload["recovered"]))
            self.projection.finance.reduced -= recovered
            self.projection.finance.appealed += recovered
        elif verb == "apply_payment":
            cash = Decimal(str(payload["cash"]))
            ar = self.projection.finance.approved + self.projection.finance.appealed - cash
            self.projection.finance.cash += cash
            self.projection.finance.accounts_receivable = ar
        elif verb == "close_matter":
            if self.projection.finance.invariant_errors():
                raise GateError("finance invariants must reconcile before close")
            self.projection.closed = True
            self.projection.matter_status = "closed"
        return payload

    def canonical_event_hash(self) -> str:
        neutral_events = []
        for event in self.events:
            event_dict = asdict(event)
            event_dict.pop("run_id", None)
            event_dict.pop("event_id", None)
            event_dict.pop("random_stream_key", None)
            neutral_events.append(event_dict)
        return digest(neutral_events)

    def projection_hash(self) -> str:
        return digest(self.projection)

