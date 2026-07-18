# Fable Design C Reconciliation Proposal

Date: 2026-07-18  
Status: adopted as `design-c-baseline-v1`; H-5, H-6, H-7, H-10 root selection, and H-11 confirmed 2026-07-18; canonical activation and backup qualification remain blocked

## Executive disposition

Adopt Fable's Design C direction: build the sealed-world spine depth-first while
retaining the existing contracts, cassettes, validators, dossier catalog,
specialist mesh, domain-pack designs, renderer work, and recovery rules as a
gate-attached specification library. Stop adding case families, document
families, learning-loop subsystems, or orchestration breadth until one
employment case passes the revised hardening gate.

The current G2 prototype is useful evidence, but it is not yet scale-qualified.
Its logical sealed/operating/evaluation projections are not a physical oracle
boundary; its in-memory finance and event state are not a crash-recovery
substrate; and its present replay checks are not the 100-fresh-process E-2
harness.

## Reconciled P0 findings

### P0-1 — accept, with a stronger boundary

The current code stores sealed and operating planes in the same process and, in
some cases, the same aggregate object. Verb denial and projection validation are
valuable but insufficient.

The target is a kernel-owned sealed capability boundary plus a separate
OperatingStore. Merely using two SQLite files is not called physical isolation
when both are readable by the same OS identity. A promoted boundary requires:

- a sealed service/process identity or equivalent filesystem/secret isolation;
- a sealed database and domain-separated sealed key never passed to workers;
- separately minted opaque operating IDs and a kernel-only crosswalk;
- one-way projection through a narrow typed interface;
- no semantic labels in paths, filenames, logs, caches, or exceptions;
- an enumerated OperatingSurfaceRegistry covering databases, staging, temp,
  logs, cache, retrieval, embeddings, provider outbox, and exports; and
- mutation-proven canary scans over raw and common encoded forms.

HMAC is an identifier-minting primitive, not access control. A canary hash or
comparison oracle must not itself become an operating side channel.

### P0-2 — accept

Replace the addendum ratchet with a frozen `design-c-baseline-v1`. New
requirements must name a gate and retire, replace, or defer comparable
obligation mass. Existing broad architecture remains reference material, not a
G0 checklist. This is H-7.

### P0-3 — accept, fail closed while unset

Human review capacity becomes a measured budget. Until H-6 supplies weekly
capacity and sampling allocations, scale capacity is zero: local deterministic
development may continue, but no multi-case or unattended gate opens. Backlog
greater than four times measured weekly capacity is a mandatory pause.

### P0-4 — accept prospectively

No persistent canonical database exists yet, so there is nothing to migrate.
The Git repository may remain in OneDrive, but canonical databases, WAL/journal
files, staging, content-addressed objects, sealed keys, and runtime ledgers must
be created only under an approved non-synced local root. Startup verifies the
root boundary and checksum chain. Backup is deliberate and quiescent/consistent,
not ordinary live-file sync. Location and backup policy are H-10.

## P1 disposition

Adopt for the one-case hardening spine:

- a full two-sided sealed substrate, with discovery as projection;
- a five-axis MeritsVector: liability, causation, damages, procedure, and
  credibility;
- deterministic single-axis counterfactual siblings;
- a DesignedImperfectionLedger;
- valid-time and recorded-time as the bitemporal core;
- KnowledgeEvents and RecollectionStates as the cause of emergent conflicts;
- assertion manifests emitted with rendered prose;
- Berean operating only on six primitives and five deterministic G0 conflict
  classes;
- one Loop Contract with only L0–L4 active;
- kernel-owned VoicePacks plus later corpus-scale stylometric thresholds; and
- provider/version drift suspension when hosted model adapters are introduced.

Defer panel ensembles, settlement learning, dense retrieval, medical packs,
additional domains, native G3 rendering, and external sources to named gates.
Three-layer synthetic marking is required before native/export-ready artifacts
and remains H-5.

## SimPy disagreement and resolution

Fable recommended study-only status without inspecting the implemented adapter.
The current adapter is exact-version pinned, route-blind, payload-free,
noncanonical, unable to call the kernel, checked against a pure integer
reference scheduler, and covered by kernel-noninterference tests.

Do not delete the completed evidence. Reclassify SimPy as a qualified optional
comparison adapter, not the normative Design C scheduler and not a G0
dependency. The pure integer reference scheduler is normative. Do not extend
SimPy until a measured resource-contention use case demonstrates value that the
reference implementation cannot supply within its audit budget. Remove it if
that trigger is never met or if its maintenance surface exceeds its measured
value.

## Revised hardening gate

One employment case must pass the existing 13 walking-skeleton requirements
plus:

14. mutation-proven canary containment across every registered operating
    surface;
15. a worker boundary test showing the intended worker identity cannot open the
    sealed store, obtain either sealed key or crosswalk, or infer semantic IDs;
16. exact DesignedImperfectionLedger reconciliation; and
17. E-2 replay in 100 fresh processes with pinned environment inputs and loud
    stale-environment rejection.

E-6 recovery qualification then requires the smallest durable substrate:
append-only ledger, expected-parent compare-and-swap, idempotency key,
immutable command/result receipt, transactional outbox, checkpoint hash, and
finance journal. Leases wait until concurrency two. Kill drills cover crashes
around commit/outbox boundaries, duplicates, stale dependencies, corrupted
checkpoints, partial finance sequences, and retry exhaustion.

## Build order

1. H-7 freeze decision; H-10 storage decision; H-6/H-11 fail-closed budgets.
2. Versioned A2 schemas and one A12 registry.
3. E-1/E-2/E-6 harness contracts and negative controls before implementations.
4. Kernel commit/projector boundary.
5. Sealed and operating stores after H-10.
6. One two-sided world, imperfection ledger, bitemporal record layer, three
   renderer families, VoicePacks, and assertion manifests.
7. One reconciled finance cycle and OperatingStore-only Berean-lite.
8. Protected splits and L0–L4 records.
9. Independent re-review before any multi-case Cursor campaign.

## Mandatory stops

Stop on any canary hit, unchanged-input replay mismatch, stale environment or
dependency, sealed-store access by a worker, authority expansion, unreconciled
finance, unledgered designed defect, cost-budget failure, reviewer-capacity
failure, or unresolved human gate. One bounded repair is allowed before
escalation. This proposal does not authorize unattended execution, external
access, publication, live data, jurisdiction lock, G3+, or another domain.
