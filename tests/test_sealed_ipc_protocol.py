from __future__ import annotations

from dataclasses import replace

import pytest

from law_firm_digital_twin.hashio import digest
from law_firm_digital_twin.sealed_ipc_protocol import (
    MAX_FRAME_BYTES,
    AppendOnlyReplayLedger,
    GenericDenialReceipt,
    SealedIpcAuthorizer,
    build_request,
    decode_frame,
    encode_frame,
    issue_capability,
    principal_commitment,
)
from law_firm_digital_twin.sealed_ipc_validator import (
    validate_capability,
    validate_external_receipt,
    validate_replay_ledger,
    validate_request,
)


KEY = b"sealed-ipc-test-signing-key-000000000000000"
WORKER = principal_commitment("S-1-5-21-100-200-300-1102")


def _capability(**changes):
    values = {
        "signing_key": KEY,
        "principal": WORKER,
        "operating_matter_id": "MAT-OPERATING-001",
        "operation": "RequestOperatingProjection",
        "issued_tick": 10,
        "expires_tick": 20,
        "nonce": "nonce-001",
        "idempotency_key": "idem-001",
    }
    values.update(changes)
    return issue_capability(**values)


def test_capability_request_success_and_exact_duplicate_are_valid() -> None:
    capability = _capability()
    request = build_request(capability, request_commitment=digest("request"))
    ledger = AppendOnlyReplayLedger()
    authorizer = SealedIpcAuthorizer(KEY, ledger)

    first = authorizer.authorize(
        request,
        authenticated_principal_commitment=WORKER,
        current_tick=11,
        result_commitment=digest("projection"),
    )
    duplicate = authorizer.authorize(
        request,
        authenticated_principal_commitment=WORKER,
        current_tick=12,
        result_commitment=digest("projection"),
    )

    assert validate_capability(capability, signing_key=KEY) == ()
    assert validate_request(request, signing_key=KEY) == ()
    assert validate_external_receipt(first) == ()
    assert validate_external_receipt(duplicate) == ()
    assert first.disposition == "ACCEPTED"
    assert duplicate.disposition == "ACCEPTED"
    assert duplicate.duplicate is True
    assert len(ledger.sealed_entries()) == 2
    assert validate_replay_ledger(ledger) == ()


def test_external_denials_are_identical_while_sealed_ledger_keeps_reason() -> None:
    cases = (
        (_capability(nonce="wrong-id"), principal_commitment("S-1-5-21-9-9-9-9"), 11, "IDENTITY_MISMATCH"),
        (_capability(nonce="expired"), WORKER, 21, "EXPIRED"),
    )
    for capability, observed_principal, tick, reason in cases:
        request = build_request(capability, request_commitment=digest(reason))
        ledger = AppendOnlyReplayLedger()
        denial = SealedIpcAuthorizer(KEY, ledger).authorize(
            request,
            authenticated_principal_commitment=observed_principal,
            current_tick=tick,
            result_commitment=digest("unused"),
        )
        assert denial == GenericDenialReceipt(
            request_id=request.request_id,
            revision="sealed-ipc-core-g0-v1",
            disposition="DENIED",
            contains_reason=False,
            contains_identity=False,
            contains_path=False,
            contains_secret=False,
        )
        assert ledger.sealed_entries()[-1].internal_denial_code == reason


def test_capability_and_request_mutations_fail_closed() -> None:
    capability = _capability()
    request = build_request(capability, request_commitment=digest("request"))
    hostile_capabilities = (
        replace(capability, auth_tag="0" * 64),
        replace(capability, expires_tick=10),
        replace(capability, contains_secret=True),  # type: ignore[arg-type]
    )
    assert all(validate_capability(item, signing_key=KEY) for item in hostile_capabilities)
    hostile_requests = (
        replace(request, request_id="IPCREQ-forged"),
        replace(request, contains_payload=True),  # type: ignore[arg-type]
        replace(request, external_effect_requested=True),  # type: ignore[arg-type]
    )
    assert all(validate_request(item, signing_key=KEY) for item in hostile_requests)


def test_malformed_exact_request_returns_generic_denial_without_exception() -> None:
    capability = _capability(nonce="malformed")
    request = build_request(capability, request_commitment=digest("valid"))
    malformed = replace(request, request_commitment="not-a-commitment")
    ledger = AppendOnlyReplayLedger()
    denial = SealedIpcAuthorizer(KEY, ledger).authorize(
        malformed,
        authenticated_principal_commitment=WORKER,
        current_tick=11,
        result_commitment=digest("unused"),
    )
    assert denial.disposition == "DENIED"
    assert denial.contains_reason is False
    assert ledger.sealed_entries()[-1].internal_denial_code == "INVALID_REQUEST"


def test_conflicting_idempotency_and_nonce_replay_are_generic_denials() -> None:
    ledger = AppendOnlyReplayLedger()
    authorizer = SealedIpcAuthorizer(KEY, ledger)
    first = build_request(_capability(), request_commitment=digest("first"))
    assert authorizer.authorize(
        first,
        authenticated_principal_commitment=WORKER,
        current_tick=11,
        result_commitment=digest("ok"),
    ).disposition == "ACCEPTED"

    conflicting = build_request(
        _capability(nonce="nonce-002"),
        request_commitment=digest("different"),
    )
    denial = authorizer.authorize(
        conflicting,
        authenticated_principal_commitment=WORKER,
        current_tick=12,
        result_commitment=digest("unused"),
    )
    assert denial.disposition == "DENIED"
    assert denial.contains_reason is False
    assert ledger.sealed_entries()[-1].internal_denial_code == "REPLAYED"


def test_canonical_framing_is_bounded_and_rejects_ambiguity() -> None:
    frame = encode_frame({"b": 2, "a": 1})
    assert decode_frame(frame) == {"a": 1, "b": 2}
    with pytest.raises(ValueError, match="length_denied"):
        decode_frame(b"\x00\x00\x00\x10{}")
    noncanonical = b'{"b":2,"a":1}'
    with pytest.raises(ValueError, match="noncanonical"):
        decode_frame(len(noncanonical).to_bytes(4, "big") + noncanonical)
    with pytest.raises(ValueError, match="size_denied"):
        encode_frame({"x": "a" * MAX_FRAME_BYTES})
