from __future__ import annotations

import hmac
import json
import re
import struct
from dataclasses import dataclass, replace
from hashlib import sha256
from threading import RLock
from typing import Literal

from .hashio import canonical_json, digest


SEALED_IPC_CORE_REVISION = "sealed-ipc-core-g0-v1"
MAX_FRAME_BYTES = 65_536

IpcOperation = Literal[
    "SubmitIngressCommitment",
    "RequestOperatingProjection",
    "AcknowledgeOutboxItem",
]
InternalDenialCode = Literal[
    "EXPIRED",
    "REPLAYED",
    "INVALID_REQUEST",
    "IDENTITY_MISMATCH",
    "AUTHORITY_MISMATCH",
]

_OPERATIONS = {
    "SubmitIngressCommitment",
    "RequestOperatingProjection",
    "AcknowledgeOutboxItem",
}
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


@dataclass(frozen=True)
class SealedIpcCapability:
    capability_id: str
    revision: Literal["sealed-ipc-core-g0-v1"]
    principal_commitment: str
    operating_matter_id: str
    allowed_operation: IpcOperation
    issued_tick: int
    expires_tick: int
    nonce: str
    idempotency_key: str
    auth_tag: str
    contains_raw_principal: Literal[False]
    contains_path: Literal[False]
    contains_secret: Literal[False]
    contains_payload: Literal[False]

    @property
    def capability_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class SealedIpcRequest:
    request_id: str
    revision: Literal["sealed-ipc-core-g0-v1"]
    capability: SealedIpcCapability
    operation: IpcOperation
    operating_matter_id: str
    request_commitment: str
    nonce: str
    idempotency_key: str
    contains_payload: Literal[False]
    canonical_write_requested: Literal[False]
    external_effect_requested: Literal[False]

    @property
    def request_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class GenericDenialReceipt:
    request_id: str
    revision: Literal["sealed-ipc-core-g0-v1"]
    disposition: Literal["DENIED"]
    contains_reason: Literal[False]
    contains_identity: Literal[False]
    contains_path: Literal[False]
    contains_secret: Literal[False]


@dataclass(frozen=True)
class SealedIpcSuccessReceipt:
    receipt_id: str
    revision: Literal["sealed-ipc-core-g0-v1"]
    request_id: str
    operation: IpcOperation
    operating_matter_id: str
    result_commitment: str
    disposition: Literal["ACCEPTED"]
    duplicate: bool
    contains_payload: Literal[False]
    contains_sealed_material: Literal[False]
    external_effects: Literal[False]


@dataclass(frozen=True)
class SealedReplayEntry:
    sequence: int
    request_hash: str
    capability_hash: str
    principal_commitment: str
    nonce_commitment: str
    idempotency_key_commitment: str
    disposition: Literal["ACCEPTED", "DENIED"]
    internal_denial_code: InternalDenialCode | Literal[""]
    prior_entry_hash: str
    entry_hash: str
    worker_visible: Literal[False]


def principal_commitment(raw_sid: str) -> str:
    if not raw_sid or len(raw_sid) > 256:
        raise ValueError("ipc_principal_sid_invalid")
    return digest({"kind": "windows_sid", "value": raw_sid})


def _capability_unsigned_payload(
    *,
    principal: str,
    operating_matter_id: str,
    operation: IpcOperation,
    issued_tick: int,
    expires_tick: int,
    nonce: str,
    idempotency_key: str,
) -> dict[str, object]:
    return {
        "revision": SEALED_IPC_CORE_REVISION,
        "principal_commitment": principal,
        "operating_matter_id": operating_matter_id,
        "allowed_operation": operation,
        "issued_tick": issued_tick,
        "expires_tick": expires_tick,
        "nonce": nonce,
        "idempotency_key": idempotency_key,
    }


def _auth_tag(signing_key: bytes, payload: dict[str, object]) -> str:
    return hmac.new(
        signing_key,
        canonical_json(payload).encode("utf-8"),
        sha256,
    ).hexdigest()


def issue_capability(
    *,
    signing_key: bytes,
    principal: str,
    operating_matter_id: str,
    operation: IpcOperation,
    issued_tick: int,
    expires_tick: int,
    nonce: str,
    idempotency_key: str,
) -> SealedIpcCapability:
    if type(signing_key) is not bytes or len(signing_key) < 32:
        raise ValueError("ipc_signing_key_invalid")
    if not _HEX_64.fullmatch(principal):
        raise ValueError("ipc_principal_commitment_invalid")
    if operation not in _OPERATIONS:
        raise ValueError("ipc_operation_invalid")
    if not _SAFE_ID.fullmatch(operating_matter_id):
        raise ValueError("ipc_operating_matter_id_invalid")
    if issued_tick < 0 or expires_tick <= issued_tick:
        raise ValueError("ipc_capability_interval_invalid")
    if not _SAFE_ID.fullmatch(nonce) or not _SAFE_ID.fullmatch(idempotency_key):
        raise ValueError("ipc_replay_binding_invalid")
    unsigned = _capability_unsigned_payload(
        principal=principal,
        operating_matter_id=operating_matter_id,
        operation=operation,
        issued_tick=issued_tick,
        expires_tick=expires_tick,
        nonce=nonce,
        idempotency_key=idempotency_key,
    )
    tag = _auth_tag(signing_key, unsigned)
    return SealedIpcCapability(
        capability_id="IPCCAP-" + digest({**unsigned, "auth_tag": tag})[:24],
        revision=SEALED_IPC_CORE_REVISION,
        principal_commitment=principal,
        operating_matter_id=operating_matter_id,
        allowed_operation=operation,
        issued_tick=issued_tick,
        expires_tick=expires_tick,
        nonce=nonce,
        idempotency_key=idempotency_key,
        auth_tag=tag,
        contains_raw_principal=False,
        contains_path=False,
        contains_secret=False,
        contains_payload=False,
    )


def build_request(
    capability: SealedIpcCapability,
    *,
    request_commitment: str,
) -> SealedIpcRequest:
    if type(capability) is not SealedIpcCapability:
        raise TypeError("ipc_capability_type_denied")
    if not _HEX_64.fullmatch(request_commitment):
        raise ValueError("ipc_request_commitment_invalid")
    payload = {
        "revision": SEALED_IPC_CORE_REVISION,
        "capability_hash": capability.capability_hash,
        "operation": capability.allowed_operation,
        "operating_matter_id": capability.operating_matter_id,
        "request_commitment": request_commitment,
        "nonce": capability.nonce,
        "idempotency_key": capability.idempotency_key,
    }
    return SealedIpcRequest(
        request_id="IPCREQ-" + digest(payload)[:24],
        revision=SEALED_IPC_CORE_REVISION,
        capability=capability,
        operation=capability.allowed_operation,
        operating_matter_id=capability.operating_matter_id,
        request_commitment=request_commitment,
        nonce=capability.nonce,
        idempotency_key=capability.idempotency_key,
        contains_payload=False,
        canonical_write_requested=False,
        external_effect_requested=False,
    )


class AppendOnlyReplayLedger:
    """Sealed-side reference ledger; never expose entries to a worker."""

    def __init__(self) -> None:
        self._entries: list[SealedReplayEntry] = []
        self._nonce_hashes: set[str] = set()
        self._idempotency: dict[str, tuple[str, SealedIpcSuccessReceipt]] = {}
        self._lock = RLock()

    def has_nonce(self, nonce_hash: str) -> bool:
        with self._lock:
            return nonce_hash in self._nonce_hashes

    def prior_success(
        self, idempotency_hash: str
    ) -> tuple[str, SealedIpcSuccessReceipt] | None:
        with self._lock:
            return self._idempotency.get(idempotency_hash)

    def append(
        self,
        *,
        request: SealedIpcRequest,
        principal: str,
        disposition: Literal["ACCEPTED", "DENIED"],
        internal_denial_code: InternalDenialCode | Literal[""],
        success: SealedIpcSuccessReceipt | None = None,
    ) -> SealedReplayEntry:
        with self._lock:
            prior_hash = self._entries[-1].entry_hash if self._entries else digest("ipc-ledger-genesis-v1")
            nonce_hash = digest(request.nonce)
            idem_hash = digest(request.idempotency_key)
            unsigned = {
                "sequence": len(self._entries) + 1,
                "request_hash": request.request_hash,
                "capability_hash": request.capability.capability_hash,
                "principal_commitment": principal,
                "nonce_commitment": nonce_hash,
                "idempotency_key_commitment": idem_hash,
                "disposition": disposition,
                "internal_denial_code": internal_denial_code,
                "prior_entry_hash": prior_hash,
            }
            entry = SealedReplayEntry(
                **unsigned,
                entry_hash=digest(unsigned),
                worker_visible=False,
            )
            self._entries.append(entry)
            self._nonce_hashes.add(nonce_hash)
            if disposition == "ACCEPTED" and success is not None:
                self._idempotency[idem_hash] = (request.request_hash, success)
            return entry

    def sealed_entries(self) -> tuple[SealedReplayEntry, ...]:
        with self._lock:
            return tuple(self._entries)


def _generic_denial(request: object) -> GenericDenialReceipt:
    request_id = getattr(request, "request_id", "IPCREQ-UNKNOWN")
    return GenericDenialReceipt(
        request_id=request_id if isinstance(request_id, str) else "IPCREQ-UNKNOWN",
        revision=SEALED_IPC_CORE_REVISION,
        disposition="DENIED",
        contains_reason=False,
        contains_identity=False,
        contains_path=False,
        contains_secret=False,
    )


class SealedIpcAuthorizer:
    def __init__(self, signing_key: bytes, ledger: AppendOnlyReplayLedger) -> None:
        if type(signing_key) is not bytes or len(signing_key) < 32:
            raise ValueError("ipc_signing_key_invalid")
        self._signing_key = signing_key
        self._ledger = ledger

    def authorize(
        self,
        request: SealedIpcRequest,
        *,
        authenticated_principal_commitment: str,
        current_tick: int,
        result_commitment: str,
    ) -> GenericDenialReceipt | SealedIpcSuccessReceipt:
        denial: InternalDenialCode | None = None
        if type(request) is not SealedIpcRequest:
            return _generic_denial(request)
        capability = request.capability
        if type(capability) is not SealedIpcCapability:
            return _generic_denial(request)
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
            expected_tag = _auth_tag(self._signing_key, unsigned)
            expected_capability_id = "IPCCAP-" + digest(
                {**unsigned, "auth_tag": expected_tag}
            )[:24]
            expected_request = build_request(
                capability,
                request_commitment=request.request_commitment,
            )
        except (AttributeError, TypeError, ValueError):
            expected_tag = ""
            expected_capability_id = ""
            expected_request = None
            denial = "INVALID_REQUEST"
        if denial is None and (
            capability.revision != SEALED_IPC_CORE_REVISION
            or not hmac.compare_digest(capability.auth_tag, expected_tag)
            or capability.capability_id != expected_capability_id
            or request != expected_request
            or request.contains_payload
            or request.canonical_write_requested
            or request.external_effect_requested
            or not _HEX_64.fullmatch(result_commitment)
        ):
            denial = "INVALID_REQUEST"
        elif not hmac.compare_digest(
            capability.principal_commitment,
            authenticated_principal_commitment,
        ):
            denial = "IDENTITY_MISMATCH"
        elif (
            request.operation != capability.allowed_operation
            or request.operating_matter_id != capability.operating_matter_id
        ):
            denial = "AUTHORITY_MISMATCH"
        elif current_tick < capability.issued_tick or current_tick >= capability.expires_tick:
            denial = "EXPIRED"
        else:
            idem_hash = digest(request.idempotency_key)
            prior = self._ledger.prior_success(idem_hash)
            if prior is not None:
                prior_request_hash, prior_receipt = prior
                if hmac.compare_digest(prior_request_hash, request.request_hash):
                    duplicate_receipt = replace(prior_receipt, duplicate=True)
                    self._ledger.append(
                        request=request,
                        principal=authenticated_principal_commitment,
                        disposition="ACCEPTED",
                        internal_denial_code="",
                        success=prior_receipt,
                    )
                    return duplicate_receipt
                denial = "REPLAYED"
            elif self._ledger.has_nonce(digest(request.nonce)):
                denial = "REPLAYED"

        if denial is not None:
            self._ledger.append(
                request=request,
                principal=authenticated_principal_commitment,
                disposition="DENIED",
                internal_denial_code=denial,
            )
            return _generic_denial(request)

        receipt_payload = {
            "request_hash": request.request_hash,
            "operation": request.operation,
            "operating_matter_id": request.operating_matter_id,
            "result_commitment": result_commitment,
        }
        receipt = SealedIpcSuccessReceipt(
            receipt_id="IPCRCP-" + digest(receipt_payload)[:24],
            revision=SEALED_IPC_CORE_REVISION,
            request_id=request.request_id,
            operation=request.operation,
            operating_matter_id=request.operating_matter_id,
            result_commitment=result_commitment,
            disposition="ACCEPTED",
            duplicate=False,
            contains_payload=False,
            contains_sealed_material=False,
            external_effects=False,
        )
        self._ledger.append(
            request=request,
            principal=authenticated_principal_commitment,
            disposition="ACCEPTED",
            internal_denial_code="",
            success=receipt,
        )
        return receipt


def encode_frame(value: object, *, max_bytes: int = MAX_FRAME_BYTES) -> bytes:
    if max_bytes <= 0 or max_bytes > MAX_FRAME_BYTES:
        raise ValueError("ipc_frame_limit_invalid")
    payload = canonical_json(value).encode("utf-8")
    if not payload or len(payload) > max_bytes:
        raise ValueError("ipc_frame_size_denied")
    return struct.pack(">I", len(payload)) + payload


def decode_frame(frame: bytes, *, max_bytes: int = MAX_FRAME_BYTES) -> dict[str, object]:
    if type(frame) is not bytes or len(frame) < 5:
        raise ValueError("ipc_frame_truncated")
    declared = struct.unpack(">I", frame[:4])[0]
    payload = frame[4:]
    if declared != len(payload) or declared == 0 or declared > max_bytes:
        raise ValueError("ipc_frame_length_denied")
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("ipc_frame_json_invalid") from exc
    if not isinstance(decoded, dict):
        raise ValueError("ipc_frame_object_required")
    if canonical_json(decoded).encode("utf-8") != payload:
        raise ValueError("ipc_frame_noncanonical")
    return decoded
