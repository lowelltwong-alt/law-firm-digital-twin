# Design C C010 and E-1 Harness Decision

Date: 2026-07-18  
Status: candidate implementation; Design C baseline and canonical storage remain unapproved

## Decision

Implement the provider-neutral schema/registry spine and the E-1 oracle-canary
falsifier before creating persistent stores. This work is useful under either
the current architecture or Fable's Design C and does not presume H-7 or H-10.

The unified registry records H-1 through H-12, A1 through A14, gate-attached
obligations, proposed L0–L4 loops, and optional runtime qualifications. Pending
human decisions stay structurally pending with fail-closed policies. SimPy is
recorded as a qualified optional non-default runtime adapter.

JobManifest and JobResult contracts require immutable input/dependency
commitments, relative write scopes under both POSIX and Windows path semantics,
separate writer/checker identities, exact budgets, one repair, idempotency and
checkpoint identities, mandatory terminal stops, and no canonical or unattended
authority.

## E-1 scope

The OperatingSurfaceRegistry enumerates ten required surfaces: operating
database, artifact staging, trace/log sink, local cache, retrieval index,
embedding index, provider-prompt outbox, public export, temporary workspace, and
renderer workspace. Uncreated or unobserved surfaces force
`incomplete_surfaces`; they cannot produce a clean claim.

The primary scanner detects the raw canary plus lowercase/uppercase hex,
standard/URL-safe Base64, and JSON-escaped forms in content, names, and metadata.
A separately implemented checker re-derives the expected hit set. The mutation
harness plants 80 leaks across every surface, encoding, and channel class.

Reports contain only protected commitments and hit classifications, never the
canary or key. Unknown surfaces are terminal. Scanner mutation evidence does not
claim system containment: worker-boundary validation, actual store scans,
filesystem/secret isolation, H-10 storage approval, and canonical qualification
all remain false.

## Expiry and stops

Re-run and re-review on any surface, encoding, report schema, path policy,
storage, key-custody, worker identity, logging, cache, retrieval, provider,
renderer, or export change. Any canary hit halts generation and quarantines the
affected run; it is never silently redacted or repaired in place.
