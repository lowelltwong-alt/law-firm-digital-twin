from __future__ import annotations

from .hashio import digest
from .operational_mesh_contracts import OperationalRole


COMMON_INPUTS = ("operational_work_request", "matter_commitment")
PROPOSAL_OUTPUT = ("operational_handoff_proposal", "immutable_routing_receipt")


def _role(
    role_id: str,
    domain: str,
    capabilities: tuple[str, ...],
    checker: str,
    separation_group: str,
    *,
    authority: tuple[str, ...] = (),
    prerequisites: tuple[str, ...] = (),
    gates: tuple[str, ...] = (),
    source: bool = False,
    release: bool = False,
    adapter: str | None = None,
    active: bool = True,
    outputs: tuple[str, ...] = PROPOSAL_OUTPUT,
) -> OperationalRole:
    return OperationalRole(
        role_id=role_id,
        domain=domain,
        capability_ids=capabilities,
        input_contract_ids=COMMON_INPUTS,
        output_contract_ids=outputs,
        checker_role_id=checker,
        separation_group=separation_group,
        required_authority_kinds=authority,
        required_prerequisite_kinds=prerequisites,
        human_gate_ids=gates,
        requires_source_admission=source,
        requires_reuse_release=release,
        adapter_kind=adapter,
        active=active,
    )


def build_operational_role_registry() -> tuple[OperationalRole, ...]:
    roles = (
        _role("ops-practice-router", "control", ("ops.route.audit",), "ops-quality-checker", "routing"),
        _role("ops-intake-triage", "intake-risk", ("ops.intake.triage",), "ops-quality-checker", "intake"),
        _role("ops-conflicts-screen", "intake-risk", ("ops.conflicts.screen",), "conflicts-independent-checker", "conflicts"),
        _role("conflicts-independent-checker", "control", ("ops.conflicts.audit",), "ops-quality-checker", "conflicts-review"),
        _role(
            "ops-matter-opening-control", "intake-risk", ("ops.matter.opening.packet",), "ops-quality-checker", "matter-opening",
            authority=("responsible_lawyer_approval", "conflicts_clearance", "carrier_authority"),
            gates=("human.responsible_lawyer", "human.conflicts_authority", "human.carrier_authority"),
        ),
        _role("ops-docket-calculator", "matter-operations", ("ops.docket.calculate",), "ops-deadline-independent-reviewer", "docketing", source=True),
        _role("ops-deadline-independent-reviewer", "control", ("ops.deadline.independent_review",), "ops-quality-checker", "deadline-review", source=True),
        _role("ops-legal-assistant-coordinator", "matter-operations", ("ops.legal_assistant.coordinate",), "ops-quality-checker", "assistant"),
        _role("ops-litigation-paralegal", "matter-operations", ("ops.paralegal.support",), "information-governance-checker", "paralegal"),
        _role(
            "ops-deposition-coordinator", "matter-operations", ("ops.deposition.coordinate",), "ops-quality-checker", "deposition",
            authority=("responsible_lawyer_approval", "activated_kernel_branch"), gates=("human.responsible_lawyer",),
        ),
        _role("ops-witness-logistics", "matter-operations", ("ops.witness.logistics",), "ops-quality-checker", "witness-logistics", authority=("responsible_lawyer_approval",)),
        _role(
            "ops-expert-vendor-coordinator", "matter-operations", ("ops.expert_vendor.coordinate",), "finance-control-reviewer", "expert-vendor",
            authority=("responsible_lawyer_approval", "carrier_budget_authority"), gates=("human.responsible_lawyer", "human.carrier_budget"),
        ),
        _role(
            "ops-filing-assembler", "matter-operations", ("ops.filing.assemble",), "ops-quality-checker", "filing-assembly",
            authority=("responsible_lawyer_approval",), prerequisites=("reconciled_deadline_receipt",), gates=("human.responsible_lawyer",),
            outputs=("simulated_filing_intent_only", "immutable_routing_receipt"),
        ),
        _role("ops-quality-checker", "control", ("ops.quality.audit",), "legal-authority-boundary-checker", "operations-quality"),
        _role("legal-authority-boundary-checker", "control", ("ops.authority.audit",), "ops-practice-router", "legal-authority"),
        _role("carrier-guideline-steward-public", "finance-carrier", ("finance.carrier_guideline.compile_public",), "finance-control-reviewer", "guideline", source=True),
        _role("carrier-guideline-steward-reuse", "finance-carrier", ("finance.carrier_guideline.compile_reused",), "finance-control-reviewer", "guideline-reuse", source=True, release=True),
        _role("timekeeping-wip-analyst", "finance-carrier", ("finance.time_wip.propose",), "prebill-reviewer", "time-wip"),
        _role("prebill-reviewer", "finance-carrier", ("finance.prebill.review",), "finance-control-reviewer", "prebill", prerequisites=("time_entry_proposal", "guideline_profile")),
        _role("legal-invoice-compiler", "finance-carrier", ("finance.invoice.compile",), "finance-reconciler", "invoice", prerequisites=("approved_prebill_receipt", "ledes_utbms_mapping_receipt")),
        _role("carrier-audit-interpreter", "finance-carrier", ("finance.carrier_audit.interpret",), "finance-control-reviewer", "carrier-audit", prerequisites=("synthetic_invoice_receipt", "guideline_profile")),
        _role("billing-appeal-preparer", "finance-carrier", ("finance.appeal.prepare",), "finance-control-reviewer", "appeal", prerequisites=("reduction_assessment",)),
        _role("revenue-ar-analyst", "finance-carrier", ("finance.revenue_ar.project",), "finance-reconciler", "revenue-ar"),
        _role("cash-application-analyst", "finance-carrier", ("finance.cash_application.propose",), "finance-reconciler", "cash-application", prerequisites=("synthetic_remittance_advice", "ar_snapshot")),
        _role("collections-coordinator", "finance-carrier", ("finance.collections.coordinate",), "finance-control-reviewer", "collections", prerequisites=("ar_aging_snapshot",)),
        _role("finance-reconciler", "finance-control", ("finance.reconcile",), "finance-control-reviewer", "finance-reconciliation", prerequisites=("immutable_journal_snapshot",)),
        _role("finance-control-reviewer", "finance-control", ("finance.control.audit",), "legal-authority-boundary-checker", "finance-control"),
        _role("trust-boundary-controller", "finance-control", ("finance.trust.classify",), "finance-control-reviewer", "trust-boundary", active=False),
        _role("dms-records-steward", "information-evidence", ("information.dms.lifecycle",), "information-governance-checker", "dms"),
        _role(
            "imanage-runtime-adapter", "technology-adapter", ("information.imanage.translate",), "adapter-contract-checker", "dms-adapter",
            prerequisites=("adapter_qualification_receipt", "cassette_replay_receipt"), adapter="imanage",
        ),
        _role("km-curator", "information-evidence", ("information.km.curate",), "km-provenance-checker", "knowledge-management", source=True),
        _role(
            "legal-hold-coordinator", "ediscovery", ("information.legal_hold.coordinate",), "information-governance-checker", "legal-hold",
            authority=("responsible_lawyer_approval",), gates=("human.responsible_lawyer",),
        ),
        _role("esi-collection-custody-coordinator", "ediscovery", ("information.esi.collect",), "custody-provenance-checker", "esi-collection", authority=("approved_collection_scope",)),
        _role("esi-processing-specialist", "ediscovery", ("information.esi.process",), "custody-provenance-checker", "esi-processing", prerequisites=("collection_custody_receipt",)),
        _role("review-privilege-triage-specialist", "ediscovery", ("information.review_privilege.triage",), "privilege-boundary-checker", "review-triage"),
        _role(
            "production-litigation-support-coordinator", "ediscovery", ("information.production.prepare",), "production-lineage-checker", "production",
            authority=("responsible_lawyer_approval",), gates=("human.responsible_lawyer",), prerequisites=("production_scope_receipt",),
        ),
        _role(
            "retention-disposition-steward", "information-evidence", ("information.retention.propose",), "information-governance-checker", "retention",
            authority=("records_authority_approval",), prerequisites=("hold_clearance_receipt",), gates=("human.records_authority",),
        ),
        _role("legal-tech-integration-operator", "technology-adapter", ("technology.integration.plan",), "adapter-contract-checker", "legal-tech"),
        _role("information-governance-checker", "information-control", ("information.governance.audit",), "legal-authority-boundary-checker", "information-governance"),
        _role("custody-provenance-checker", "information-control", ("information.custody.audit",), "information-governance-checker", "custody-check"),
        _role("privilege-boundary-checker", "information-control", ("information.privilege_boundary.audit",), "legal-authority-boundary-checker", "privilege-check"),
        _role("production-lineage-checker", "information-control", ("information.production.audit",), "information-governance-checker", "production-check"),
        _role("adapter-contract-checker", "technology-control", ("technology.adapter.audit",), "information-governance-checker", "adapter-check"),
        _role("km-provenance-checker", "information-control", ("information.km_provenance.audit",), "information-governance-checker", "km-check"),
    )
    _validate_registry(roles)
    return roles


def _validate_registry(roles: tuple[OperationalRole, ...]) -> None:
    role_ids = [role.role_id for role in roles]
    if len(role_ids) != len(set(role_ids)):
        raise ValueError("duplicate_operational_role_id")
    capabilities = [capability for role in roles for capability in role.capability_ids]
    if len(capabilities) != len(set(capabilities)):
        raise ValueError("duplicate_operational_capability_id")
    known = set(role_ids)
    by_id = {role.role_id: role for role in roles}
    for role in roles:
        if role.checker_role_id not in known:
            raise ValueError(f"unknown_operational_checker:{role.role_id}")
        if role.checker_role_id == role.role_id:
            raise ValueError(f"operational_self_check:{role.role_id}")
        if by_id[role.checker_role_id].separation_group == role.separation_group:
            raise ValueError(f"operational_checker_separation_collision:{role.role_id}")


def operational_registry_commitment(roles: tuple[OperationalRole, ...] | None = None) -> str:
    selected = roles if roles is not None else build_operational_role_registry()
    return digest(tuple(role.role_hash for role in selected))
