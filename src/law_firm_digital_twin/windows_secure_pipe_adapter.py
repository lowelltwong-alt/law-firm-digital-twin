from __future__ import annotations

import ctypes
import re
import sys
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable, Literal, Protocol

from .hashio import digest
from .sealed_ipc_protocol import MAX_FRAME_BYTES, principal_commitment


WINDOWS_SECURE_PIPE_ADAPTER_REVISION = "windows-secure-pipe-adapter-g0-v1"

PIPE_ACCESS_DUPLEX = 0x00000003
FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000
PIPE_TYPE_MESSAGE = 0x00000004
PIPE_READMODE_MESSAGE = 0x00000002
PIPE_WAIT = 0x00000000
PIPE_REJECT_REMOTE_CLIENTS = 0x00000008

PIPE_OPEN_MODE = PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE
PIPE_MODE = (
    PIPE_TYPE_MESSAGE
    | PIPE_READMODE_MESSAGE
    | PIPE_WAIT
    | PIPE_REJECT_REMOTE_CLIENTS
)
MAX_PIPE_INSTANCES = 1
PIPE_BUFFER_BYTES = MAX_FRAME_BYTES + 4
PIPE_DEFAULT_TIMEOUT_MS = 5_000

# FILE_READ_DATA | FILE_WRITE_DATA | FILE_READ_ATTRIBUTES |
# FILE_WRITE_ATTRIBUTES | READ_CONTROL | SYNCHRONIZE. This intentionally does
# not grant FILE_APPEND_DATA/FILE_CREATE_PIPE_INSTANCE.
WORKER_PIPE_ACCESS_MASK = 0x00120183

_SID = re.compile(r"^S-1-(?:\d+-){1,14}\d+$")
_PIPE = re.compile(r"^\\\\\.\\pipe\\[A-Za-z0-9._-]{1,128}$")


@dataclass(frozen=True)
class RuntimePrivatePipeConfig:
    pipe_name: str
    kernel_sid: str
    worker_sid: str
    max_frame_bytes: int = MAX_FRAME_BYTES


@dataclass(frozen=True)
class SecurePipeStaticQualification:
    qualification_id: str
    revision: Literal["windows-secure-pipe-adapter-g0-v1"]
    pipe_name_commitment: str
    kernel_principal_commitment: str
    worker_principal_commitment: str
    open_mode: int
    pipe_mode: int
    max_instances: int
    buffer_bytes: int
    worker_access_mask: int
    first_instance_required: Literal[True]
    remote_clients_rejected: Literal[True]
    message_mode_required: Literal[True]
    client_token_impersonation_required: Literal[True]
    exact_sid_match_required: Literal[True]
    revert_to_self_required: Literal[True]
    default_security_descriptor_denied: Literal[True]
    raw_sid_disclosed: Literal[False]
    pipe_name_disclosed: Literal[False]
    live_pipe_created: Literal[False]
    live_os_qualified: Literal[False]
    physical_isolation_qualified: Literal[False]
    canonical_activation_authorized: Literal[False]
    external_effects: Literal[False]
    portable_class: Literal["runtime_adapter"]

    @property
    def qualification_hash(self) -> str:
        return digest(self)


class WindowsPipeApi(Protocol):
    def current_process_sid(self) -> str: ...
    def security_descriptor_from_sddl(self, sddl: str) -> object: ...
    def free_security_descriptor(self, descriptor: object) -> None: ...
    def create_first_instance(
        self,
        *,
        pipe_name: str,
        open_mode: int,
        pipe_mode: int,
        max_instances: int,
        buffer_bytes: int,
        timeout_ms: int,
        security_descriptor: object,
    ) -> object: ...
    def connect(self, pipe_handle: object) -> None: ...
    def read_frame(self, pipe_handle: object, max_frame_bytes: int) -> bytes: ...
    def authenticated_client_sid(self, pipe_handle: object) -> str: ...
    def write_frame(self, pipe_handle: object, frame: bytes) -> None: ...
    def disconnect(self, pipe_handle: object) -> None: ...
    def close_handle(self, handle: object) -> None: ...


def validate_runtime_private_pipe_config(config: RuntimePrivatePipeConfig) -> None:
    if type(config) is not RuntimePrivatePipeConfig:
        raise TypeError("secure_pipe_config_type_denied")
    if not _PIPE.fullmatch(config.pipe_name):
        raise ValueError("secure_pipe_name_invalid")
    if not _SID.fullmatch(config.kernel_sid) or not _SID.fullmatch(config.worker_sid):
        raise ValueError("secure_pipe_sid_invalid")
    if config.kernel_sid == config.worker_sid:
        raise ValueError("secure_pipe_identity_separation_required")
    if config.max_frame_bytes <= 0 or config.max_frame_bytes > MAX_FRAME_BYTES:
        raise ValueError("secure_pipe_frame_limit_invalid")


def build_pipe_sddl(config: RuntimePrivatePipeConfig) -> str:
    validate_runtime_private_pipe_config(config)
    # Protected DACL: LocalSystem, Administrators, and the kernel identity have
    # full control; the worker receives only the explicit client access mask.
    return (
        f"O:{config.kernel_sid}G:{config.kernel_sid}D:P"
        f"(A;;GA;;;SY)(A;;GA;;;BA)(A;;GA;;;{config.kernel_sid})"
        f"(A;;0x{WORKER_PIPE_ACCESS_MASK:08x};;;{config.worker_sid})"
    )


def build_static_qualification(
    config: RuntimePrivatePipeConfig,
) -> SecurePipeStaticQualification:
    validate_runtime_private_pipe_config(config)
    payload = {
        "revision": WINDOWS_SECURE_PIPE_ADAPTER_REVISION,
        "pipe_name_commitment": digest(config.pipe_name),
        "kernel_principal_commitment": principal_commitment(config.kernel_sid),
        "worker_principal_commitment": principal_commitment(config.worker_sid),
        "open_mode": PIPE_OPEN_MODE,
        "pipe_mode": PIPE_MODE,
        "max_instances": MAX_PIPE_INSTANCES,
        "buffer_bytes": PIPE_BUFFER_BYTES,
        "worker_access_mask": WORKER_PIPE_ACCESS_MASK,
    }
    return SecurePipeStaticQualification(
        qualification_id="SPQ-" + digest(payload)[:24],
        **payload,
        first_instance_required=True,
        remote_clients_rejected=True,
        message_mode_required=True,
        client_token_impersonation_required=True,
        exact_sid_match_required=True,
        revert_to_self_required=True,
        default_security_descriptor_denied=True,
        raw_sid_disclosed=False,
        pipe_name_disclosed=False,
        live_pipe_created=False,
        live_os_qualified=False,
        physical_isolation_qualified=False,
        canonical_activation_authorized=False,
        external_effects=False,
        portable_class="runtime_adapter",
    )


class SecureNamedPipeServer:
    """One-session Windows adapter. Construction has no host effect."""

    def __init__(self, config: RuntimePrivatePipeConfig, api: WindowsPipeApi) -> None:
        validate_runtime_private_pipe_config(config)
        self._config = config
        self._api = api

    def serve_one(
        self,
        processor: Callable[[bytes, str], bytes],
    ) -> Literal["served", "identity_denied"]:
        if self._api.current_process_sid() != self._config.kernel_sid:
            raise PermissionError("secure_pipe_kernel_identity_denied")
        descriptor = self._api.security_descriptor_from_sddl(
            build_pipe_sddl(self._config)
        )
        handle: object | None = None
        connected = False
        try:
            handle = self._api.create_first_instance(
                pipe_name=self._config.pipe_name,
                open_mode=PIPE_OPEN_MODE,
                pipe_mode=PIPE_MODE,
                max_instances=MAX_PIPE_INSTANCES,
                buffer_bytes=PIPE_BUFFER_BYTES,
                timeout_ms=PIPE_DEFAULT_TIMEOUT_MS,
                security_descriptor=descriptor,
            )
            self._api.connect(handle)
            connected = True
            # Only bounded bytes are read before authentication; no parsing or
            # domain action occurs until the client token is verified.
            frame = self._api.read_frame(handle, self._config.max_frame_bytes)
            client_sid = self._api.authenticated_client_sid(handle)
            if client_sid != self._config.worker_sid:
                return "identity_denied"
            response = processor(frame, principal_commitment(client_sid))
            if type(response) is not bytes or len(response) > self._config.max_frame_bytes + 4:
                raise ValueError("secure_pipe_response_frame_invalid")
            self._api.write_frame(handle, response)
            return "served"
        finally:
            if handle is not None:
                if connected:
                    self._api.disconnect(handle)
                self._api.close_handle(handle)
            self._api.free_security_descriptor(descriptor)


class NativeWindowsPipeApi:
    """ctypes Win32 implementation. Instantiate/use only in an authorized wave."""

    ERROR_INSUFFICIENT_BUFFER = 122
    ERROR_MORE_DATA = 234
    ERROR_PIPE_CONNECTED = 535
    TOKEN_QUERY = 0x0008
    TOKEN_USER = 1
    SDDL_REVISION_1 = 1
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    class SECURITY_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ("nLength", wintypes.DWORD),
            ("lpSecurityDescriptor", wintypes.LPVOID),
            ("bInheritHandle", wintypes.BOOL),
        ]

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise OSError("windows_secure_pipe_adapter_requires_windows")
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        self._configure_signatures()

    @staticmethod
    def _raise_last_error(label: str) -> None:
        code = ctypes.get_last_error()
        raise OSError(code, label)

    def _configure_signatures(self) -> None:
        handle_pointer = ctypes.POINTER(wintypes.HANDLE)
        dword_pointer = ctypes.POINTER(wintypes.DWORD)
        self._advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.LPVOID),
            dword_pointer,
        ]
        self._advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
        self._advapi32.OpenProcessToken.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            handle_pointer,
        ]
        self._advapi32.OpenProcessToken.restype = wintypes.BOOL
        self._advapi32.OpenThreadToken.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.BOOL,
            handle_pointer,
        ]
        self._advapi32.OpenThreadToken.restype = wintypes.BOOL
        self._advapi32.GetTokenInformation.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
            dword_pointer,
        ]
        self._advapi32.GetTokenInformation.restype = wintypes.BOOL
        self._advapi32.ConvertSidToStringSidW.argtypes = [
            wintypes.LPVOID,
            ctypes.POINTER(wintypes.LPWSTR),
        ]
        self._advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
        self._advapi32.ImpersonateNamedPipeClient.argtypes = [wintypes.HANDLE]
        self._advapi32.ImpersonateNamedPipeClient.restype = wintypes.BOOL
        self._advapi32.RevertToSelf.argtypes = []
        self._advapi32.RevertToSelf.restype = wintypes.BOOL

        self._kernel32.GetCurrentProcess.argtypes = []
        self._kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        self._kernel32.GetCurrentThread.argtypes = []
        self._kernel32.GetCurrentThread.restype = wintypes.HANDLE
        self._kernel32.LocalFree.argtypes = [wintypes.LPVOID]
        self._kernel32.LocalFree.restype = wintypes.LPVOID
        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel32.CloseHandle.restype = wintypes.BOOL
        self._kernel32.CreateNamedPipeW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(self.SECURITY_ATTRIBUTES),
        ]
        self._kernel32.CreateNamedPipeW.restype = wintypes.HANDLE
        self._kernel32.ConnectNamedPipe.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
        self._kernel32.ConnectNamedPipe.restype = wintypes.BOOL
        self._kernel32.ReadFile.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            wintypes.DWORD,
            dword_pointer,
            wintypes.LPVOID,
        ]
        self._kernel32.ReadFile.restype = wintypes.BOOL
        self._kernel32.WriteFile.argtypes = [
            wintypes.HANDLE,
            wintypes.LPCVOID,
            wintypes.DWORD,
            dword_pointer,
            wintypes.LPVOID,
        ]
        self._kernel32.WriteFile.restype = wintypes.BOOL
        self._kernel32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
        self._kernel32.FlushFileBuffers.restype = wintypes.BOOL
        self._kernel32.DisconnectNamedPipe.argtypes = [wintypes.HANDLE]
        self._kernel32.DisconnectNamedPipe.restype = wintypes.BOOL
    def _sid_from_token(self, token: object) -> str:
        needed = wintypes.DWORD(0)
        self._advapi32.GetTokenInformation(
            token, self.TOKEN_USER, None, 0, ctypes.byref(needed)
        )
        if ctypes.get_last_error() != self.ERROR_INSUFFICIENT_BUFFER or needed.value == 0:
            self._raise_last_error("GetTokenInformation(size)")
        buffer = ctypes.create_string_buffer(needed.value)
        if not self._advapi32.GetTokenInformation(
            token,
            self.TOKEN_USER,
            buffer,
            needed,
            ctypes.byref(needed),
        ):
            self._raise_last_error("GetTokenInformation(value)")
        sid_pointer = ctypes.cast(buffer, ctypes.POINTER(wintypes.LPVOID))[0]
        sid_string = wintypes.LPWSTR()
        if not self._advapi32.ConvertSidToStringSidW(
            sid_pointer, ctypes.byref(sid_string)
        ):
            self._raise_last_error("ConvertSidToStringSidW")
        try:
            return sid_string.value
        finally:
            self._kernel32.LocalFree(sid_string)

    def current_process_sid(self) -> str:
        token = wintypes.HANDLE()
        if not self._advapi32.OpenProcessToken(
            self._kernel32.GetCurrentProcess(), self.TOKEN_QUERY, ctypes.byref(token)
        ):
            self._raise_last_error("OpenProcessToken")
        try:
            return self._sid_from_token(token)
        finally:
            self.close_handle(token)

    def security_descriptor_from_sddl(self, sddl: str) -> object:
        descriptor = wintypes.LPVOID()
        size = wintypes.DWORD(0)
        if not self._advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl,
            self.SDDL_REVISION_1,
            ctypes.byref(descriptor),
            ctypes.byref(size),
        ):
            self._raise_last_error("ConvertStringSecurityDescriptorToSecurityDescriptorW")
        return descriptor

    def free_security_descriptor(self, descriptor: object) -> None:
        self._kernel32.LocalFree(descriptor)

    def create_first_instance(self, **kwargs: object) -> object:
        attributes = self.SECURITY_ATTRIBUTES(
            ctypes.sizeof(self.SECURITY_ATTRIBUTES),
            kwargs["security_descriptor"],
            False,
        )
        handle = self._kernel32.CreateNamedPipeW(
            kwargs["pipe_name"],
            kwargs["open_mode"],
            kwargs["pipe_mode"],
            kwargs["max_instances"],
            kwargs["buffer_bytes"],
            kwargs["buffer_bytes"],
            kwargs["timeout_ms"],
            ctypes.byref(attributes),
        )
        if handle == self.INVALID_HANDLE_VALUE:
            self._raise_last_error("CreateNamedPipeW")
        return handle

    def connect(self, pipe_handle: object) -> None:
        if not self._kernel32.ConnectNamedPipe(pipe_handle, None):
            if ctypes.get_last_error() != self.ERROR_PIPE_CONNECTED:
                self._raise_last_error("ConnectNamedPipe")

    def _read_exact(self, handle: object, size: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            remaining = size - len(chunks)
            buffer = ctypes.create_string_buffer(remaining)
            read = wintypes.DWORD(0)
            ok = self._kernel32.ReadFile(
                handle, buffer, remaining, ctypes.byref(read), None
            )
            error = ctypes.get_last_error()
            if not ok and error != self.ERROR_MORE_DATA:
                self._raise_last_error("ReadFile")
            if read.value == 0:
                raise OSError("named_pipe_unexpected_eof")
            chunks.extend(buffer.raw[: read.value])
        return bytes(chunks)

    def read_frame(self, pipe_handle: object, max_frame_bytes: int) -> bytes:
        header = self._read_exact(pipe_handle, 4)
        size = int.from_bytes(header, "big")
        if size <= 0 or size > max_frame_bytes:
            raise ValueError("secure_pipe_inbound_frame_size_denied")
        return header + self._read_exact(pipe_handle, size)

    def authenticated_client_sid(self, pipe_handle: object) -> str:
        if not self._advapi32.ImpersonateNamedPipeClient(pipe_handle):
            self._raise_last_error("ImpersonateNamedPipeClient")
        token = wintypes.HANDLE()
        try:
            if not self._advapi32.OpenThreadToken(
                self._kernel32.GetCurrentThread(),
                self.TOKEN_QUERY,
                True,
                ctypes.byref(token),
            ):
                self._raise_last_error("OpenThreadToken")
            return self._sid_from_token(token)
        finally:
            if token:
                self.close_handle(token)
            if not self._advapi32.RevertToSelf():
                self._raise_last_error("RevertToSelf")

    def write_frame(self, pipe_handle: object, frame: bytes) -> None:
        written = wintypes.DWORD(0)
        if not self._kernel32.WriteFile(
            pipe_handle, frame, len(frame), ctypes.byref(written), None
        ) or written.value != len(frame):
            self._raise_last_error("WriteFile")

    def disconnect(self, pipe_handle: object) -> None:
        self._kernel32.FlushFileBuffers(pipe_handle)
        self._kernel32.DisconnectNamedPipe(pipe_handle)

    def close_handle(self, handle: object) -> None:
        self._kernel32.CloseHandle(handle)
