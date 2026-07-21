from __future__ import annotations

from dataclasses import asdict, fields
import json
from pathlib import Path
import re

from law_firm_digital_twin.hashio import digest
from law_firm_digital_twin.sealed_ipc_protocol import (
    SealedIpcCapability,
    SealedIpcRequest,
    build_request,
    issue_capability,
    principal_commitment,
)
from law_firm_digital_twin.windows_secure_pipe_adapter import (
    RuntimePrivatePipeConfig,
    SecurePipeStaticQualification,
    build_static_qualification,
)


ROOT = Path(__file__).resolve().parents[1]


def _assert_schema_matches(schema_name: str, value: object, contract: type) -> None:
    schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    assert set(schema["required"]) == {item.name for item in fields(contract)}
    assert set(schema["properties"]) == {item.name for item in fields(contract)}
    payload = asdict(value)
    for name, definition in schema["properties"].items():
        if "const" in definition:
            assert payload[name] == definition["const"]
        if "pattern" in definition:
            assert re.fullmatch(definition["pattern"], payload[name])


def test_sealed_ipc_capability_and_request_schemas_match_contracts() -> None:
    capability = issue_capability(
        signing_key=b"schema-test-key-000000000000000000000",
        principal=principal_commitment("S-1-5-21-1-2-3-1102"),
        operating_matter_id="MAT-001",
        operation="SubmitIngressCommitment",
        issued_tick=1,
        expires_tick=2,
        nonce="nonce-schema",
        idempotency_key="idem-schema",
    )
    request = build_request(capability, request_commitment=digest("request"))
    _assert_schema_matches("sealed-ipc-capability-v1.schema.json", capability, SealedIpcCapability)
    _assert_schema_matches("sealed-ipc-request-v1.schema.json", request, SealedIpcRequest)


def test_secure_pipe_static_qualification_schema_matches_contract() -> None:
    receipt = build_static_qualification(
        RuntimePrivatePipeConfig(
            pipe_name=r"\\.\pipe\lfdt-schema",
            kernel_sid="S-1-5-21-1-2-3-1101",
            worker_sid="S-1-5-21-1-2-3-1102",
        )
    )
    _assert_schema_matches(
        "secure-pipe-static-qualification-v1.schema.json",
        receipt,
        SecurePipeStaticQualification,
    )
