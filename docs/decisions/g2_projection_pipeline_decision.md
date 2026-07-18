# G2 Projection Pipeline Decision

Date: 2026-07-18
Status: accepted candidate for additive implementation
Risk tier: high, because these contracts control information boundaries inherited by future generators and cases.

## Authorized boundary

This wave implements only deterministic G0-G2 synthetic contracts and fixtures. It does not activate another case family, ingest external data, add real jurisdiction rules, render G3 native files, call a model/provider, change the existing walking-skeleton default path, publish, deploy, or authorize unattended execution.

## Decision

Adopt an immutable declarative compiler with four separated products:

1. kernel-only sealed case state;
2. operating projection;
3. one-artifact renderer projection; and
4. evaluation projection.

Artifacts remain staged proposals until separately admitted by a future kernel adapter. Renderers receive only an immutable artifact plan, an allowlisted assertion set, a time-local persona view, and required channel metadata. They never receive a blueprint, sealed case, evaluation projection, raw world bundle, or whole matter.

Every reusable contract is a `portable_core`. Provider/model choices belong only in future `runtime_adapter` and `provider_probe` records.

## Options considered

### A. Immutable declarative compiler

Advantages: smallest trusted surface, deterministic replay, explicit least-privilege projections, easy hostile mutation tests, and compatibility with the current G2 kernel.

Costs: time-varying state is represented by explicit immutable snapshots and lineage.

Decision: selected.

### B. Append-only sealed event ledger with reducers

Advantages: natural bitemporal persona, evidence, custody, and knowledge evolution.

Costs: more ordering, invalidation, reducer, and future-event leakage risk than the present qualification fixture can justify.

Decision: defer as an internal implementation option behind the same projection interfaces.

### Rejected: direct generative world mutation

A renderer or writer would receive a matter/world object and directly create facts or canonical artifacts.

Reason rejected: it violates world-first truth ownership and makes prompt instructions the only information boundary.

### Rejected: redact-after-generation

A broad prompt would expose sealed information and a filter would remove forbidden fields afterward.

Reason rejected: exposure has already occurred, small-domain hashes can become oracle side channels, and prose can encode labels without field names.

## Blast radius

Downstream consumers include evidence generators, persona/voice workers, Berean, fixture builders, corpus manifests, runtime adapters, Cursor campaign jobs, protected evaluation, learning loops, and future domain packs.

The existing `build_employment_world`, G2 kernel, cassettes, routes, and Berean checks remain unchanged. New modules are additive until a separately reviewed parity adapter exists.

## Invariants

- Only the trusted compiler reads sealed blueprints.
- Unknown or non-`active_g2` families fail closed.
- Operating and renderer projections contain no seed, axis label, design label, target posture/strength, conflict purpose, outcome control, evaluator ID, or cross-plane join key.
- A renderer assertion must exactly match an allowlisted fact/value known by its author at the artifact time.
- Persona state is contextual and time-varying; personality labels, protected attributes, education, class, or profession cannot determine intelligence, grammar, credibility, liability, or outcome.
- World, matter, persona, artifact, thread, version, and custody namespaces cannot cross cases.
- Content, required metadata, assertions, lineage, and custody are hash-bound.
- A staged artifact is never canonical merely because a worker marks it accepted.
- A local artifact receipt certifies only byte/shape consistency. Any controller or future admission adapter must also verify a full-case qualification receipt binding sealed fact authority, canonical persona projection, capability revision/authority, lineage graph, staged bytes, and every local receipt.
- Evaluation output cannot feed a generator without the declared learning-loop and human promotion gates.
- Schema, validator, privacy, authority, runtime-adapter, or scope changes invalidate qualification evidence.

## Campaign correction

The original static campaign allowed J100, J110, and J120 to run in parallel, then gave J200 no source-code write scope. That could produce three passing modules that do not compose.

Add J130 after J100/J110/J120:

- objective: lock the shared protocol and prove compiler/evidence/persona composition;
- source write scope: none; J130 is a test-only contract lock and must return upstream defects to J100/J110/J120 repairs;
- test scope: integration, hostile projection, replay, authority, lineage, receipt-integrity, and non-leakage tests;
- checker must differ from all three workers;
- J200 depends on J130 and may not repair source.

The campaign remains specification-only.

## Premortem

| Failure | Early signal | Stop or rollback |
|---|---|---|
| Renderer receives a sealed or whole-case object | Test needs redaction or traversal exceptions | Terminal; remove the reference path |
| Modules use incompatible IDs or revisions | Integration requires string translation or J200 source edits | Stop J200; repair J130 protocol |
| Future knowledge appears in an earlier artifact | Assertion source day exceeds artifact day | Reject artifact and invalidate case output |
| Persona richness becomes stereotype | Voice variation tracks prohibited proxy or collapses to templates | Suspend renderer and require representation review |
| Lineage/custody authenticates IDs rather than bytes | Body/metadata mutation leaves receipt valid | Terminal; expand commitment surface |
| Duplicate template volume masquerades as scale | High near-duplicate rate or low substantive density | Stop corpus expansion |
| Evaluator labels influence generation | Output differs when hidden evaluation projection changes | Terminal split/oracle violation |
| Commitment hash is treated as access control | Small-domain label inference succeeds | Remove it from renderer/operating surface |

## Acceptance and rollback

Acceptance requires focused hostile tests, the complete existing suite, compile checks, deterministic replay, static campaign validation, and independent fresh-eyes review.

Rollback is additive: remove the new modules, tests, fixture outputs, and J130 campaign revision. No existing world, kernel, cassette, or stored data migration is changed. The compiler result is a trusted kernel-internal record; worker handoffs must use only operating exports or one-artifact renderer projections, never the composite compilation.

