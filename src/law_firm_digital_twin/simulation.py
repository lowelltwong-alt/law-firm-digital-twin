from __future__ import annotations

from dataclasses import asdict

from .factory import build_employment_matter
from .hashio import digest
from .kernel import GateError, WorldKernel
from .models import Arm, Command, Route
from .rules import placeholder_data_first_rule_pack


def _cmd(index: int, verb: str, matter_id: str, payload: dict[str, object], authority: tuple[str, ...] = (), knowledge: tuple[str, ...] = ()) -> Command:
    return Command(
        command_id=f"CMD-{index:03d}-{verb}",
        verb=verb,
        actor_id="party_interface_actor",
        role_id="firm_player",
        matter_id=matter_id,
        payload=payload,
        requires_authority=authority,
        requires_knowledge=knowledge,
    )


def run_walking_skeleton(seed: str, arm: Arm, route: Route) -> dict[str, object]:
    rule_pack = placeholder_data_first_rule_pack()
    matter = build_employment_matter(seed, rule_pack)
    kernel = WorldKernel(run_id=f"RUN-{arm.value}-{route.value}-{seed}", matter=matter, arm_label=arm.value, route=route)

    commands = [
        _cmd(1, "receive_referral", matter.matter_id, {"referral_id": matter.referral_id}),
        _cmd(2, "submit_conflict_result", matter.matter_id, {"conflict": "prior affiliate contact requires affected-client consent"}, ("conflict_search",), ("party_names",)),
        _cmd(3, "record_lawyer_gate", matter.matter_id, {"gate": "affected_client_consent", "grants": "matter_opening"}, ("lawyer_conflict_determination",), ("party_names",)),
        _cmd(4, "open_matter", matter.matter_id, {"coverage": "reservation_of_rights", "guidelines": "synthetic_ocg_v0"}, ("matter_opening",), ("referral_summary",)),
        _cmd(5, "verify_deadlines", matter.matter_id, {"complaint_filed_day": 0}, ("deadline_proposal",), ("initial_record",)),
        _cmd(6, "produce_discovery", matter.matter_id, {"set": "small_inconsistent_evidence"}, ("legal_work",), ("initial_record",)),
        _cmd(7, "take_deposition", matter.matter_id, {"witness": "synthetic_hr_witness"}, ("legal_work",), ("produced_evidence",)),
        _cmd(8, "retain_expert", matter.matter_id, {"expert": "synthetic_hr_practices_expert"}, ("legal_work",), ("deposition_transcript",)),
        _cmd(9, "resolve_route", matter.matter_id, {"route": route.value}, ("legal_work",), ("expert_opinion",)),
        _cmd(10, "record_time", matter.matter_id, {"amount": "1000.00"}, ("billing",), ("initial_record",)),
        _cmd(11, "submit_invoice", matter.matter_id, {}, ("billing",), ("initial_record",)),
        _cmd(12, "carrier_audit", matter.matter_id, {"reduction": "100.00"}, ("billing",), ("guidelines",)),
        _cmd(13, "appeal_reduction", matter.matter_id, {"recovered": "25.00"}, ("billing",), ("guidelines",)),
        _cmd(14, "apply_payment", matter.matter_id, {"cash": "925.00"}, ("billing",), ("guidelines",)),
        _cmd(15, "close_matter", matter.matter_id, {"retention": "scheduled", "final_report": "delivered"}, ("billing",), ("guidelines",)),
    ]
    for command in commands:
        kernel.submit(command)

    oracle_blocked = False
    try:
        kernel.submit(_cmd(99, "read_oracle", matter.matter_id, {}, ("legal_work",), ("initial_record",)))
    except GateError:
        oracle_blocked = True

    finance_errors = kernel.projection.finance.invariant_errors()
    return {
        "seed": seed,
        "arm": arm.value,
        "route": route.value,
        "matter": asdict(matter),
        "event_count": len(kernel.events),
        "event_hash": kernel.canonical_event_hash(),
        "projection_hash": kernel.projection_hash(),
        "closed": kernel.projection.closed,
        "deadlines": dict(kernel.projection.deadlines),
        "finance_errors": finance_errors,
        "oracle_blocked": oracle_blocked,
        "human_gate_bypasses": kernel.projection.human_gate_bypasses,
        "synthetic_non_predictive": True,
    }


def run_all_routes(seed: str = "alpha") -> dict[str, object]:
    runs = [
        run_walking_skeleton(seed, arm, route)
        for arm in (Arm.TRADITIONAL, Arm.AI_FIRST)
        for route in Route
    ]
    return {
        "simulator": "Law Firm Digital Twin",
        "scope": "G0-G2 walking skeleton",
        "runs": runs,
        "bundle_hash": digest(runs),
    }


# G2 implementation entry points. The original compact skeleton remains above as
# a readable migration record; all public callers are bound to the structurally
# gated world-first engine below.
from .g2 import run_all_routes as _run_all_routes_g2
from .g2 import run_walking_skeleton as _run_walking_skeleton_g2

run_walking_skeleton = _run_walking_skeleton_g2
run_all_routes = _run_all_routes_g2
