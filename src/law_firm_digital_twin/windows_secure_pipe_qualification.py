from __future__ import annotations

from .hashio import digest
from .sealed_ipc_protocol import principal_commitment
from .windows_secure_pipe_adapter import (
    FILE_FLAG_FIRST_PIPE_INSTANCE,
    MAX_PIPE_INSTANCES,
    PIPE_ACCESS_DUPLEX,
    PIPE_BUFFER_BYTES,
    PIPE_MODE,
    PIPE_OPEN_MODE,
    PIPE_READMODE_MESSAGE,
    PIPE_REJECT_REMOTE_CLIENTS,
    PIPE_TYPE_MESSAGE,
    WINDOWS_SECURE_PIPE_ADAPTER_REVISION,
    WORKER_PIPE_ACCESS_MASK,
    RuntimePrivatePipeConfig,
    SecurePipeStaticQualification,
    build_pipe_sddl,
)


WINDOWS_SECURE_PIPE_CHECKER_REVISION = "windows-secure-pipe-checker-g0-v1"


def independently_check_static_qualification(
    config: RuntimePrivatePipeConfig,
    receipt: SecurePipeStaticQualification,
) -> tuple[str, ...]:
    errors: list[str] = []
    expected_payload = {
        "revision": WINDOWS_SECURE_PIPE_ADAPTER_REVISION,
        "pipe_name_commitment": digest(config.pipe_name),
        "kernel_principal_commitment": principal_commitment(config.kernel_sid),
        "worker_principal_commitment": principal_commitment(config.worker_sid),
        "open_mode": PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE,
        "pipe_mode": PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_REJECT_REMOTE_CLIENTS,
        "max_instances": 1,
        "buffer_bytes": 65_540,
        "worker_access_mask": 0x00120183,
    }
    expected_id = "SPQ-" + digest(expected_payload)[:24]
    if (
        receipt.qualification_id != expected_id
        or receipt.revision != WINDOWS_SECURE_PIPE_ADAPTER_REVISION
        or receipt.pipe_name_commitment != expected_payload["pipe_name_commitment"]
        or receipt.kernel_principal_commitment != expected_payload["kernel_principal_commitment"]
        or receipt.worker_principal_commitment != expected_payload["worker_principal_commitment"]
    ):
        errors.append("WSP-001:qualification_binding_invalid")
    if (
        PIPE_OPEN_MODE != expected_payload["open_mode"]
        or PIPE_MODE != expected_payload["pipe_mode"]
        or MAX_PIPE_INSTANCES != expected_payload["max_instances"]
        or PIPE_BUFFER_BYTES != expected_payload["buffer_bytes"]
        or WORKER_PIPE_ACCESS_MASK != expected_payload["worker_access_mask"]
        or receipt.open_mode != expected_payload["open_mode"]
        or receipt.pipe_mode != expected_payload["pipe_mode"]
        or receipt.max_instances != expected_payload["max_instances"]
        or receipt.buffer_bytes != expected_payload["buffer_bytes"]
        or receipt.worker_access_mask != expected_payload["worker_access_mask"]
    ):
        errors.append("WSP-002:security_flags_or_limits_invalid")
    if (
        not receipt.first_instance_required
        or not receipt.remote_clients_rejected
        or not receipt.message_mode_required
        or not receipt.client_token_impersonation_required
        or not receipt.exact_sid_match_required
        or not receipt.revert_to_self_required
        or not receipt.default_security_descriptor_denied
    ):
        errors.append("WSP-003:security_invariant_invalid")
    if (
        receipt.raw_sid_disclosed
        or receipt.pipe_name_disclosed
        or receipt.live_pipe_created
        or receipt.live_os_qualified
        or receipt.physical_isolation_qualified
        or receipt.canonical_activation_authorized
        or receipt.external_effects
        or receipt.portable_class != "runtime_adapter"
    ):
        errors.append("WSP-004:authority_or_disclosure_overclaim")
    sddl = build_pipe_sddl(config)
    if (
        "D:P" not in sddl
        or "(A;;GA;;;SY)" not in sddl
        or "(A;;GA;;;BA)" not in sddl
        or f"(A;;0x00120183;;;{config.worker_sid})" not in sddl
        or "WD" in sddl
        or "AN" in sddl
    ):
        errors.append("WSP-005:sddl_policy_invalid")
    return tuple(errors)
