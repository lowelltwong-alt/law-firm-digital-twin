from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
import sys

import pytest

from law_firm_digital_twin.hashio import digest
from law_firm_digital_twin.operational_router_process import (
    invoke_process_router, validate_process_response,
)
from law_firm_digital_twin.operational_router_protocol import (
    FIXTURE_ID, MAX_REQUEST_BYTES, PROTOCOL_REVISION,
    ProcessRouteRequest, ProcessRouteResponse,
)
from law_firm_digital_twin.operational_router_worker import handle_request


def request(**changes: object) -> ProcessRouteRequest:
    return replace(ProcessRouteRequest(
        protocol_revision=PROTOCOL_REVISION, request_id="REQ-PROCESS-1",
        fixture_id=FIXTURE_ID, capability_id="ops.intake.triage",
        requester_role_id="ops-practice-router",
    ), **changes)


def raw_worker(payload: bytes) -> tuple[dict[str, object], bytes]:
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "-I", str(root / "scripts" / "operational_router_service_bootstrap.py")],
        input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=8, cwd=root, env={},
    )
    assert completed.returncode == 0 and completed.stderr == b""
    return json.loads(completed.stdout), completed.stdout


def raw_payload(item: ProcessRouteRequest) -> dict[str, object]:
    value = asdict(item)
    for field in (
        "source_admission_receipt_ids", "reuse_release_receipt_ids",
        "authority_artifact_ids", "prerequisite_receipt_ids",
    ):
        value[field] = list(value[field])
    return value


def test_process_route_is_rederived_and_worker_does_not_attest_transport() -> None:
    item = request()
    response = invoke_process_router(item)
    assert response.status == "ok" and response.decision is not None
    assert response.decision["worker_role_id"] == "ops-intake-triage"
    assert response.decision["checker_role_id"] == "ops-quality-checker"
    assert response.decision["request_id"].startswith("REQREF-")
    assert item.request_id not in json.dumps(asdict(response))
    assert response.receipt is not None
    assert response.receipt.worker_transport_attested is False
    assert response.receipt.physical_identity_isolation_qualified is False
    assert response.receipt.canonical_activation_authorized is False
    assert validate_process_response(item, response) == ()
    direct = handle_request(json.dumps(raw_payload(item)).encode())
    assert direct.receipt is not None and direct.receipt.worker_transport_attested is False


def test_two_fresh_processes_are_raw_byte_deterministic() -> None:
    payload = json.dumps(raw_payload(request()), sort_keys=True, separators=(",", ":")).encode()
    first, first_raw = raw_worker(payload)
    second, second_raw = raw_worker(payload)
    assert first == second and first_raw == second_raw


@pytest.mark.parametrize(
    "injected", ["authority_ledger", "records", "ledger_path", "runtime_path", "provider", "api_key", "environment"],
)
def test_closed_protocol_rejects_authority_path_provider_key_and_env_injection(injected: str) -> None:
    payload = raw_payload(request())
    payload[injected] = {"approved": True}
    response, _ = raw_worker(json.dumps(payload).encode())
    assert response["status"] == "blocked"
    assert response["error_code"] == "request_fields_invalid"
    assert response["decision"] is None and response["receipt"] is None


@pytest.mark.parametrize(
    ("payload", "error"),
    [(b"not-json", "malformed_json"), (b"[]", "request_not_object"), (b"x" * (MAX_REQUEST_BYTES + 1), "request_too_large")],
)
def test_malformed_nonobject_and_oversized_inputs_fail_closed(payload: bytes, error: str) -> None:
    response, _ = raw_worker(payload)
    assert response["status"] == "blocked" and response["error_code"] == error
    assert "traceback" not in json.dumps(response).lower()


def test_paths_and_unbounded_identifiers_are_rejected_before_routing() -> None:
    for field, value in (
        ("request_id", r"C:\private\runtime.key"),
        ("requested_adapter", "../private/key"),
        ("authority_artifact_ids", ["X"] * 33),
    ):
        payload = raw_payload(request())
        payload[field] = value
        response, _ = raw_worker(json.dumps(payload).encode())
        assert response["status"] == "blocked"
        assert response["error_code"] in {"request_types_invalid", "request_value_invalid"}


def test_invented_authority_is_hashed_not_reflected_and_cannot_open_matter() -> None:
    item = request(
        capability_id="ops.matter.opening.packet",
        authority_artifact_ids=("sk-live-SECRET",),
    )
    response = invoke_process_router(item)
    serialized = json.dumps(asdict(response))
    assert response.status == "ok" and response.decision is not None
    assert response.decision["status"] == "blocked"
    assert "sk-live-SECRET" not in serialized
    assert any(code.startswith("unverified_record_ref:sha256:") for code in response.decision["reason_codes"])


def test_private_external_and_human_only_work_remain_blocked() -> None:
    for item in (
        request(data_class="client", synthetic_only=False),
        request(external_io=True),
        request(capability_id="legal.settlement.authorize"),
    ):
        response = invoke_process_router(item)
        assert response.status == "ok" and response.decision is not None
        assert response.decision["status"] == "blocked"


def test_checker_rejects_every_receipt_field_mutation_and_rewritten_decision() -> None:
    item = request()
    response = invoke_process_router(item)
    assert response.receipt is not None and response.decision is not None
    receipt_mutations = {
        "service_revision": "forged", "fixture_id": "forged",
        "fixture_commitment": "sha256:forged", "environment_commitment": "sha256:forged",
        "source_revision_commitment": "sha256:forged", "schema_commitment": "sha256:forged",
        "request_commitment": "sha256:forged", "decision_commitment": "sha256:forged",
        "worker_transport_attested": True, "physical_identity_isolation_qualified": True,
        "canonical_activation_authorized": True,
    }
    for field, value in receipt_mutations.items():
        mutation = replace(response, receipt=replace(response.receipt, **{field: value}))
        assert validate_process_response(item, mutation)
    changed = dict(response.decision)
    changed["worker_role_id"] = "attacker-worker"
    forged_receipt = replace(response.receipt, decision_commitment="sha256:" + digest(changed))
    assert validate_process_response(item, replace(response, decision=changed, receipt=forged_receipt))


def test_blocked_response_must_use_safe_string_error_code() -> None:
    for error in ({"traceback": "SECRET"}, "traceback: SECRET", 7, "invented_error"):
        forged = ProcessRouteResponse(PROTOCOL_REVISION, "blocked", None, None, error)  # type: ignore[arg-type]
        assert validate_process_response(request(), forged)


def test_response_contains_no_ledger_rows_paths_sealed_data_or_internal_exception() -> None:
    serialized = json.dumps(asdict(invoke_process_router(request())), sort_keys=True).lower()
    for forbidden in (
        '"authority_ledger":', '"records":', "ledger_id", "source_body",
        "sealed_world", "runtime_path", "traceback", "exception",
    ):
        assert forbidden not in serialized


def test_timeout_and_crash_are_bounded_without_stderr_leakage(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired("worker", 0.01)
    monkeypatch.setattr(subprocess, "run", timeout)
    timed_out = invoke_process_router(request(), timeout_seconds=0.01)
    assert timed_out.status == "blocked" and timed_out.error_code == "service_timeout"

    class Completed:
        returncode = 7
        stdout = b""
        stderr = b"private internal failure"
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Completed())
    crashed = invoke_process_router(request())
    assert crashed.status == "blocked" and crashed.error_code == "service_crash"
    assert "private internal failure" not in json.dumps(asdict(crashed))


def test_schema_closes_request_decision_receipt_and_both_response_shapes() -> None:
    schema = json.loads((Path(__file__).resolve().parents[1] / "schemas" / "operational-router-process-v1.schema.json").read_text())
    assert set(schema["$defs"]) >= {"request", "decision", "receipt", "success", "blocked"}
    for name in ("request", "decision", "receipt", "success", "blocked"):
        assert schema["$defs"][name]["additionalProperties"] is False
    assert schema["$defs"]["success"]["properties"]["status"] == {"const": "ok"}
    assert schema["$defs"]["blocked"]["properties"]["status"] == {"const": "blocked"}
