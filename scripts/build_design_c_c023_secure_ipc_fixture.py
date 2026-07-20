from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from law_firm_digital_twin.hashio import digest  # noqa: E402
from law_firm_digital_twin.sealed_ipc_protocol import (  # noqa: E402
    MAX_FRAME_BYTES,
    SEALED_IPC_CORE_REVISION,
    AppendOnlyReplayLedger,
    SealedIpcAuthorizer,
    build_request,
    issue_capability,
    principal_commitment,
)
from law_firm_digital_twin.sealed_ipc_validator import (  # noqa: E402
    SEALED_IPC_VALIDATOR_REVISION,
    validate_capability,
    validate_external_receipt,
    validate_replay_ledger,
    validate_request,
)
from law_firm_digital_twin.windows_secure_pipe_adapter import (  # noqa: E402
    WINDOWS_SECURE_PIPE_ADAPTER_REVISION,
    RuntimePrivatePipeConfig,
    build_static_qualification,
)
from law_firm_digital_twin.windows_secure_pipe_qualification import (  # noqa: E402
    WINDOWS_SECURE_PIPE_CHECKER_REVISION,
    independently_check_static_qualification,
)


OUTPUT = ROOT / "generated" / "design-c-c023-secure-ipc-v1"


def build_summary() -> dict[str, object]:
    signing_key = b"public-synthetic-fixture-key-not-a-runtime-key"
    config = RuntimePrivatePipeConfig(
        pipe_name=r"\\.\pipe\synthetic-lfdt-fixture",
        kernel_sid="S-1-5-21-111-222-333-1101",
        worker_sid="S-1-5-21-111-222-333-1102",
    )
    worker = principal_commitment(config.worker_sid)
    capability = issue_capability(
        signing_key=signing_key,
        principal=worker,
        operating_matter_id="MAT-SYNTHETIC-001",
        operation="RequestOperatingProjection",
        issued_tick=100,
        expires_tick=110,
        nonce="fixture-nonce",
        idempotency_key="fixture-idempotency",
    )
    request = build_request(capability, request_commitment=digest("fixture-request"))
    ledger = AppendOnlyReplayLedger()
    success = SealedIpcAuthorizer(signing_key, ledger).authorize(
        request,
        authenticated_principal_commitment=worker,
        current_tick=101,
        result_commitment=digest("fixture-result"),
    )
    static_receipt = build_static_qualification(config)

    primary_errors = (
        validate_capability(capability, signing_key=signing_key)
        + validate_request(request, signing_key=signing_key)
        + validate_external_receipt(success)
        + validate_replay_ledger(ledger)
    )
    checker_errors = independently_check_static_qualification(config, static_receipt)
    capability_mutations = (
        replace(capability, auth_tag="0" * 64),
        replace(capability, expires_tick=capability.issued_tick),
        replace(capability, contains_raw_principal=True),
        replace(capability, contains_path=True),
        replace(capability, contains_secret=True),
    )
    request_mutations = (
        replace(request, request_id="IPCREQ-forged"),
        replace(request, contains_payload=True),
        replace(request, canonical_write_requested=True),
        replace(request, external_effect_requested=True),
    )
    static_mutations = (
        replace(static_receipt, open_mode=0),
        replace(static_receipt, pipe_mode=0),
        replace(static_receipt, max_instances=2),
        replace(static_receipt, worker_access_mask=0xFFFFFFFF),
        replace(static_receipt, first_instance_required=False),
        replace(static_receipt, remote_clients_rejected=False),
        replace(static_receipt, exact_sid_match_required=False),
        replace(static_receipt, revert_to_self_required=False),
        replace(static_receipt, default_security_descriptor_denied=False),
        replace(static_receipt, raw_sid_disclosed=True),
        replace(static_receipt, live_pipe_created=True),
        replace(static_receipt, live_os_qualified=True),
        replace(static_receipt, physical_isolation_qualified=True),
    )
    detected = sum(
        bool(validate_capability(item, signing_key=signing_key))
        for item in capability_mutations
    )
    detected += sum(
        bool(validate_request(item, signing_key=signing_key))
        for item in request_mutations
    )
    detected += sum(
        bool(independently_check_static_qualification(config, item))
        for item in static_mutations
    )
    mutation_count = len(capability_mutations) + len(request_mutations) + len(static_mutations)
    schema_files = (
        "sealed-ipc-capability-v1.schema.json",
        "sealed-ipc-request-v1.schema.json",
        "secure-pipe-static-qualification-v1.schema.json",
    )
    if primary_errors or checker_errors or detected != mutation_count:
        raise ValueError("c023_secure_ipc_fixture_invalid")
    return {
        "schema": "design_c_c023_secure_ipc_public_summary_v1",
        "contract_revisions": {
            "portable_core": SEALED_IPC_CORE_REVISION,
            "primary_validator": SEALED_IPC_VALIDATOR_REVISION,
            "windows_adapter": WINDOWS_SECURE_PIPE_ADAPTER_REVISION,
            "independent_checker": WINDOWS_SECURE_PIPE_CHECKER_REVISION,
        },
        "aggregate_counts": {
            "operation_count": 3,
            "schema_count": len(schema_files),
            "mutation_count": mutation_count,
            "detected_mutation_count": detected,
            "max_frame_bytes": MAX_FRAME_BYTES,
            "live_pipe_api_call_count": 0,
        },
        "validated_contracts": {
            "capability_signature_and_authority_bound": True,
            "principal_commitment_bound_to_authenticated_sid": True,
            "bounded_canonical_framing_required": True,
            "replay_and_idempotency_ledger_present": True,
            "generic_worker_denial_with_sealed_reason": True,
            "first_instance_and_remote_denial_flags_pinned": True,
            "protected_explicit_dacl_required": True,
            "client_token_impersonation_and_exact_sid_check_required": True,
            "revert_to_self_and_handle_cleanup_required": True,
            "primary_validator_passed": not primary_errors,
            "independent_checker_passed": not checker_errors,
            "all_mutations_detected": detected == mutation_count,
            "all_schema_files_present": all((ROOT / "schemas" / name).is_file() for name in schema_files),
        },
        "qualification_boundaries": {
            "implementation_present": True,
            "static_and_fake_backend_qualified": True,
            "live_pipe_created": False,
            "live_os_probe_pending": True,
            "c020_gap_ipc_still_blocking": True,
            "host_mutation_authorized": False,
            "physical_isolation_qualified": False,
            "canonical_activation_authorized": False,
            "unattended_execution_authorized": False,
            "external_effects": False,
        },
        "contains_pipe_name": False,
        "contains_sids": False,
        "contains_principal_commitments": False,
        "contains_capability_or_request_ids": False,
        "contains_signing_key": False,
        "contains_runtime_root": False,
        "contains_secrets": False,
        "nonjoinable": True,
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "summary.json").write_text(
        json.dumps(build_summary(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
