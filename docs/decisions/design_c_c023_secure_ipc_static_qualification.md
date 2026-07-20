# Design C C023 Secure IPC Static Qualification

Date: 2026-07-18

Status: portable protocol and Windows runtime adapter implemented; static and
fake-backend checks pass; live named-pipe and cross-identity qualification are
still pending and unauthorized

## Decision

Implement the first runtime component behind `C020-GAP-IPC` without creating or
connecting a live named pipe. The result has two replaceable layers:

1. `sealed_ipc_protocol.py` is the provider-neutral capability, request,
   canonical framing, generic-denial, idempotency, and append-only sealed replay
   contract.
2. `windows_secure_pipe_adapter.py` is a Windows adapter behind an injectable
   API interface. It includes the real Win32 call path, but current evidence
   exercises it only through a deterministic fake backend.

This is an implementation milestone, not physical-isolation evidence. The C020
IPC gap remains blocking until an explicitly authorized qualification wave
creates the planned identities and qualification-only pipe, observes its DACL,
proves approved-client success and all other-identity denial, verifies token
identity and replay behavior in fresh processes, and tears everything down.

## Provider-neutral protocol

Capabilities bind an authenticated-principal commitment, one operating matter,
one of three exact operations, an integer validity interval, nonce,
idempotency key, and HMAC authentication tag. Requests contain commitments, not
document bodies, paths, sealed identifiers, crosswalks, keys, or world-truth
labels. The three operations are:

- `SubmitIngressCommitment`;
- `RequestOperatingProjection`; and
- `AcknowledgeOutboxItem`.

HMAC authenticates capability bytes; it is not access control. Authorization
also requires the Windows adapter to establish the calling process identity and
the connected client's token SID. Every worker-visible denial is exactly
`DENIED` with no reason, identity, path, or secret. The sealed replay ledger
retains the internal reason: expired, replayed, invalid request, identity
mismatch, or authority mismatch.

Frames are canonical JSON with a four-byte big-endian length prefix and a
65,536-byte payload ceiling. Noncanonical, truncated, mismatched-length,
non-object, invalid-UTF-8, and oversized frames fail closed.

## Windows security invariants

The server must run as the planned kernel SID. It uses a protected explicit
DACL, never the default named-pipe security descriptor. LocalSystem,
Administrators, and the kernel identity are trusted-computing-base principals;
the worker receives the explicit client mask `0x00120183`, which deliberately
omits `FILE_APPEND_DATA`/`FILE_CREATE_PIPE_INSTANCE`.

The server pins:

- `PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE`;
- message type and message read mode;
- blocking wait mode;
- `PIPE_REJECT_REMOTE_CLIENTS`;
- one pipe instance; and
- bounded input and output buffers.

After a bounded frame is read, the server calls
`ImpersonateNamedPipeClient`, opens the thread token, obtains `TokenUser`, and
requires an exact match to the planned worker SID. No request parsing or domain
action occurs before that identity check. Impersonation is always ended with
`RevertToSelf`; pipe, token, and security-descriptor resources are released on
all paths. A wrong client is disconnected without a detailed response.

Microsoft states that a null security descriptor grants default named-pipe
access including read access to Everyone and anonymous users, so it is denied
here. Microsoft also warns that `FILE_GENERIC_WRITE` includes the identically
valued `FILE_CREATE_PIPE_INSTANCE` right for named pipes, which is why the
worker ACE uses individual rights. `FILE_FLAG_FIRST_PIPE_INSTANCE` rejects a
second creator, and `PIPE_REJECT_REMOTE_CLIENTS` rejects remote connections.
Microsoft further warns that a failed impersonation leaves the server in its
own security context; therefore failure is terminal and no client action may be
executed.

The reference uses synchronous single-session calls. Before any live use, the
qualification wave must add and prove a bounded process lease or an overlapped
I/O deadline/termination strategy; the CreateNamedPipeW default timeout is not
a server read/connect timeout. No resident service or unattended listener is
qualified by C023.

Primary references:

- https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-createnamedpipew
- https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-security-and-access-rights
- https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-impersonatenamedpipeclient
- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation
- https://learn.microsoft.com/en-us/windows/win32/api/sddl/nf-sddl-convertstringsecuritydescriptortosecuritydescriptorw

## Qualification evidence

The focused C023 slice passes 15 tests. The public fixture catches 22 protocol,
security-flag, DACL-policy, disclosure, and authority mutations. Tests cover
capability/request binding, exact duplicate behavior, conflicting replay,
generic denials with sealed reasons, bounded canonical framing, wrong-kernel
and wrong-client denial, cleanup, schema parity, static flag/DACL checks, and a
repository-wide AST guard that finds live native pipe calls in scripts or
fixtures.

The checked-in public summary contains no pipe name, SID, principal commitment,
capability/request ID, signing key, runtime root, secret, or joinable host value.
Its synthetic fixture key and identities are test-only and are never emitted.

## Portability and rerun boundary

- Capability, request, framing, replay, and primary validation:
  `portable_core`.
- Win32 named-pipe implementation and SDDL policy: `runtime_adapter`.
- Fake-backend and mutation results: static implementation evidence only.
- A future live receipt: environment-bound evidence that expires and never
  becomes a portable truth claim.

Rerun the full affected check if operation, frame, capability, replay, denial,
identity, DACL, access-mask, Win32 API, runtime, privacy, authority, or physical
topology changes. Runtime/model/provider changes cannot inherit this evidence
without requalification.

## Evidence

- `src/law_firm_digital_twin/sealed_ipc_protocol.py`
- `src/law_firm_digital_twin/sealed_ipc_validator.py`
- `src/law_firm_digital_twin/windows_secure_pipe_adapter.py`
- `src/law_firm_digital_twin/windows_secure_pipe_qualification.py`
- `schemas/sealed-ipc-capability-v1.schema.json`
- `schemas/sealed-ipc-request-v1.schema.json`
- `schemas/secure-pipe-static-qualification-v1.schema.json`
- `tests/test_sealed_ipc_protocol.py`
- `tests/test_windows_secure_pipe_adapter.py`
- `tests/test_secure_pipe_schemas.py`
- `tests/test_design_c_c023_secure_ipc_public_fixture.py`
- `generated/design-c-c023-secure-ipc-v1/summary.json`

## Mandatory stop

Do not instantiate `NativeWindowsPipeApi`, create or connect the pipe, create
accounts, change DACLs or rights, elevate, write canonical state, or claim
physical isolation without Lowell's explicit authorization for the
qualification-only C020 host wave. S010 and later remain stopped.
