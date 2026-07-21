from __future__ import annotations

from dataclasses import replace

import pytest

from law_firm_digital_twin.operational_mesh_contracts import (
    OPERATIONAL_MESH_REVISION,
    OperationalAuthorityLedger,
    OperationalWorkRequest,
    VerifiedOperationalRecord,
)
from law_firm_digital_twin.factory import build_employment_matter
from law_firm_digital_twin.kernel import WorldKernel
from law_firm_digital_twin.models import Route, SourceReceipt
from law_firm_digital_twin.operational_mesh_registry import (
    _validate_registry,
    build_operational_role_registry,
)
from law_firm_digital_twin.operational_mesh_router import _KernelOperationalRouter
import law_firm_digital_twin.operational_mesh_router as router_module
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack


def build_kernel(
    records: tuple[VerifiedOperationalRecord, ...] = (),
) -> WorldKernel:
    source_receipts = tuple(
        SourceReceipt(
            source_id=item.record_id,
            stable_source="public-test-source",
            authority="test-fixture",
            retrieval_date="2026-07-18",
            effective_date="2026-07-18",
            license_posture="public",
            intended_use="simulation routing test",
            prohibited_use="production legal use",
            source_hash=item.asset_digest,
            validator="test-fixture",
            status="admitted",
        )
        for item in records
        if item.record_kind == "source_admission"
        and item.source_class == "public"
        and item.approved
    )
    rule_pack = replace(
        placeholder_data_first_rule_pack(),
        source_receipts=source_receipts,
    )
    matter = build_employment_matter("operational-mesh-tests", rule_pack)
    return WorldKernel(
        run_id="RUN-OP-MESH",
        matter=matter,
        arm_label="ai_first",
        route=Route.TRIAL_APPEAL,
    )


BASE_KERNEL = build_kernel()


def request(capability: str, **changes: object) -> OperationalWorkRequest:
    base = OperationalWorkRequest(
        request_id="REQ-1",
        matter_commitment=BASE_KERNEL.operational_matter_commitment,
        capability_id=capability,
        requester_role_id="ops-practice-router",
    )
    return replace(base, **changes)


def record(
    record_id: str,
    kind: str,
    capability: str,
    *,
    matter: str = "sha256:matter",
    issuer: str = "human-authority-1",
    issuer_class: str = "named_human",
    source_class: str = "kernel_event",
    approved: bool = True,
) -> VerifiedOperationalRecord:
    return VerifiedOperationalRecord(
        record_id=record_id,
        record_kind=kind,
        issuer_id=issuer,
        issuer_class=issuer_class,  # type: ignore[arg-type]
        subject_matter_commitment=matter,
        scope_capability_ids=(capability,),
        valid_from_revision=OPERATIONAL_MESH_REVISION,
        valid_through_revision=OPERATIONAL_MESH_REVISION,
        asset_digest="sha256:" + "a" * 64,
        source_class=source_class,  # type: ignore[arg-type]
        approved=approved,
    )


def route_operational_work(
    work: OperationalWorkRequest,
    records: tuple[VerifiedOperationalRecord, ...] = (),
    *,
    matter_known: bool = True,
    requester_known: bool = True,
):
    kernel = build_kernel(records)
    routed_work = replace(
        work,
        matter_commitment=(
            kernel.operational_matter_commitment
            if matter_known
            else "sha256:" + "f" * 64
        ),
        requester_role_id=(
            work.requester_role_id if requester_known else "unknown-requester"
        ),
    )
    return kernel.route_operational_work(routed_work)


def test_registry_is_exhaustive_unique_provider_neutral_and_independently_checked() -> None:
    roles = build_operational_role_registry()
    role_ids = {role.role_id for role in roles}
    assert len(roles) >= 40
    assert all(role.provider_neutral and role.simulation_only for role in roles)
    assert all(not role.external_effects and not role.canonical_truth_write for role in roles)
    assert all(role.checker_role_id in role_ids and role.checker_role_id != role.role_id for role in roles)
    assert {role.domain for role in roles} >= {
        "intake-risk", "matter-operations", "finance-carrier", "finance-control",
        "information-evidence", "ediscovery", "technology-adapter",
    }


def test_routing_is_deterministic_and_unknown_work_fails_closed() -> None:
    known = request("ops.intake.triage")
    assert route_operational_work(known) == route_operational_work(known)
    assert route_operational_work(known).status == "routed"
    unknown = route_operational_work(request("ops.make_it_up"))
    assert unknown.status == "blocked"
    assert unknown.worker_role_id is None
    assert unknown.reason_codes == ("unknown_or_ambiguous_capability",)


def test_green_data_and_effect_boundaries_are_structural() -> None:
    for changes in (
        {"data_class": "client", "synthetic_only": False},
        {"effect_class": "external_write"},
        {"effect_class": "financial_posting"},
        {"effect_class": "legal_decision"},
        {"external_io": True},
    ):
        decision = route_operational_work(request("ops.intake.triage", **changes))
        assert decision.status == "blocked"
        assert decision.external_effects is False


def test_intake_cannot_clear_conflicts_or_open_a_matter() -> None:
    intake = route_operational_work(request("ops.intake.triage"))
    assert intake.worker_role_id == "ops-intake-triage"
    human_only = route_operational_work(request("legal.conflict.clear"))
    assert human_only.status == "blocked"
    opening = route_operational_work(request("ops.matter.opening.packet"))
    assert opening.status == "human_gate_required"
    assert set(opening.reason_codes) == {
        "missing_authority:carrier_authority",
        "missing_authority:conflicts_clearance",
        "missing_authority:responsible_lawyer_approval",
    }


def test_docketing_requires_admitted_rules_and_an_independent_reviewer() -> None:
    missing = route_operational_work(request("ops.docket.calculate"))
    assert missing.status == "blocked"
    assert "source_admission_receipt_missing" in missing.reason_codes
    routed = route_operational_work(
        request("ops.docket.calculate", source_admission_receipt_ids=("SAR-1",)),
        records=(
            record(
                "SAR-1",
                "source_admission",
                "ops.docket.calculate",
                source_class="public",
            ),
        ),
    )
    assert routed.status == "blocked"
    assert routed.reason_codes == (
        "source_admission_receipt_missing",
        "unverified_record:SAR-1",
    )
    assert routed.worker_role_id == "ops-docket-calculator"
    assert routed.checker_role_id == "ops-deadline-independent-reviewer"


def test_deposition_expert_and_filing_routes_require_distinct_authority() -> None:
    deposition = route_operational_work(request("ops.deposition.coordinate"))
    assert deposition.status == "human_gate_required"
    expert = route_operational_work(request("ops.expert_vendor.coordinate"))
    assert expert.status == "human_gate_required"
    assert set(expert.reason_codes) == {
        "missing_authority:carrier_budget_authority",
        "missing_authority:responsible_lawyer_approval",
    }
    filing = route_operational_work(request("ops.filing.assemble"))
    assert filing.status == "blocked"
    assert filing.reason_codes == ("missing_prerequisite:reconciled_deadline_receipt",)


def test_carrier_guidelines_require_source_and_reuse_receipts() -> None:
    public = route_operational_work(request("finance.carrier_guideline.compile_public"))
    assert public.status == "blocked"
    admitted = route_operational_work(
        request(
            "finance.carrier_guideline.compile_public",
            source_admission_receipt_ids=("SAR-OCG",),
        ),
        records=(
            record(
                "SAR-OCG",
                "source_admission",
                "finance.carrier_guideline.compile_public",
                source_class="public",
            ),
        ),
    )
    assert admitted.status == "blocked"
    assert admitted.reason_codes == (
        "source_admission_receipt_missing",
        "unverified_record:SAR-OCG",
    )
    reused = route_operational_work(
        request(
            "finance.carrier_guideline.compile_reused",
            source_admission_receipt_ids=("SAR-OCG",),
        ),
        records=(
            record(
                "SAR-OCG",
                "source_admission",
                "finance.carrier_guideline.compile_reused",
                source_class="public",
            ),
        ),
    )
    assert reused.status == "blocked"
    assert set(reused.reason_codes) == {
        "source_admission_receipt_missing",
        "reuse_release_receipt_missing",
        "unverified_record:SAR-OCG",
    }


def test_finance_segregates_time_prebill_invoice_cash_and_reconciliation() -> None:
    roles = {role.role_id: role for role in build_operational_role_registry()}
    ids = {
        "timekeeping-wip-analyst", "prebill-reviewer", "legal-invoice-compiler",
        "cash-application-analyst", "finance-reconciler", "finance-control-reviewer",
    }
    assert len(ids) == len({roles[item].separation_group for item in ids})
    cash = route_operational_work(
        request(
            "finance.cash_application.propose",
            prerequisite_receipt_ids=("REM-1", "AR-1"),
        ),
        records=(
            record(
                "REM-1",
                "prerequisite:synthetic_remittance_advice",
                "finance.cash_application.propose",
                issuer="kernel",
                issuer_class="kernel",
            ),
            record(
                "AR-1",
                "prerequisite:ar_snapshot",
                "finance.cash_application.propose",
                issuer="kernel",
                issuer_class="kernel",
            ),
        ),
    )
    assert cash.status == "blocked"
    assert "unverified_record:REM-1" in cash.reason_codes
    assert cash.checker_role_id == "finance-reconciler"
    reconcile = route_operational_work(
        request(
            "finance.reconcile",
            prerequisite_receipt_ids=("JOURNAL-1",),
        ),
        records=(
            record(
                "JOURNAL-1",
                "prerequisite:immutable_journal_snapshot",
                "finance.reconcile",
                issuer="kernel",
                issuer_class="kernel",
            ),
        ),
    )
    assert reconcile.status == "blocked"
    assert reconcile.checker_role_id == "finance-control-reviewer"


def test_trust_money_movement_writeoff_and_settlement_are_blocked() -> None:
    inactive = route_operational_work(request("finance.trust.classify"))
    assert inactive.status == "blocked"
    assert "capability_inactive" in inactive.reason_codes
    for capability in (
        "finance.trust.transact", "finance.money.move", "finance.writeoff.approve",
        "legal.settlement.authorize",
    ):
        decision = route_operational_work(request(capability))
        assert decision.status == "blocked"
        assert decision.reason_codes == ("human_only_effect",)


def test_imanage_is_only_a_qualified_adapter_not_the_dms_core() -> None:
    core = route_operational_work(request("information.dms.lifecycle"))
    assert core.status == "routed"
    assert core.worker_role_id == "dms-records-steward"
    missing = route_operational_work(
        request("information.imanage.translate", requested_adapter="imanage")
    )
    assert missing.status == "blocked"
    assert set(missing.reason_codes) == {
        "missing_prerequisite:adapter_qualification_receipt",
        "missing_prerequisite:cassette_replay_receipt",
    }
    routed = route_operational_work(
        request(
            "information.imanage.translate",
            requested_adapter="imanage",
            prerequisite_receipt_ids=("ADAPTER-1", "CASSETTE-1"),
        ),
        records=(
            record(
                "ADAPTER-1",
                "prerequisite:adapter_qualification_receipt",
                "information.imanage.translate",
                issuer="kernel",
                issuer_class="kernel",
            ),
            record(
                "CASSETTE-1",
                "prerequisite:cassette_replay_receipt",
                "information.imanage.translate",
                issuer="kernel",
                issuer_class="kernel",
            ),
        ),
    )
    assert routed.status == "blocked"
    assert "unverified_record:ADAPTER-1" in routed.reason_codes
    assert routed.worker_role_id == "imanage-runtime-adapter"


def test_ediscovery_privilege_production_hold_and_disposition_gates() -> None:
    privilege = route_operational_work(request("legal.privilege.determine"))
    assert privilege.status == "blocked"
    hold = route_operational_work(request("information.legal_hold.coordinate"))
    assert hold.status == "human_gate_required"
    production = route_operational_work(
        request(
            "information.production.prepare",
            prerequisite_receipt_ids=("PROD-SCOPE",),
        ),
        records=(
            record(
                "PROD-SCOPE",
                "prerequisite:production_scope_receipt",
                "information.production.prepare",
                issuer="kernel",
                issuer_class="kernel",
            ),
        ),
    )
    assert production.status == "blocked"
    assert "unverified_record:PROD-SCOPE" in production.reason_codes
    disposition = route_operational_work(request("information.retention.propose"))
    assert disposition.status == "blocked"
    assert disposition.reason_codes == ("missing_prerequisite:hold_clearance_receipt",)


def test_requester_cannot_be_the_assigned_checker() -> None:
    decision = route_operational_work(
        request("ops.intake.triage", requester_role_id="ops-quality-checker")
    )
    assert decision.status == "blocked"
    assert decision.reason_codes == ("requester_checker_collision",)


def test_invented_authority_and_receipt_ids_never_satisfy_a_gate() -> None:
    opening = route_operational_work(
        request(
            "ops.matter.opening.packet",
            authority_artifact_ids=("INVENTED-1", "INVENTED-2", "INVENTED-3"),
        )
    )
    assert opening.status == "blocked"
    assert any(code.startswith("unverified_record:") for code in opening.reason_codes)
    reused = route_operational_work(
        request(
            "finance.carrier_guideline.compile_reused",
            source_admission_receipt_ids=("INVENTED-SOURCE",),
            reuse_release_receipt_ids=("INVENTED-RELEASE",),
        )
    )
    assert reused.status == "blocked"
    assert "source_admission_receipt_missing" in reused.reason_codes
    assert "reuse_release_receipt_missing" in reused.reason_codes


def test_wrong_matter_scope_issuer_approval_or_revision_records_fail() -> None:
    capability = "ops.matter.opening.packet"
    valid = record(
        "AUTH-1",
        "authority:responsible_lawyer_approval",
        capability,
    )
    invalid_records = (
        replace(valid, subject_matter_commitment="sha256:other"),
        replace(valid, scope_capability_ids=("ops.intake.triage",)),
        replace(valid, issuer_id="synthetic-requester"),
        replace(valid, approved=False),
        replace(valid, valid_through_revision="expired-revision"),
    )
    for invalid in invalid_records:
        decision = route_operational_work(
            request(capability, authority_artifact_ids=(invalid.record_id,)),
            records=(invalid,),
        )
        assert decision.status == "blocked"
        assert decision.reason_codes == ("unverified_record:AUTH-1",)


def test_unknown_matter_and_requester_fail_before_routing() -> None:
    work = request("ops.intake.triage")
    assert route_operational_work(work, matter_known=False).reason_codes == (
        "unknown_matter_commitment",
    )
    assert route_operational_work(work, requester_known=False).reason_codes == (
        "unknown_requester_role",
    )


def test_registry_rejects_same_separation_group_checker_fixture() -> None:
    roles = build_operational_role_registry()
    worker = next(role for role in roles if role.role_id == "ops-intake-triage")
    checker = next(role for role in roles if role.role_id == worker.checker_role_id)
    forged = tuple(
        replace(role, separation_group=worker.separation_group)
        if role.role_id == checker.role_id
        else role
        for role in roles
    )
    with pytest.raises(ValueError, match="operational_checker_separation_collision"):
        _validate_registry(forged)


def test_privilege_triage_cannot_become_a_privilege_determination() -> None:
    decision = route_operational_work(
        request(
            "information.review_privilege.triage",
            effect_class="legal_decision",
        )
    )
    assert decision.status == "blocked"
    assert decision.reason_codes == ("effect_exceeds_proposal_scope",)


def test_adapter_receipts_bound_to_another_matter_are_invalid() -> None:
    capability = "information.imanage.translate"
    records = (
        record(
            "ADAPTER-X",
            "prerequisite:adapter_qualification_receipt",
            capability,
            matter="sha256:other",
            issuer="kernel",
            issuer_class="kernel",
        ),
        record(
            "CASSETTE-X",
            "prerequisite:cassette_replay_receipt",
            capability,
            matter="sha256:other",
            issuer="kernel",
            issuer_class="kernel",
        ),
    )
    decision = route_operational_work(
        request(
            capability,
            requested_adapter="imanage",
            prerequisite_receipt_ids=("ADAPTER-X", "CASSETTE-X"),
        ),
        records=records,
    )
    assert decision.status == "blocked"
    assert set(decision.reason_codes) == {
        "unverified_record:ADAPTER-X",
        "unverified_record:CASSETTE-X",
        "missing_prerequisite:adapter_qualification_receipt",
        "missing_prerequisite:cassette_replay_receipt",
    }


def test_syntactically_valid_attacker_ledger_cannot_construct_kernel_router() -> None:
    assert not hasattr(router_module, "_KERNEL_ROUTER_TOKEN")
    forged = OperationalAuthorityLedger(
        ledger_id="FORGED",
        issuer_id="kernel.operational_authority_registry.v1",
        known_matter_commitments=(BASE_KERNEL.operational_matter_commitment,),
        known_requester_role_ids=("ops-practice-router",),
        records=(
            record(
                "FORGED-AUTH",
                "authority:conflicts_clearance",
                "ops.matter.opening.packet",
            ),
        ),
    )
    with pytest.raises(ValueError, match="kernel_operational_router_construction_forbidden"):
        _KernelOperationalRouter(object(), lambda: forged)
