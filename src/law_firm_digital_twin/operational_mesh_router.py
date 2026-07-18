from __future__ import annotations

from collections.abc import Callable

from .operational_mesh_contracts import (
    OPERATIONAL_MESH_REVISION,
    OperationalAuthorityLedger,
    OperationalRoutingDecision,
    OperationalRole,
    OperationalWorkRequest,
    VerifiedOperationalRecord,
)
from .operational_mesh_registry import (
    build_operational_role_registry,
    operational_registry_commitment,
)


ALLOWED_EFFECTS = {"advisory_only", "simulation_planning_only"}
ALLOWED_DATA_CLASSES = {"synthetic", "public"}
HUMAN_ONLY_CAPABILITIES = {
    "legal.conflict.clear",
    "legal.conflict.waive",
    "legal.privilege.determine",
    "legal.filing.sign",
    "legal.filing.submit",
    "legal.settlement.authorize",
    "legal.strategy.decide",
    "finance.money.move",
    "finance.writeoff.approve",
    "finance.trust.transact",
    "information.hold.release",
    "information.production.transmit",
    "information.disposition.execute",
}


def _route_with_authority_ledger(
    request: OperationalWorkRequest,
    authority_ledger: OperationalAuthorityLedger,
    roles: tuple[OperationalRole, ...] | None = None,
) -> OperationalRoutingDecision:
    registry = roles if roles is not None else build_operational_role_registry()
    commitment = operational_registry_commitment(registry)
    reasons: list[str] = []
    worker: OperationalRole | None = None
    records_by_id = {record.record_id: record for record in authority_ledger.records}
    if len(records_by_id) != len(authority_ledger.records):
        reasons.append("authority_ledger_duplicate_record")
    if authority_ledger.issuer_id != "kernel.operational_authority_registry.v1":
        reasons.append("authority_ledger_issuer_invalid")
    if request.matter_commitment not in authority_ledger.known_matter_commitments:
        reasons.append("unknown_matter_commitment")
    if request.requester_role_id not in authority_ledger.known_requester_role_ids:
        reasons.append("unknown_requester_role")

    matches = [role for role in registry if request.capability_id in role.capability_ids]
    if request.capability_id in HUMAN_ONLY_CAPABILITIES:
        reasons.append("human_only_effect")
    elif len(matches) != 1:
        reasons.append("unknown_or_ambiguous_capability")
    else:
        worker = matches[0]

    if request.data_class not in ALLOWED_DATA_CLASSES or not request.synthetic_only:
        reasons.append("non_green_data_blocked")
    if request.effect_class not in ALLOWED_EFFECTS:
        reasons.append("effect_exceeds_proposal_scope")
    if request.external_io:
        reasons.append("external_io_blocked")
    missing_authority: tuple[str, ...] = ()
    if worker is not None:
        if not worker.active:
            reasons.append("capability_inactive")
        if request.requester_role_id == worker.checker_role_id:
            reasons.append("requester_checker_collision")
        resolved_source = _resolve_records(
            request.source_admission_receipt_ids,
            "source_admission",
            request,
            worker,
            authority_ledger,
            records_by_id,
            reasons,
        )
        resolved_reuse = _resolve_records(
            request.reuse_release_receipt_ids,
            "reuse_release",
            request,
            worker,
            authority_ledger,
            records_by_id,
            reasons,
        )
        resolved_authority = _resolve_records(
            request.authority_artifact_ids,
            "authority:",
            request,
            worker,
            authority_ledger,
            records_by_id,
            reasons,
            prefix=True,
        )
        resolved_prerequisites = _resolve_records(
            request.prerequisite_receipt_ids,
            "prerequisite:",
            request,
            worker,
            authority_ledger,
            records_by_id,
            reasons,
            prefix=True,
        )
        if worker.requires_source_admission and not resolved_source:
            reasons.append("source_admission_receipt_missing")
        if worker.requires_reuse_release and not resolved_reuse:
            reasons.append("reuse_release_receipt_missing")
        authority_kinds = {
            record.record_kind.removeprefix("authority:") for record in resolved_authority
        }
        prerequisite_kinds = {
            record.record_kind.removeprefix("prerequisite:")
            for record in resolved_prerequisites
        }
        missing_authority = tuple(
            sorted(set(worker.required_authority_kinds) - authority_kinds)
        )
        missing_prerequisites = tuple(
            sorted(set(worker.required_prerequisite_kinds) - prerequisite_kinds)
        )
        if missing_prerequisites:
            reasons.extend(f"missing_prerequisite:{item}" for item in missing_prerequisites)
        if worker.adapter_kind is not None:
            if request.requested_adapter != worker.adapter_kind:
                reasons.append("adapter_mismatch_or_missing")
        elif request.requested_adapter is not None:
            reasons.append("adapter_not_permitted_for_capability")

    hard_reasons = tuple(sorted(set(reasons)))
    if hard_reasons:
        status = "blocked"
    elif missing_authority:
        status = "human_gate_required"
        hard_reasons = tuple(f"missing_authority:{item}" for item in missing_authority)
    else:
        status = "routed"

    return OperationalRoutingDecision(
        request_id=request.request_id,
        request_hash=request.request_hash,
        status=status,
        worker_role_id=worker.role_id if worker is not None else None,
        checker_role_id=worker.checker_role_id if worker is not None else None,
        reason_codes=hard_reasons,
        required_human_gates=worker.human_gate_ids if worker is not None else (),
        registry_commitment=commitment,
        authority_ledger_commitment=authority_ledger.ledger_hash,
        mesh_revision=OPERATIONAL_MESH_REVISION,
    )


def _define_kernel_router() -> tuple[type, Callable[[Callable[[], OperationalAuthorityLedger]], object]]:
    construction_token = object()

    class KernelOperationalRouter:
        def __init__(
            self,
            token: object,
            ledger_provider: Callable[[], OperationalAuthorityLedger],
        ):
            if token is not construction_token:
                raise ValueError("kernel_operational_router_construction_forbidden")
            self.__ledger_provider = ledger_provider

        def route(self, request: OperationalWorkRequest) -> OperationalRoutingDecision:
            return _route_with_authority_ledger(request, self.__ledger_provider())

    def build(
        ledger_provider: Callable[[], OperationalAuthorityLedger],
    ) -> KernelOperationalRouter:
        return KernelOperationalRouter(construction_token, ledger_provider)

    return KernelOperationalRouter, build


_KernelOperationalRouter, _build_kernel_operational_router = _define_kernel_router()


def _resolve_records(
    record_ids: tuple[str, ...],
    expected_kind: str,
    request: OperationalWorkRequest,
    worker: OperationalRole,
    ledger: OperationalAuthorityLedger,
    records_by_id: dict[str, VerifiedOperationalRecord],
    reasons: list[str],
    *,
    prefix: bool = False,
) -> tuple[VerifiedOperationalRecord, ...]:
    resolved: list[VerifiedOperationalRecord] = []
    for record_id in record_ids:
        record = records_by_id.get(record_id)
        if record is None:
            reasons.append(f"unverified_record:{record_id}")
            continue
        kind_matches = (
            record.record_kind.startswith(expected_kind)
            if prefix
            else record.record_kind == expected_kind
        )
        subject_matches = (
            record.subject_matter_commitment == request.matter_commitment
            or (
                expected_kind in {"source_admission", "reuse_release"}
                and record.subject_matter_commitment == "global"
            )
        )
        scope_matches = (
            request.capability_id in record.scope_capability_ids
            or "*" in record.scope_capability_ids
        )
        revision_matches = (
            record.valid_from_revision == OPERATIONAL_MESH_REVISION
            and record.valid_through_revision == OPERATIONAL_MESH_REVISION
        )
        digest_valid = (
            record.asset_digest.startswith("sha256:")
            and len(record.asset_digest) == len("sha256:") + 64
        )
        issuer_separate = record.issuer_id not in {
            request.requester_role_id,
            worker.role_id,
            worker.checker_role_id,
        }
        class_valid = True
        if expected_kind == "source_admission":
            class_valid = record.source_class in {"synthetic", "public"}
        elif expected_kind == "reuse_release":
            class_valid = (
                record.source_class == "released_local_asset"
                and record.issuer_class == "named_human"
            )
        elif expected_kind == "authority:":
            class_valid = record.issuer_class == "named_human"
        if not all(
            (
                kind_matches,
                subject_matches,
                scope_matches,
                revision_matches,
                digest_valid,
                issuer_separate,
                record.approved,
                class_valid,
                record.record_id in records_by_id,
                ledger.issuer_id == "kernel.operational_authority_registry.v1",
            )
        ):
            reasons.append(f"invalid_record:{record_id}")
            continue
        resolved.append(record)
    return tuple(resolved)
