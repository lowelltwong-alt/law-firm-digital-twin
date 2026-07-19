# Law Firm Digital Twin H-10 Qualification-Gate Reconciliation

Date: 2026-07-19  
Status: current decision packet; implementation and independent review required; **host mutation unauthorized**

## Disposition

This packet supersedes all H-10 authorization packets dated 2026-07-18. Those
packets are stale evidence only and grant no authority. C021 and the 2026-07-18
physical-wave runbook remain source evidence and cannot independently authorize
execution. This packet reconciles H-10 with the frozen H-7 baseline, C020,
C021, C022 through C027, C200, C210, and that runbook. It is a decision and readiness record only.
It contains no command and grants no authority to provision, elevate, execute,
tear down, back up, restore, activate, publish, or access an external service.

The safe default remains in force:

> No host mutation is authorized. Implement and independently review every
> blocking runtime component before requesting qualification-only host authority.

## Frozen lineage and source authority

The following approved files remain byte-for-byte frozen in this branch:

- H-7: `docs/decisions/design_c_baseline_v1_adoption.md`, approved SHA-256
  `F4CB567565D3A388FFCD93CEDE9B28528A9ECAC7E92A77194841E6FCD7CE3BA3`.
- C020: `docs/decisions/design_c_c020_windows_storage_boundary_dry_run.md`,
  approved SHA-256
  `37DA9B3DD76E795FA7F337E3916F6E54B5BC792435EACC730AFC88819D8E336A`.

This reconciliation was derived read-only from the following exact source
revisions in the local source-authority repository:

| Source | SHA-256 |
|---|---|
| `docs/decisions/design_c_c021_physical_authorization_packet.md` | `A0006BF4C554AEFE278E2636383CF5622541D1C1ACA318C41F843CD2F30B587A` |
| `docs/decisions/design_c_c022_read_only_host_preflight.md` | `5DFC8B4C10E66D4D2D48A5E67D2B88EEFF64C6CD6D2B1692916F982F1D3097B7` |
| `docs/decisions/design_c_c023_secure_ipc_static_qualification.md` | `0973780740EDBEAB325CE20646CF56E0746B4078EC4C35F7856933427CEAB47E` |
| `docs/decisions/design_c_c024_same_handle_intake_static_qualification.md` | `964895A7B03C19C70B15E6408CFAA4F00D16D803BADC000D7A05788C87B907B3` |
| `docs/decisions/design_c_c025_effective_access_static_qualification.md` | `48F6779590B2CD241D317788942FF148661EF4421151C8B184DBE663D02CBB82` |
| `docs/decisions/design_c_c026_surface_canary_static_qualification.md` | `3D197EC9F8D1E4F623450107059BEA9A1B709EB0C2FBB3178FF4937BBB1D9F03` |
| `docs/decisions/design_c_c027_physical_recovery_static_qualification.md` | `A4ECF54FB2A5F67C18D3B1C2E0145FB2BE3B0A4CC3C37BE2E505B3E4E8F67F93` |
| `docs/decisions/design_c_c200_durable_key_continuity_static_qualification.md` | `F9639399B3CB2581CE13994C31EC4402ED3EC8554BAE06C2843C568B841F4EEB` |
| `docs/decisions/design_c_c210_backup_restore_contract.md` | `ECFB672721CB2861EA18709EB9EB3DC56F1DD692D8FB7A98B980EA4363830FE6` |
| `docs/runbooks/c020_physical_wave_authorization_packet.md` | `6E3713DF05378FD5E753CF976AF670CB399F5EBDECB1051C536C8600A3594D3D` |

If a source revision changes, this packet must be reconciled and independently
reviewed again before it can support a later authorization request.

## Corrected H-10 invariants

1. The runtime layout has exactly **26 total path intents**, including the
   runtime root: one runtime-root intent plus 25 descendant intents. It is not a
   runtime root plus 26 additional surfaces.
2. The machine-specific runtime-root selection belongs only in ignored local
   configuration. No selected host path, alias, account SID, credential, or
   other host identifier may appear in this packet or in public qualification
   evidence. Tracked tests may use an explicitly synthetic placeholder that
   cannot be loaded as the selected runtime root. The source runbook's tracked
   literal is stale, non-executable evidence—not a selected runtime root. Before
   any future host request, a separately authorized runbook revision must
   resolve the exact ignored-local `LFDT_RUNTIME_ROOT` selection at execution
   time, create its 25 descendant path intents, and never embed or emit the
   selected value in tracked or public evidence. Changing the runbook is outside
   this packet's authorized file scope.
3. Qualification uses exactly three distinct, task-created, non-administrator
   identities: sealed kernel, worker, and operating auditor.
4. Only the sealed kernel may hold sealed-world authority. The worker and
   operating auditor must be denied sealed stores, recovery material, protected
   crosswalks, replay ledgers, commit stores, and canonical mutation.
5. A passing fake or static receipt never proves a native Windows boundary.
   Runtime-private evidence must be observed under the actual restricted
   identities and reduced to a privacy-safe, nonjoinable public aggregate.
6. `C020-S060` is a disposable qualification canary only. It cannot satisfy
   H-12 or C200 durable-key continuity.
7. A disposable fixture copy cannot satisfy C210. Backup strategy, separate
   nonsynchronized backup location, retention/deletion policy, recovery medium,
   and clean-room restore remain separately human-gated.
8. Physical qualification cannot silently activate canonical storage or change
   external-effect, scale, spend, release, or data-admission authority.
9. H-7 remains the build-order authority. If physical isolation is qualified,
   the next H-7 obligation is oracle canaries; this packet does not reorder the
   baseline or promote a different next artifact.
10. Any C026 activity inside C020 is boundary-falsification evidence solely for
    H-7 step 2. It does not satisfy, advance, or co-qualify H-7 step 3. Only
    after physical isolation is independently accepted may a separate
    revision-bound wave qualify the mutation oracle-canary obligation.

## Current evidence and blockers

`C020-S000` produced a point-in-time read-only host receipt on 2026-07-18 with
14 passes, one failure, and zero unknowns. The failure records that the process
was not elevated. That receipt expires on 2026-07-25 and must be rerun from the
then-current source revision immediately before any future physical wave. It
does not authorize elevation or mutation.

Eight blocking runtime components remain unimplemented or unqualified:

1. live secured named-pipe creation with explicit DACL, first-instance and
   remote-client controls; peer-token, replay, and denial proof; and a bounded
   process lease or overlapped-I/O deadline and termination strategy proved on
   the selected host;
2. a native same-handle sealed-intake actuator and live reparse-race proof;
3. native final-path, ACL, effective-access, and token observation;
4. a fresh-process cross-identity runner and live denial evidence;
5. native C026 surface providers, canary plant/cleanup, challenge-route exercise,
   and residual scans;
6. a native C027 identity/process/kill/database/key recovery runner and live
   physical-identity recovery evidence;
7. an H-12-selected native durable-key adapter with custody, restart, rotation,
   revocation, recovery, zeroization, destruction, and teardown proof; and
8. a selected C210 backup mechanism with a distinct nonsynchronized backup
   location and clean-room restore evidence.

The first six block the qualification-only physical wave. The seventh and
eighth are later durability waves and do not become authorized merely because
the physical wave passes.

## Gate sequence

| Gate | Required result | Present authority |
|---|---|---|
| `GATE-H10-IMPLEMENTATION-READINESS` | Implement native adapters with injectable effects, fail-closed defaults, deterministic tests, and independent review | Local code/test work only; no live effects |
| `GATE-C020-HOST-MUTATION` | One qualification-only `C020-S010` through `C020-S120` wave, including teardown | Denied |
| `GATE-C020-INDEPENDENT-CHECK` | Independently accept native ACL, denial, IPC, canary, intake, recovery, teardown, and residual evidence | Pending evidence |
| `GATE-H12-DURABLE-KEY` | Select and qualify one C200 strategy under a separate reviewed plan | Denied and unselected |
| `GATE-H10-BACKUP-SELECTION` | Select and qualify one C210 mechanism, separate location, retention/deletion policy, and clean-room restore plan | Denied and unselected |
| `GATE-C020-CANONICAL-ACTIVATION` | Separate final human decision after all prior gates pass | Denied |

No gate may infer, auto-advance, or broaden the next gate.

## Permitted work before a future host request

The current authority permits only repository-local implementation and testing
that has no live effects. Each environment-bound adapter must:

- expose a provider-neutral request/receipt contract and an injectable native
  effects boundary;
- default to `live_effects=false` and reject unclassified or implicit providers;
- contain no hidden live switch, automatic elevation, auto-repair, auto-advance,
  or machine-specific default;
- validate exact target identity, final path, object identity, and attempt count;
- make one attempt per declared operation and stop on unknown evidence;
- support an exact-target teardown plan in the same task manifest;
- keep credentials, keys, SIDs, paths, private evidence, and raw errors out of
  tracked and public artifacts; and
- receive deterministic, mutation, privacy, authority, and independent review.

Completing code or tests does not itself authorize a host wave.

## Readiness criteria for requesting qualification-only host authority

A later H-10 host request may be prepared only after all six physical-wave
runtime blockers above have implementations and independent review. The request
must bind to exact revisions of the frozen lineage and every native adapter,
and must include:

- a fresh passing `C020-S000` receipt with no collision or unknown result;
- an untracked runtime-root selection proven nonsynchronized, local, resolved,
  non-reparse-backed, ADS-safe, and within the approved target boundary;
- the exact 26-path-intent manifest and exactly three task-created identities;
- a predeclared one-attempt sequence for `C020-S010` through `C020-S120`;
- the exact rollback/teardown manifest, target identities, stop conditions, and
  independent-check plan;
- confirmation that the same authorization wave necessarily executes mandatory
  teardown at `C020-S120`, whether earlier probes pass or fail;
- proof that the implementer and independent checker are distinct; and
- explicit exclusions for H-12, backup/restore, canonical activation, external
  services, real or public case data, publication, deployment, and spend.

Only Lowell may grant that future qualification-only host authority. This
packet deliberately provides no approval phrase because the prerequisites are
not satisfied.

## Mandatory same-wave teardown

Any future authorization for `C020-S010` through `C020-S110` must also authorize
and require `C020-S120` teardown in the **same qualification wave**. Teardown is
not an optional later approval and cannot be omitted after a failed probe.

The future implementation must predeclare exact task-created resources and may
remove only those resources after re-resolving each target. It must stop bounded
processes and endpoints, destroy qualification-only key material, remove only
task-created rights, grants, directories, and identities, preserve only
privacy-safe receipts, and prove no residual access or task-created resource
remains. It must never delete, take ownership of, merge with, or modify a
preexisting account, path, grant, key, database, backup, service, or endpoint.

An unsafe target, changed manifest, collision, ambiguous ownership, failed
cleanup, or residual access is a qualification failure and an immediate stop.
It does not broaden cleanup authority.

## Evidence required from a later physical wave

A passing independently checked receipt must bind to:

- distinct non-admin SIDs and effective logon-right observations;
- ancestor, root, container, leaf, and effective-access matrices for all 26 path
  intents under all three identities;
- live pipe ownership, first-instance, remote rejection, peer-token, replay,
  expiry, wrong-client, and generic-denial observations;
- same-handle copy/hash and reparse, ADS, final-path, and file-identity race
  observations;
- worker and auditor denials produced by fresh processes;
- C026 canary placement, challenge-route, cleanup, and residual scans;
- all seven C027 crash points, wrong-key failure, exactly-once duplicate delivery,
  handle release, and physical-identity recovery observations; and
- `C020-S120` teardown and residual-access observations.

Unknown, stale, substituted, aggregate-only, fake-backend, or reused-process
evidence fails. No partial pass is permitted.

## Mandatory stops and non-authorizations

Stop before any elevation, account or right creation, path or ACL mutation, live
pipe, key operation, process drill, canary, database access, backup, restore,
teardown, external-service access, or canonical activation unless a later exact
human authorization covers the qualified implementation and task manifest.

This packet does **not** authorize:

- host mutation, including qualification provisioning or teardown;
- installation of a service, scheduled task, firewall rule, network share,
  registry-wide policy, persistent endpoint, or unattended runner;
- selection or use of a C200 durable-key strategy, TPM, DPAPI, CNG, KMS, or HSM;
- selection or use of a C210 backup location, mechanism, retention/deletion
  policy, clean-room restore, or external backup service;
- canonical storage, real client data, PACER purchases, raw emails, live court
  data ingestion, native export, public release, deployment, G3+, multi-case
  execution, spend, money movement, or legal-compliance claims; or
- any claim of production readiness, physical isolation, durable-key continuity,
  backup qualification, or canonical activation.

## Later separate waves

After a physical wave passes and is independently accepted, H-12 may select one
C200 strategy through a new decision and separately reviewed qualification
plan. C200 qualification must not use the disposable `C020-S060` canary as
durability evidence.

After H-12 and the necessary key-recovery boundary are qualified, H-10 may
select one C210 backup mechanism, a distinct nonsynchronized backup location,
retention/deletion rules, and a clean-room restore plan. That is a separate
qualification wave with separate host and effects authority.

Canonical activation remains a final, separately worded human decision after
all blocking evidence is current and independently accepted. There is no
canonical-activation approval phrase in this packet.

## Next safe implementation packet

The next authorized work is repository-local implementation of the first
missing native physical-wave component behind an injectable, fail-closed,
non-executing Windows adapter, followed by deterministic and independent review.
It must preserve H-7 order and may not exercise the host. When all six physical
runtime components satisfy the readiness criteria, prepare—but do not execute—a
new revision-bound H-10 physical-wave authorization packet.
