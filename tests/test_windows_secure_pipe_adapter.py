from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest

from law_firm_digital_twin.sealed_ipc_protocol import encode_frame
from law_firm_digital_twin.windows_secure_pipe_adapter import (
    FILE_FLAG_FIRST_PIPE_INSTANCE,
    PIPE_MODE,
    PIPE_OPEN_MODE,
    PIPE_REJECT_REMOTE_CLIENTS,
    WORKER_PIPE_ACCESS_MASK,
    RuntimePrivatePipeConfig,
    SecureNamedPipeServer,
    build_pipe_sddl,
    build_static_qualification,
)
from law_firm_digital_twin.windows_secure_pipe_qualification import (
    independently_check_static_qualification,
)


KERNEL = "S-1-5-21-100-200-300-1101"
WORKER = "S-1-5-21-100-200-300-1102"


def _config() -> RuntimePrivatePipeConfig:
    return RuntimePrivatePipeConfig(
        pipe_name=r"\\.\pipe\lfdt-kernel-g0",
        kernel_sid=KERNEL,
        worker_sid=WORKER,
    )


class FakeApi:
    def __init__(self, *, process_sid: str = KERNEL, client_sid: str = WORKER) -> None:
        self.process_sid = process_sid
        self.client_sid = client_sid
        self.calls: list[object] = []
        self.frame = encode_frame({"request_commitment": "0" * 64})

    def current_process_sid(self) -> str:
        self.calls.append("current_process_sid")
        return self.process_sid

    def security_descriptor_from_sddl(self, sddl: str) -> object:
        self.calls.append(("security_descriptor", sddl))
        return "descriptor"

    def free_security_descriptor(self, descriptor: object) -> None:
        self.calls.append(("free_security_descriptor", descriptor))

    def create_first_instance(self, **kwargs: object) -> object:
        self.calls.append(("create_first_instance", kwargs))
        return "handle"

    def connect(self, pipe_handle: object) -> None:
        self.calls.append(("connect", pipe_handle))

    def read_frame(self, pipe_handle: object, max_frame_bytes: int) -> bytes:
        self.calls.append(("read_frame", pipe_handle, max_frame_bytes))
        return self.frame

    def authenticated_client_sid(self, pipe_handle: object) -> str:
        self.calls.append(("authenticated_client_sid", pipe_handle))
        return self.client_sid

    def write_frame(self, pipe_handle: object, frame: bytes) -> None:
        self.calls.append(("write_frame", pipe_handle, frame))

    def disconnect(self, pipe_handle: object) -> None:
        self.calls.append(("disconnect", pipe_handle))

    def close_handle(self, handle: object) -> None:
        self.calls.append(("close_handle", handle))


def test_static_qualification_pins_flags_dacl_and_nonqualification() -> None:
    config = _config()
    receipt = build_static_qualification(config)
    assert independently_check_static_qualification(config, receipt) == ()
    assert receipt.open_mode & FILE_FLAG_FIRST_PIPE_INSTANCE
    assert receipt.pipe_mode & PIPE_REJECT_REMOTE_CLIENTS
    assert receipt.live_pipe_created is False
    assert receipt.live_os_qualified is False
    assert receipt.physical_isolation_qualified is False
    assert KERNEL not in repr(receipt)
    assert WORKER not in repr(receipt)

    sddl = build_pipe_sddl(config)
    assert sddl.startswith(f"O:{KERNEL}G:{KERNEL}D:P")
    assert f"(A;;0x{WORKER_PIPE_ACCESS_MASK:08x};;;{WORKER})" in sddl
    assert ";;;WD)" not in sddl
    assert ";;;AN)" not in sddl


def test_fake_runtime_authenticates_before_processing_and_uses_exact_flags() -> None:
    api = FakeApi()
    processed: list[tuple[bytes, str]] = []
    server = SecureNamedPipeServer(_config(), api)
    status = server.serve_one(
        lambda frame, principal: (
            processed.append((frame, principal)) or encode_frame({"disposition": "DENIED"})
        )
    )
    assert status == "served"
    assert len(processed) == 1
    create = next(item for item in api.calls if isinstance(item, tuple) and item[0] == "create_first_instance")
    assert create[1]["open_mode"] == PIPE_OPEN_MODE
    assert create[1]["pipe_mode"] == PIPE_MODE
    assert api.calls.index(("authenticated_client_sid", "handle")) < next(
        index for index, call in enumerate(api.calls) if isinstance(call, tuple) and call[0] == "write_frame"
    )
    assert api.calls[-3:] == [
        ("disconnect", "handle"),
        ("close_handle", "handle"),
        ("free_security_descriptor", "descriptor"),
    ]


def test_wrong_kernel_never_creates_pipe_and_wrong_client_gets_no_response() -> None:
    wrong_kernel = FakeApi(process_sid=WORKER)
    with pytest.raises(PermissionError, match="kernel_identity_denied"):
        SecureNamedPipeServer(_config(), wrong_kernel).serve_one(lambda *_: b"unused")
    assert wrong_kernel.calls == ["current_process_sid"]

    wrong_client = FakeApi(client_sid="S-1-5-21-100-200-300-9999")
    invoked = False

    def processor(*_: object) -> bytes:
        nonlocal invoked
        invoked = True
        return b"should-not-run"

    assert SecureNamedPipeServer(_config(), wrong_client).serve_one(processor) == "identity_denied"
    assert invoked is False
    assert not any(isinstance(call, tuple) and call[0] == "write_frame" for call in wrong_client.calls)


def test_checker_catches_security_and_authority_mutations() -> None:
    config = _config()
    receipt = build_static_qualification(config)
    hostile = (
        replace(receipt, open_mode=receipt.open_mode ^ FILE_FLAG_FIRST_PIPE_INSTANCE),
        replace(receipt, pipe_mode=receipt.pipe_mode ^ PIPE_REJECT_REMOTE_CLIENTS),
        replace(receipt, worker_access_mask=0xFFFFFFFF),
        replace(receipt, live_os_qualified=True),  # type: ignore[arg-type]
        replace(receipt, raw_sid_disclosed=True),  # type: ignore[arg-type]
    )
    assert all(independently_check_static_qualification(config, item) for item in hostile)


def test_no_script_or_fixture_can_create_or_connect_a_live_pipe() -> None:
    root = Path(__file__).resolve().parents[1]
    candidate_paths = tuple((root / "scripts").glob("*.py")) + tuple((root / "tests").glob("*.py"))
    forbidden_names = {"NativeWindowsPipeApi", "CreateNamedPipeW", "ConnectNamedPipe"}
    for path in candidate_paths:
        if path.name == Path(__file__).name:
            continue
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=str(path))
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        called.update(
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        )
        assert not (called & forbidden_names), path
