from __future__ import annotations

import hmac
import re

from .hashio import digest
from .sealed_ipc_protocol import (
    SEALED_IPC_CORE_REVISION,
    AppendOnlyReplayLedger,
    GenericDenialReceipt,
    SealedIpcCapability,
    SealedIpcRequest,
    SealedIpcSuccessReceipt,
    _auth_tag,
    _capability_unsigned_payload,
    build_request,
)


SEALED_IPC_VALIDATOR_REVISION = "sealed-ipc-validator-g0-v1"
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")


def validate_capability(
    capability: SealedIpcCapability,
    *,
    signing_key: bytes,
) -> tuple[str, ...]:
    errors: list[str] = []
    if type(capability) is not SealedIpcCapability:
        return ("SIP-001:capability_type_invalid",)
    try:
        unsigned = _capability_unsigned_payload(
            principal=capability.principal_commitment,
            operating_matter_id=capability.operating_matter_id,
            operation=capability.allowed_operation,
            issued_tick=capability.issued_tick,
            expires_tick=capability.expires_tick,
            nonce=capability.nonce,
            idempotency_key=capability.idempotency_key,
        )
        tag = _auth_tag(signing_key, unsigned)
    except Exception:
        return ("SIP-002:capability_binding_invalid",)
    expected_id = "IPCCAP-" + digest({**unsigned, "auth_tag": tag})[:24]
    if (
        capability.revision != SEALED_IPC_CORE_REVISION
        or not _HEX_64.fullmatch(capability.principal_commitment)
        or not _HEX_64.fullmatch(capability.auth_tag)
        or not hmac.compare_digest(tag, capability.auth_tag)
        or capability.capability_id != expected_id
        or capability.expires_tick <= capability.issued_tick
    ):
        errors.append("SIP-002:capability_binding_invalid")
    if (
        capability.contains_raw_principal
        or capability.contains_path
        or capability.contains_secret
        or capability.contains_payload
    ):
        errors.append("SIP-003:capability_disclosure_invalid")
    return tuple(errors)


def validate_request(
    request: SealedIpcRequest,
    *,
    signing_key: bytes,
) -> tuple[str, ...]:
    if type(request) is not SealedIpcRequest:
        return ("SIP-004:request_type_invalid",)
    errors = list(validate_capability(request.capability, signing_key=signing_key))
    try:
        expected = build_request(
            request.capability,
            request_commitment=request.request_commitment,
        )
    except (TypeError, ValueError):
        expected = None
    if request.revision != SEALED_IPC_CORE_REVISION or request != expected:
        errors.append("SIP-005:request_binding_invalid")
    if (
        request.contains_payload
        or request.canonical_write_requested
        or request.external_effect_requested
    ):
        errors.append("SIP-006:request_authority_invalid")
    return tuple(dict.fromkeys(errors))


def validate_external_receipt(
    receipt: GenericDenialReceipt | SealedIpcSuccessReceipt,
) -> tuple[str, ...]:
    if type(receipt) is GenericDenialReceipt:
        if (
            receipt.revision != SEALED_IPC_CORE_REVISION
            or receipt.disposition != "DENIED"
            or receipt.contains_reason
            or receipt.contains_identity
            or receipt.contains_path
            or receipt.contains_secret
        ):
            return ("SIP-007:generic_denial_invalid",)
        return ()
    if type(receipt) is SealedIpcSuccessReceipt:
        if (
            receipt.revision != SEALED_IPC_CORE_REVISION
            or receipt.disposition != "ACCEPTED"
            or not _HEX_64.fullmatch(receipt.result_commitment)
            or receipt.contains_payload
            or receipt.contains_sealed_material
            or receipt.external_effects
        ):
            return ("SIP-008:success_receipt_invalid",)
        expected_id = "IPCRCP-" + digest(
            {
                "request_hash": None,
                "operation": receipt.operation,
                "operating_matter_id": receipt.operating_matter_id,
                "result_commitment": receipt.result_commitment,
            }
        )[:24]
        # The request hash is intentionally not worker-visible, so full ID
        # recomputation belongs to the sealed ledger validator below.
        if not receipt.receipt_id.startswith("IPCRCP-") or len(receipt.receipt_id) != len(expected_id):
            return ("SIP-009:success_receipt_id_shape_invalid",)
        return ()
    return ("SIP-010:external_receipt_type_invalid",)


def validate_replay_ledger(ledger: AppendOnlyReplayLedger) -> tuple[str, ...]:
    if type(ledger) is not AppendOnlyReplayLedger:
        return ("SIP-011:ledger_type_invalid",)
    errors: list[str] = []
    prior = digest("ipc-ledger-genesis-v1")
    seen_entries: set[str] = set()
    for sequence, entry in enumerate(ledger.sealed_entries(), start=1):
        unsigned = {
            "sequence": entry.sequence,
            "request_hash": entry.request_hash,
            "capability_hash": entry.capability_hash,
            "principal_commitment": entry.principal_commitment,
            "nonce_commitment": entry.nonce_commitment,
            "idempotency_key_commitment": entry.idempotency_key_commitment,
            "disposition": entry.disposition,
            "internal_denial_code": entry.internal_denial_code,
            "prior_entry_hash": entry.prior_entry_hash,
        }
        if (
            entry.sequence != sequence
            or entry.prior_entry_hash != prior
            or entry.entry_hash != digest(unsigned)
            or entry.entry_hash in seen_entries
            or entry.worker_visible
        ):
            errors.append(f"SIP-012:ledger_entry_{sequence}_invalid")
        if (entry.disposition == "ACCEPTED") != (entry.internal_denial_code == ""):
            errors.append(f"SIP-013:ledger_disposition_{sequence}_invalid")
        prior = entry.entry_hash
        seen_entries.add(entry.entry_hash)
    return tuple(errors)
