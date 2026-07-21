from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from .factory import build_employment_matter
from .hashio import digest
from .kernel import WorldKernel
from .models import Route
from .operational_router_protocol import (
    FIXTURE_ARM, FIXTURE_ID, FIXTURE_RUN_ID, FIXTURE_SEED,
    PROTOCOL_REVISION, SAFE_BLOCK_CODES, SERVICE_REVISION,
    ProcessQualificationReceipt, ProcessRouteRequest, ProcessRouteResponse,
    bounded_environment_commitment, request_to_bytes, sanitize_decision_payload,
    schema_commitment, source_revision_commitment, to_operational_request,
)
from .rules import placeholder_data_first_rule_pack


DEFAULT_TIMEOUT_SECONDS = 8.0
MAX_RESPONSE_BYTES = 65_536
MAX_STDERR_BYTES = 8_192
_RESPONSE_FIELDS = {"protocol_revision", "status", "decision", "receipt", "error_code"}
_RECEIPT_FIELDS = {
    "protocol_revision", "service_revision", "fixture_id", "fixture_commitment",
    "environment_commitment", "source_revision_commitment", "schema_commitment",
    "request_commitment", "decision_commitment", "worker_transport_attested",
    "physical_identity_isolation_qualified", "canonical_activation_authorized",
}
_DECISION_FIELDS = {
    "request_id", "request_hash", "status", "worker_role_id", "checker_role_id",
    "reason_codes", "required_human_gates", "registry_commitment",
    "authority_ledger_commitment", "mesh_revision", "proposal_only",
    "external_effects", "canonical_admission",
}


def _bootstrap_path() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts" / "operational_router_service_bootstrap.py"


def _run_worker(request: ProcessRouteRequest, timeout_seconds: float) -> tuple[ProcessRouteResponse, bytes]:
    try:
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            completed = subprocess.run(
                [sys.executable, "-I", str(_bootstrap_path())],
                input=request_to_bytes(request), stdout=stdout_file,
                stderr=stderr_file, check=False, timeout=timeout_seconds,
                cwd=str(_bootstrap_path().parent.parent), env={},
            )
            stdout_size = stdout_file.tell()
            stderr_size = stderr_file.tell()
            if stdout_size > MAX_RESPONSE_BYTES or stderr_size > MAX_STDERR_BYTES:
                return ProcessRouteResponse(PROTOCOL_REVISION, "blocked", None, None, "response_invalid"), b""
            stdout_file.seek(0)
            raw_response = stdout_file.read()
    except subprocess.TimeoutExpired:
        return ProcessRouteResponse(PROTOCOL_REVISION, "blocked", None, None, "service_timeout"), b""
    if completed.returncode != 0:
        return ProcessRouteResponse(PROTOCOL_REVISION, "blocked", None, None, "service_crash"), b""
    try:
        payload = json.loads(raw_response.decode("utf-8"))
        if not isinstance(payload, dict) or set(payload) != _RESPONSE_FIELDS:
            raise ValueError("response_fields_invalid")
        receipt_payload = payload.get("receipt")
        if receipt_payload is not None and not isinstance(receipt_payload, dict):
            raise ValueError("receipt_type_invalid")
        if isinstance(receipt_payload, dict) and set(receipt_payload) != _RECEIPT_FIELDS:
            raise ValueError("receipt_fields_invalid")
        receipt = ProcessQualificationReceipt(**receipt_payload) if isinstance(receipt_payload, dict) else None
        response = ProcessRouteResponse(
            protocol_revision=payload["protocol_revision"], status=payload["status"],
            decision=payload.get("decision"), receipt=receipt,
            error_code=payload.get("error_code"),
        )
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return ProcessRouteResponse(PROTOCOL_REVISION, "blocked", None, None, "response_invalid"), b""
    if validate_process_response(request, response):
        return ProcessRouteResponse(PROTOCOL_REVISION, "blocked", None, None, "response_invalid"), b""
    return response, raw_response


def invoke_process_router(
    request: ProcessRouteRequest, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
) -> ProcessRouteResponse:
    return _run_worker(request, timeout_seconds)[0]


def _expected_kernel() -> WorldKernel:
    matter = build_employment_matter(FIXTURE_SEED, placeholder_data_first_rule_pack())
    return WorldKernel(
        run_id=FIXTURE_RUN_ID, matter=matter,
        arm_label=FIXTURE_ARM, route=Route.TRIAL_APPEAL,
    )


def _expected_decision(request: ProcessRouteRequest) -> dict[str, Any]:
    kernel = _expected_kernel()
    payload = sanitize_decision_payload(kernel.route_operational_work(
        to_operational_request(request, matter_commitment=kernel.operational_matter_commitment)
    ))
    return json.loads(json.dumps(payload))


def _expected_fixture_commitment() -> str:
    kernel = _expected_kernel()
    return "sha256:" + digest({
        "fixture_id": FIXTURE_ID,
        "matter_commitment": kernel.operational_matter_commitment,
        "rule_pack": kernel.matter.rule_pack,
        "service_revision": SERVICE_REVISION,
    })


def validate_process_response(
    request: ProcessRouteRequest, response: ProcessRouteResponse
) -> tuple[str, ...]:
    errors: list[str] = []
    if response.protocol_revision != PROTOCOL_REVISION:
        errors.append("OPP-001:protocol_revision_invalid")
    if response.status == "blocked":
        if (
            response.decision is not None or response.receipt is not None
            or type(response.error_code) is not str
            or response.error_code not in SAFE_BLOCK_CODES
        ):
            errors.append("OPP-002:blocked_shape_invalid")
        return tuple(errors)
    if response.status != "ok" or response.error_code is not None:
        errors.append("OPP-003:status_invalid")
    if (
        not isinstance(response.decision, dict)
        or set(response.decision) != _DECISION_FIELDS
        or response.receipt is None
    ):
        errors.append("OPP-004:success_shape_invalid")
        return tuple(errors)
    receipt = response.receipt
    expected_values = {
        "protocol_revision": PROTOCOL_REVISION,
        "service_revision": SERVICE_REVISION,
        "fixture_id": FIXTURE_ID,
        "fixture_commitment": _expected_fixture_commitment(),
        "environment_commitment": bounded_environment_commitment(),
        "source_revision_commitment": source_revision_commitment(),
        "schema_commitment": schema_commitment(),
        "request_commitment": request.request_commitment,
        "decision_commitment": "sha256:" + digest(response.decision),
    }
    for field, expected in expected_values.items():
        if getattr(receipt, field) != expected:
            errors.append(f"OPP-005:{field}_invalid")
    if response.decision != _expected_decision(request):
        errors.append("OPP-006:decision_rederivation_failed")
    if (
        type(receipt.worker_transport_attested) is not bool
        or receipt.worker_transport_attested is not False
        or type(receipt.physical_identity_isolation_qualified) is not bool
        or receipt.physical_identity_isolation_qualified is not False
        or type(receipt.canonical_activation_authorized) is not bool
        or receipt.canonical_activation_authorized is not False
    ):
        errors.append("OPP-007:qualification_claim_invalid")
    serialized = json.dumps(asdict(response), sort_keys=True).lower()
    prohibited = ('"authority_ledger":', '"records":', '"source_body":', '"sealed_world":', '"runtime_path":', '"traceback":', '"exception":')
    if any(item in serialized for item in prohibited):
        errors.append("OPP-008:prohibited_output")
    return tuple(errors)


def qualification_summary(*, launches: int = 10) -> dict[str, Any]:
    request = ProcessRouteRequest(
        protocol_revision=PROTOCOL_REVISION, request_id="REQ-QUALIFY-1",
        fixture_id=FIXTURE_ID, capability_id="ops.intake.triage",
        requester_role_id="ops-practice-router",
    )
    attempts = tuple(_run_worker(request, DEFAULT_TIMEOUT_SECONDS) for _ in range(launches))
    responses = tuple(item[0] for item in attempts)
    raw_hashes = tuple("sha256:" + hashlib.sha256(item[1]).hexdigest() for item in attempts)
    passed = (
        launches >= 10 and all(item.status == "ok" for item in responses)
        and all(raw for _, raw in attempts) and len(set(raw_hashes)) == 1
        and not any(validate_process_response(request, item) for item in responses)
    )
    return {
        "schema_version": "lfdt.operational_router_process_qualification.v1",
        "protocol_revision": PROTOCOL_REVISION,
        "service_revision": SERVICE_REVISION,
        "source_revision_commitment": source_revision_commitment(),
        "schema_commitment": schema_commitment(),
        "fixture_commitment": _expected_fixture_commitment(),
        "launches": launches, "unique_raw_response_hashes": len(set(raw_hashes)),
        "raw_response_hash": raw_hashes[0] if raw_hashes else None,
        "same_user_subprocess_qualified": passed,
        "physical_identity_isolation_qualified": False,
        "canonical_activation_authorized": False,
        "status": "pass" if passed else "fail",
    }
