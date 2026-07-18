from __future__ import annotations

import json
from pathlib import Path

import pytest

from law_firm_digital_twin.operational_router_process import (
    MAX_RESPONSE_BYTES,
    invoke_process_router,
    qualification_summary,
)
from law_firm_digital_twin.operational_router_protocol import (
    FIXTURE_ID,
    PROTOCOL_REVISION,
    ProcessRouteRequest,
)


def request() -> ProcessRouteRequest:
    return ProcessRouteRequest(
        protocol_revision=PROTOCOL_REVISION,
        request_id="REQ-RELEASE-GATE",
        fixture_id=FIXTURE_ID,
        capability_id="ops.intake.triage",
        requester_role_id="ops-practice-router",
    )


class Completed:
    returncode = 0


def test_nonobject_receipt_is_not_normalized_into_valid_blocked_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forged = json.dumps({
        "protocol_revision": PROTOCOL_REVISION,
        "status": "blocked",
        "decision": None,
        "receipt": [],
        "error_code": "malformed_json",
    }).encode()

    def fake_run(*args: object, **kwargs: object) -> Completed:
        kwargs["stdout"].write(forged)  # type: ignore[union-attr]
        return Completed()

    monkeypatch.setattr("subprocess.run", fake_run)
    response = invoke_process_router(request())
    assert response.status == "blocked"
    assert response.error_code == "response_invalid"


def test_worker_output_is_spooled_and_rejected_before_unbounded_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> Completed:
        kwargs["stdout"].write(b"x" * (MAX_RESPONSE_BYTES + 1))  # type: ignore[union-attr]
        return Completed()

    monkeypatch.setattr("subprocess.run", fake_run)
    response = invoke_process_router(request())
    assert response.status == "blocked"
    assert response.error_code == "response_invalid"


def test_checked_in_summary_matches_fresh_revision_bound_qualification() -> None:
    root = Path(__file__).resolve().parents[1]
    checked_in = json.loads(
        (root / "generated" / "operational-router-process-v1" / "summary.json").read_text()
    )
    assert qualification_summary(launches=10) == checked_in
