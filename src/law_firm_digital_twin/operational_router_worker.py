from __future__ import annotations

from dataclasses import asdict
import json

from .factory import build_employment_matter
from .hashio import digest
from .kernel import WorldKernel
from .models import Route
from .operational_router_protocol import (
    FIXTURE_ARM, FIXTURE_ID, FIXTURE_RUN_ID, FIXTURE_SEED,
    PROTOCOL_REVISION, SERVICE_REVISION,
    ProcessQualificationReceipt, ProcessRouteResponse, ProtocolError,
    bounded_environment_commitment, parse_request_bytes,
    sanitize_decision_payload, schema_commitment, source_revision_commitment,
    to_operational_request,
)
from .rules import placeholder_data_first_rule_pack


def build_fixture_kernel() -> WorldKernel:
    matter = build_employment_matter(FIXTURE_SEED, placeholder_data_first_rule_pack())
    return WorldKernel(
        run_id=FIXTURE_RUN_ID, matter=matter,
        arm_label=FIXTURE_ARM, route=Route.TRIAL_APPEAL,
    )


def fixture_commitment(kernel: WorldKernel) -> str:
    return "sha256:" + digest({
        "fixture_id": FIXTURE_ID,
        "matter_commitment": kernel.operational_matter_commitment,
        "rule_pack": kernel.matter.rule_pack,
        "service_revision": SERVICE_REVISION,
    })


def handle_request(raw: bytes) -> ProcessRouteResponse:
    try:
        request = parse_request_bytes(raw)
        kernel = build_fixture_kernel()
        decision = sanitize_decision_payload(kernel.route_operational_work(
            to_operational_request(request, matter_commitment=kernel.operational_matter_commitment)
        ))
        receipt = ProcessQualificationReceipt(
            protocol_revision=PROTOCOL_REVISION,
            service_revision=SERVICE_REVISION,
            fixture_id=FIXTURE_ID,
            fixture_commitment=fixture_commitment(kernel),
            environment_commitment=bounded_environment_commitment(),
            source_revision_commitment=source_revision_commitment(),
            schema_commitment=schema_commitment(),
            request_commitment=request.request_commitment,
            decision_commitment="sha256:" + digest(decision),
        )
        return ProcessRouteResponse(PROTOCOL_REVISION, "ok", decision, receipt, None)
    except ProtocolError as exc:
        return ProcessRouteResponse(PROTOCOL_REVISION, "blocked", None, None, str(exc))
    except Exception:
        return ProcessRouteResponse(PROTOCOL_REVISION, "blocked", None, None, "service_failure")


def response_bytes(response: ProcessRouteResponse) -> bytes:
    return json.dumps(asdict(response), sort_keys=True, separators=(",", ":")).encode("utf-8")
