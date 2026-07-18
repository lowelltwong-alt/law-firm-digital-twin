from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Literal

from .hashio import digest
from .operational_mesh_contracts import OperationalRoutingDecision, OperationalWorkRequest


PROTOCOL_REVISION = "lfdt-operational-router-process-v1"
SERVICE_REVISION = "lfdt-operational-router-service-g2-v2"
MAX_REQUEST_BYTES = 16_384
MAX_IDENTIFIER_ITEMS = 32
FIXTURE_ID = "employment-green-g2-v1"
FIXTURE_SEED = "operational-router-process-v1"
FIXTURE_RUN_ID = "RUN-OPERATIONAL-PROCESS-V1"
FIXTURE_ARM = "ai_first"
FIXTURE_ROUTE = "trial_appeal"

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
_REQUEST_FIELDS = {
    "protocol_revision", "request_id", "fixture_id", "capability_id",
    "requester_role_id", "data_class", "effect_class",
    "source_admission_receipt_ids", "reuse_release_receipt_ids",
    "authority_artifact_ids", "prerequisite_receipt_ids",
    "requested_adapter", "synthetic_only", "external_io",
}
SAFE_BLOCK_CODES = {
    "fixture_unknown", "malformed_json", "protocol_revision_invalid",
    "request_fields_invalid", "request_not_object", "request_too_large",
    "request_types_invalid", "request_value_invalid", "service_failure",
    "service_timeout", "service_crash", "response_invalid",
}


class ProtocolError(ValueError):
    """A bounded, public-safe protocol failure."""


@dataclass(frozen=True)
class ProcessRouteRequest:
    protocol_revision: Literal["lfdt-operational-router-process-v1"]
    request_id: str
    fixture_id: Literal["employment-green-g2-v1"]
    capability_id: str
    requester_role_id: str
    data_class: Literal["synthetic", "public", "private", "client"] = "synthetic"
    effect_class: Literal[
        "advisory_only", "simulation_planning_only", "external_write",
        "legal_decision", "financial_posting",
    ] = "simulation_planning_only"
    source_admission_receipt_ids: tuple[str, ...] = ()
    reuse_release_receipt_ids: tuple[str, ...] = ()
    authority_artifact_ids: tuple[str, ...] = ()
    prerequisite_receipt_ids: tuple[str, ...] = ()
    requested_adapter: str | None = None
    synthetic_only: bool = True
    external_io: bool = False

    @property
    def request_commitment(self) -> str:
        return "sha256:" + digest(self)


@dataclass(frozen=True)
class ProcessQualificationReceipt:
    protocol_revision: str
    service_revision: str
    fixture_id: str
    fixture_commitment: str
    environment_commitment: str
    source_revision_commitment: str
    schema_commitment: str
    request_commitment: str
    decision_commitment: str
    worker_transport_attested: Literal[False] = False
    physical_identity_isolation_qualified: Literal[False] = False
    canonical_activation_authorized: Literal[False] = False


@dataclass(frozen=True)
class ProcessRouteResponse:
    protocol_revision: str
    status: Literal["ok", "blocked"]
    decision: dict[str, Any] | None
    receipt: ProcessQualificationReceipt | None
    error_code: str | None


def _valid_identifier(value: object) -> bool:
    return isinstance(value, str) and bool(_IDENTIFIER.fullmatch(value))


def parse_request_bytes(raw: bytes) -> ProcessRouteRequest:
    if len(raw) > MAX_REQUEST_BYTES:
        raise ProtocolError("request_too_large")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("malformed_json") from exc
    if not isinstance(value, dict):
        raise ProtocolError("request_not_object")
    if set(value) != _REQUEST_FIELDS:
        raise ProtocolError("request_fields_invalid")
    tuple_fields = (
        "source_admission_receipt_ids", "reuse_release_receipt_ids",
        "authority_artifact_ids", "prerequisite_receipt_ids",
    )
    for field in tuple_fields:
        items = value[field]
        if (
            not isinstance(items, list)
            or len(items) > MAX_IDENTIFIER_ITEMS
            or not all(_valid_identifier(item) for item in items)
        ):
            raise ProtocolError("request_types_invalid")
        value[field] = tuple(items)
    for field in ("request_id", "capability_id", "requester_role_id"):
        if not _valid_identifier(value[field]):
            raise ProtocolError("request_value_invalid")
    if value["requested_adapter"] is not None and not _valid_identifier(value["requested_adapter"]):
        raise ProtocolError("request_value_invalid")
    if type(value["synthetic_only"]) is not bool or type(value["external_io"]) is not bool:
        raise ProtocolError("request_types_invalid")
    if value["protocol_revision"] != PROTOCOL_REVISION:
        raise ProtocolError("protocol_revision_invalid")
    if value["fixture_id"] != FIXTURE_ID:
        raise ProtocolError("fixture_unknown")
    if value["data_class"] not in {"synthetic", "public", "private", "client"}:
        raise ProtocolError("request_value_invalid")
    if value["effect_class"] not in {
        "advisory_only", "simulation_planning_only", "external_write",
        "legal_decision", "financial_posting",
    }:
        raise ProtocolError("request_value_invalid")
    return ProcessRouteRequest(**value)


def request_to_bytes(request: ProcessRouteRequest) -> bytes:
    return json.dumps(asdict(request), sort_keys=True, separators=(",", ":")).encode("utf-8")


def public_request_handle(request: ProcessRouteRequest) -> str:
    return "REQREF-" + digest({"request_id": request.request_id})[:20]


def bounded_environment_commitment() -> str:
    return "sha256:" + digest({
        "python_contract": ">=3.11",
        "isolated_mode_required": True,
        "inherited_environment_keys": (),
        "external_io_allowed": False,
        "service_revision": SERVICE_REVISION,
    })


def _normalized_file_hash(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def source_revision_commitment() -> str:
    root = Path(__file__).resolve().parents[2]
    paths = (
        "src/law_firm_digital_twin/operational_router_protocol.py",
        "src/law_firm_digital_twin/operational_router_process.py",
        "src/law_firm_digital_twin/operational_router_worker.py",
        "src/law_firm_digital_twin/operational_mesh_contracts.py",
        "src/law_firm_digital_twin/operational_mesh_registry.py",
        "src/law_firm_digital_twin/operational_mesh_router.py",
        "src/law_firm_digital_twin/kernel.py",
        "src/law_firm_digital_twin/factory.py",
        "src/law_firm_digital_twin/hashio.py",
        "src/law_firm_digital_twin/models.py",
        "src/law_firm_digital_twin/rules.py",
        "scripts/operational_router_service_bootstrap.py",
        "scripts/build_operational_router_process_qualification.py",
        "tests/test_operational_router_process.py",
        "tests/test_operational_router_process_release_gate.py",
        "docs/decisions/g2_operational_router_process_boundary.md",
        "schemas/operational-router-process-v1.schema.json",
        "registry/source-admission-receipts.json",
    )
    return "sha256:" + digest({item: _normalized_file_hash(root / item) for item in paths})


def schema_commitment() -> str:
    path = Path(__file__).resolve().parents[2] / "schemas" / "operational-router-process-v1.schema.json"
    return "sha256:" + _normalized_file_hash(path)


def sanitize_decision_payload(decision: OperationalRoutingDecision) -> dict[str, Any]:
    payload = asdict(decision)
    sanitized: list[str] = []
    for reason in payload["reason_codes"]:
        prefix, separator, supplied = reason.partition(":")
        if separator and prefix in {"unverified_record", "invalid_record"}:
            sanitized.append(f"{prefix}_ref:sha256:{digest({'record_ref': supplied})[:24]}")
        else:
            sanitized.append(reason)
    payload["reason_codes"] = tuple(sanitized)
    return payload


def to_operational_request(request: ProcessRouteRequest, *, matter_commitment: str) -> OperationalWorkRequest:
    return OperationalWorkRequest(
        request_id=public_request_handle(request), matter_commitment=matter_commitment,
        capability_id=request.capability_id, requester_role_id=request.requester_role_id,
        data_class=request.data_class, effect_class=request.effect_class,
        source_admission_receipt_ids=request.source_admission_receipt_ids,
        reuse_release_receipt_ids=request.reuse_release_receipt_ids,
        authority_artifact_ids=request.authority_artifact_ids,
        prerequisite_receipt_ids=request.prerequisite_receipt_ids,
        requested_adapter=request.requested_adapter,
        synthetic_only=request.synthetic_only, external_io=request.external_io,
    )
