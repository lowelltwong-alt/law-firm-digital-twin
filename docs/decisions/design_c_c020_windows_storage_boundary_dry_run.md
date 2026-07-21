# Design C C020 Windows Storage Boundary Dry-Run Decision

Date: 2026-07-18  
Status: dry-run contract tests passed; physical provisioning not authorized or performed

## Decision

The smallest meaningful Windows boundary uses three distinct local OS identities:
`LFDT-SealedKernel`, `LFDT-Worker`, and `LFDT-OperatingAuditor`. HMAC-derived
identifiers are correlation controls only; they are not access control. The
sealed identity alone may receive the sealed key, open sealed stores and
crosswalks, or write the canonical operating projection. The worker may read the
operating projection and write only its ingress, workspace, and bounded staging
surfaces. The auditor reads operating surfaces and writes only quarantine and
audit-report surfaces. It receives no sealed access.

The portable contract defines 26 root/parent/leaf path intents across sealed,
operating, ingress, workspace, staging, and audit zones. The runtime root and
every intermediate parent and leaf require inheritance to be broken. Broad
grants such as Everyone, Users, and Authenticated Users must be removed. SYSTEM
and Administrators are explicit host trusted-computing-base exceptions. The
worker receives no execute grant and no mutation grant to canonical operating,
quarantine, audit, key, crosswalk, replay-ledger, or sealed-intake paths.

Kernel interaction is a typed, capability-scoped local-IPC contract bound to the
authenticated Windows SID, opaque operating matter, allowed operation, expiry,
nonce, idempotency key, and replay ledger. The pipe security intent makes the
kernel its owner and the worker its only LFDT client, rejects remote and
unapproved identities, requires first-instance creation and token inspection,
and mandates post-provision denial probes. Generic SQL, arbitrary file
reads/writes, path passthrough, sealed-identifier lookup, key/crosswalk export,
world-truth labels, raw exception passthrough, and debug shells are forbidden.
Externally every rejection is `DENIED`; precise reasons remain only in the
kernel-owned sealed replay ledger.

Every privileged read of a worker- or auditor-writable surface is governed by a
per-open handle policy: do not follow reparse points; reject every reparse tag
and alternate data stream; verify the final handle path remains inside both the
approved root and bound surface; verify stable object identity; hash after
opening; and copy bytes from that same still-open verified handle into kernel-only sealed intake before validation or admission. An atomic receipt binds source object identity, source hash, sealed-intake hash, policy revision, consumer role, and kernel ledger tick; only the sealed copy may be admitted.
One-time startup scanning and direct admission from the original path are
prohibited.

The qualification key-vault intent uses DPAPI current-user scope bound to the
resolved kernel SID. The sealed service profile must be loaded, and a fresh
process under that SID must prove protect/unprotect. Plaintext-at-rest, export,
logging, provider fallback, and backup before H-12 are forbidden. H-12 continuity
remains unqualified.

## Dry-run evidence

The Windows adapter builds a non-executing provisioning plan from the H-10-bound
`LFDT_RUNTIME_ROOT` selection. It rejects relative, UNC/device, synced,
traversal, alternate-data-stream, reserved-device, expandable, and wrong-root
forms. Hostile tests mutate sealed grants, parent/surface coverage, capability
scope, denial behavior, root commitment, account alias, Windows rights, host TCB,
identity posture, pipe policy, key storage, per-open path safety, provisioning
flags, and canonical authority; all are rejected.

The checked-in public summary contains only aggregate requirements. It excludes
the selected root, root commitment, account aliases/SIDs, plan hash, keys,
passwords, and case data. The dry run created no runtime-root directory and
performed no account, logon-right, DACL, service, pipe, key, database, backup, or
canonical operation.

## Provisioning gate

Physical qualification requires a separately authorized Windows provisioning
wave, resolved distinct local non-admin SIDs, exact post-provisioning effective
ACL and ancestor observations, service-profile and DPAPI fresh-process proof,
pipe security and token-authentication probes, denial probes executed as every
nonclient identity, per-open reparse-race tests, sealed-canary probes across every
real operating surface, restart and recovery drills, a separately selected
backup location with restore evidence, and a human activation decision.

Any later claim is limited to configured-identity isolation. It is not
administrator resistance, legal compliance, backup recovery, production
readiness, or canonical activation.